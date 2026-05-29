# Vision Pipeline — FANUC Robot Shape Sorting (v3 — Patched)

**Goal:** Detect objects and cavities on the workspace, estimate 6DoF poses, match objects to cavities, plan grasp sequences for a 3-finger Tesollo gripper, and output MoveIt-consumable pick/place plans.

**This document is a patched revision of `vision_pipeline_fanuc.md`. It corrects critical architectural mistakes in the v1 design.** Read this in preference to v1.

---

## 0. Change Log vs v1

| # | Severity | Area | Change |
|---|---|---|---|
| 1 | 🔴 Critical | Sensor model | Mech-Eye is **trigger-driven**, not streaming. Removed `ApproximateTimeSynchronizer`. Node 1 now drives a capture via the Mech-Eye SDK on PLC HIGH. |
| 2 | 🔴 Critical | Compute target | FoundationPose **will not run on Jetson Nano**. Pose estimation downgraded to ICP + PCA init (with FoundationPose as an opt-in path for x86 + RTX hosts). |
| 3 | 🔴 Critical | Cavity pose | Cavities are negative space — FoundationPose cannot match a solid mesh to them. Node 3B redesigned around rim edge detection + plane fitting. |
| 4 | 🔴 Critical | MoveIt interface | Grasp planners now output `moveit_msgs/Grasp[]` (pre-grasp → grasp → lift), not a single `PoseStamped`. |
| 5 | 🔴 Critical | IK feasibility | Grasp planner now performs an IK check on FANUC kinematics before publishing. Rejects singular / unreachable candidates. |
| 6 | 🔴 Critical | Assignment | New **Node 7: Task Assignment** matches objects ↔ cavities and enforces assembly order. |
| 7 | 🟡 Design | Gripper model | ContactGraspNet (parallel-jaw) used only for approach direction; finger placement derived from a 3-finger Tesollo-specific geometry pass. |
| 8 | 🟡 Design | Message bloat | Removed `SyncedRGBD` bundle. Capture-completed signal carries only a header + sequence; downstream nodes subscribe to Mech-Eye topics directly. |
| 9 | 🟡 Design | Confirmation trigger | `/task/placement_done` and the retry path are now first-class entries in the topic map. |
| 10 | 🟡 Design | ROS2 launch | `.launch` → `.launch.py`. Pinned to ROS 2 Humble. |
| 11 | 🟡 Design | Threading | Pose estimation runs in a single-threaded callback group with a drop-newest policy. |
| 12 | 🟢 Add | Hand-eye TF | Static TF broadcaster for `T_base_camera` loaded from a calibration YAML. |
| 13 | 🟢 Add | Depth scale | Mech-Eye depth is 16-bit mm — explicit scale conversion at back-projection. |
| 14 | 🟢 Add | Occlusion | Detection node flags overlapping bboxes; task assignment defers occluded picks. |
| 15 | 🟢 Add | Assembly order | Default order **circle → triangle → heart** enforced in Node 7. |

---

## 1. System Overview (Revised)

```
┌─────────────────────────────────────────────────────────────────────┐
│                       INDUSTRIAL I/O LAYER                           │
│   PLC Trigger (rising edge)         PLC ACK (vision_done)            │
│   std_msgs/Header                   std_msgs/Header                  │
└────────┬────────────────────────────────────▲────────────────────────┘
         │                                    │
         ▼                                    │
┌─────────────────────────────────────────────┴───────────────────────┐
│  NODE 1: Capture Driver (Mech-Eye)                                   │
│  • On PLC rising edge → CameraClient::Capture()                      │
│  • One atomic RGB + point-cloud + depth from a single structured-    │
│    light shot. NO time sync (hardware-synchronized).                 │
│  • Publishes: /mecheye/rgb, /mecheye/depth, /mecheye/points,         │
│               /mecheye/camera_info, /vision/capture_done             │
└────────────────────────────┬────────────────────────────────────────┘
                             │  /vision/capture_done (Header w/ seq)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  NODE 2: Object Detection (YOLOv8)                                   │
│  • Subscribes: /mecheye/rgb + /vision/capture_done (trigger)         │
│  • Output A: /vision/detections/objects  (object_*)                  │
│  • Output B: /vision/detections/cavities (cavity_*)                  │
│  • Reports per-detection occlusion_score (IoU with other bboxes)     │
└──────────────┬──────────────────────────┬───────────────────────────┘
               │                          │
    /detections/objects         /detections/cavities
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────────────────┐
│  NODE 3A: Object Pose    │  │  NODE 3B: Cavity Pose                 │
│  (ICP + PCA init)        │  │  (Rim detection + plane fit)          │
│  • Crop point cloud      │  │  • Canny on RGB rim ROI               │
│  • Init pose via PCA     │  │  • RANSAC plane on surrounding depth  │
│  • ICP refine to mesh    │  │  • Centroid = insertion XY            │
│  • Optional: Foundation- │  │  • Plane normal = insertion Z         │
│    Pose (x86+RTX only)   │  │  • No CAD mesh required               │
│  • Publishes:            │  │  • Publishes:                         │
│    /vision/poses/objects │  │    /vision/poses/cavities             │
└──────────────┬───────────┘  └──────────────┬───────────────────────┘
               │                             │
               └───────────────┬─────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  NODE 7 (NEW): Task Assignment                                       │
│  • Inputs: object poses + cavity poses + occlusion scores            │
│  • Matches object_<shape> ↔ cavity_<shape>                           │
│  • Defers picks with occlusion_score > threshold                     │
│  • Emits (pick, place) pairs in assembly order:                      │
│    circle → triangle → heart                                         │
│  • Publishes: /vision/task_pairs (PickPlacePair[])                   │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
┌──────────────────────────┐  ┌──────────────────────────────────────┐
│  NODE 4: Pick Grasp      │  │  NODE 5: Place Grasp                  │
│  • 3-finger Tesollo geom │  │  • Uses object-in-gripper offset      │
│  • Pre-grasp + grasp +   │  │    T_gripper_object from Node 4       │
│    lift sequence         │  │  • Pre-place + place + retreat        │
│  • IK feasibility filter │  │  • IK feasibility filter              │
│  • Output: moveit_msgs/  │  │  • Output: moveit_msgs/Grasp[]        │
│    Grasp[]               │  │                                       │
└──────────────┬───────────┘  └──────────────┬───────────────────────┘
               │                             │
               ▼                             ▼
        /grasp/pick_poses             /grasp/place_poses
        (moveit_msgs/Grasp[])         (moveit_msgs/Grasp[])
               │                             │
               └──────────────┬──────────────┘
                              ▼
                        ═══════════════════════
                        MoveIt boundary
                        ═══════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│  NODE 6: Visual Confirmation                                         │
│  • Trigger: /task/placement_done (from task manager — IN TOPIC MAP) │
│  • Re-triggers a Mech-Eye capture, crops cavity ROI                  │
│  • Lightweight classifier filled / empty                             │
│  • Publishes: /vision/confirmation                                   │
│  • If filled=false → publishes /vision/retry_request                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. ROS 2 Topic Map (Revised)

Pinned to **ROS 2 Humble**. All custom messages live in package `fanuc_vision_msgs` (renamed from `vision_msgs` to avoid colliding with the upstream `vision_msgs` package).

| Topic | Message Type | Publisher | Subscriber(s) |
|---|---|---|---|
| `/mecheye/rgb`                 | `sensor_msgs/Image`             | Node 1       | Node 2, Node 6       |
| `/mecheye/depth`               | `sensor_msgs/Image`             | Node 1       | Node 3A              |
| `/mecheye/point_cloud`         | `sensor_msgs/PointCloud2`       | Node 1       | Node 3A, Node 3B     |
| `/mecheye/camera_info`         | `sensor_msgs/CameraInfo`        | Node 1       | Node 3A, Node 3B     |
| `/vision/poses/objects`        | `vision_msgs/ObjectPoseArray`   | Node 3A      | Node 7               |
| `/vision/poses/cavities`       | `vision_msgs/ObjectPoseArray`   | Node 3B      | Node 7, Node 6       |
| `/task/assembly_queue`         | `vision_msgs/AssemblyTask[]`    | Node 7       | Task Manager (MoveIt)|
| `/grasp/pick_poses`            | `moveit_msgs/Grasp[]`           | Node 4       | MoveIt               |
| `/grasp/place_poses`           | `moveit_msgs/Grasp[]`           | Node 5       | MoveIt               |
| `/task/placement_done`         | `std_msgs/String`               | Task Manager | Node 6               |

Removed: /vision/synced_rgbd (SyncedRGBD custom message — no longer needed)

> Note: `moveit_msgs/Grasp[]` is not directly a topic type — it is published inside a small wrapper array message. v1 incorrectly listed `geometry_msgs/PoseStamped[]` as a topic type, which is invalid in ROS 2.

---

## 3. Node Specifications (Revised)

## Node 1 — Sensor Fusion & Gating
Role: Entry gate for the entire pipeline. Nothing downstream runs unless PLC signals ready.

- Subscribes to `/plc/trigger` (std_msgs/Bool)
- On PLC HIGH: calls `mecheye_ros2_interface::CameraClient::Capture()` — single atomic capture
- Mech-Eye returns RGB + depth + point cloud in one hardware-synchronized bundle — no time sync needed
- Publishes `/mecheye/rgb`, `/mecheye/depth`, `/mecheye/point_cloud` downstream
- On PLC LOW: does nothing — robot arm is in motion, no frames processed
- No `ApproximateTimeSynchronizer` — Mech-Eye hardware guarantees RGB/depth alignment

### Node 2 — Object Detection (YOLOv8)

**Role:** Unchanged from v1 except:

- Subscribes to `/vision/capture_done` as a trigger; only consumes the *latest* `/mecheye/rgb` matching that header.
- For each detection, computes `occlusion_score = max IoU with any other detection bbox`. Stored in the second hypothesis score slot.
- NMS threshold and confidence threshold loaded from config.

## Node 3A — Object Pose Estimation (6DoF)
Role: Lift 2D detections to full 6DoF poses in robot base frame.

Method: GDR-Net trained on BlenderProc-generated BOP-format synthetic data

At startup:
- Loads trained GDR-Net weights from `config/gdrn_weights.pth`
- Loads mesh registry: `config/mesh_registry.yaml` maps class name → `.ply` path
- Loads Mech-Eye intrinsics K matrix from `/mecheye/camera_info`

Steps per detection:
1. Receive bounding box from Node 2
2. Crop RGB + depth to bounding box
3. Convert Mech-Eye depth (mm) → meters (divide by 1000)
4. Run GDR-Net inference → outputs R (3×3 rotation) + t (3D translation) in camera frame
5. Reject if pose confidence < 0.5
6. Transform pose from camera frame → robot base frame via static TF (hand-eye calibration)
7. Publish to `/vision/poses/objects` as `ObjectPoseArray`

Training data: BlenderProc PBR renders in BOP format (see Training Pipeline section)
Evaluation: BOP metrics — target AR > 0.85 per shape before deployment
Generalization: New shape = add `.ply` mesh + retrain GDR-Net + add to mesh_registry.yaml

## Node 3B — Cavity Pose Estimation (6DoF)
Role: Estimate cavity position and insertion normal. NOT the same method as Node 3A.

Cavities are negative space — no solid mesh to register against. FoundationPose/GDR-Net
do not apply here. Method is geometry-based:

Steps per cavity detection:
1. Receive cavity bounding box from Node 2
2. Crop depth map to bounding box
3. Fit plane to depth points around cavity rim using RANSAC (pcl::SACSegmentation)
4. Compute cavity centroid as mean of rim edge points — this is the insertion XY target
5. Cavity Z-axis = board surface plane normal (pointing up toward camera)
6. Cavity orientation derived from rim geometry:
   - Triangle: fit 3 line segments to rim → longest edge = X-axis
   - Heart: bilateral symmetry axis from PCA on rim points = X-axis
   - Circle: X-axis arbitrary (rotationally symmetric)
7. Transform to robot base frame via static TF
8. Publish to `/vision/poses/cavities` as `ObjectPoseArray`

Note: Nodes 3A and 3B are separate nodes — estimation method is fundamentally different.
They cannot be the same node parametrized by family.

## Node 4 — Pick Grasp Planner (3-Finger Gripper)
Role: Given 6DoF object pose, compute optimal 3-finger grasp and output MoveIt-ready message.

Input:  `/vision/poses/objects` (ObjectPoseArray)
Output: `/grasp/pick_poses` (moveit_msgs/Grasp[])

For each object pose received:
1. Load object mesh from registry
2. Fit minimal enclosing geometry around mesh at estimated pose
3. Compute 3-finger contact points on largest stable grasp axis
4. Build grasp sequence:
   - `pre_grasp_pose`  — approach vector, 150mm above grasp point
   - `grasp_pose`      — contact position
   - `post_grasp_pose` — lift 100mm straight up after close
5. IK feasibility check on ALL three poses before publishing:
   - Reject if any pose has no IK solution
   - Reject if any pose puts FANUC J5 within 10° of 0° (wrist singularity)
   - Try next-best grasp candidate on rejection
6. Set gripper pre-grasp opening width per shape:
   - Circle:   fingers open to object diameter + 10mm clearance
   - Triangle: pinch mode width
   - Heart:    lobe width + 10mm clearance
7. Publish `moveit_msgs/Grasp[]` — MoveIt pick pipeline consumes this directly

Generalization: New shape = add mesh. Grasp logic operates on geometry, not class name.

## Node 5 — Place Grasp Planner (3-Finger Gripper)
Role: Given 6DoF cavity pose, compute release sequence and output MoveIt-ready message.

Input:  `/vision/poses/cavities` (ObjectPoseArray)
Output: `/grasp/place_poses` (moveit_msgs/Grasp[])

For each cavity pose received:
1. Align held object's insertion axis with cavity opening normal
2. Build place sequence:
   - `pre_place_pose`  — hover 80mm above cavity center
   - `place_pose`      — release position at cavity mouth
3. IK feasibility check on both poses before publishing
4. Publish `moveit_msgs/Grasp[]`

### Node 6 — Visual Confirmation  🟡 **PATCHED**

**Role:** Verify cavity is filled after a place. Now with explicit topic-map presence and retry path.

- Trigger: `/task/placement_done` (now declared in the topic map).
- Re-triggers a Mech-Eye capture (it issues a one-shot capture to Node 1 over an internal service `/mecheye/single_capture`, since the PLC is not driving this loop).
- Crops cavity ROI using the last known cavity pose; runs ResNet18 binary classifier.
- Publishes `/vision/confirmation`.
- If `filled == false`: publishes `/vision/retry_request` with the failed cavity_id; task manager re-enters the pipeline for that cavity.

## Node 7 — Task Assignment (NEW)
Role: Match detected objects to their corresponding cavities. Enforce assembly order.
      This node is the boundary between vision and motion planning.

Input:  `/vision/poses/objects`  (ObjectPoseArray)
        `/vision/poses/cavities` (ObjectPoseArray)
Output: `/task/assembly_queue`   (AssemblyTask[]) — ordered list of (pick, place) pairs

Logic:
1. Wait until both object poses and cavity poses are received for current frame
2. Match each `object_<shape>` to its `cavity_<shape>` by class name suffix
3. If multiple instances of same shape: assign nearest object to nearest cavity
4. Sort assembly queue by difficulty (ascending):
   - circle first   (easiest — symmetric, trivial IK, simple insertion)
   - triangle second
   - heart last     (hardest — non-convex, orientation-critical, force FSM)
5. Publish ordered AssemblyTask[] queue to `/task/assembly_queue`
6. Task Manager (MoveIt side) pops one task at a time, executes, 
   signals `/task/placement_done` when complete

Failure handling:
- Object detected but no matching cavity → log warning, skip that object
- Cavity detected but no matching object → log, mark cavity as pending

---

## 4. Hand-Eye Calibration & TF  🟢 **NEW SECTION**

Frames (REP-103 compliant):

```
world ── base_link ── tool0 ── tesollo_palm ── tesollo_finger_{1,2,3}_tip
                              ▲
                              │ (only if eye-in-hand)
                              │
        mecheye_link ── mecheye_color_optical_frame
        ▲
        │ static TF from calibration (this file)
        │
        base_link  (eye-to-hand, our default)
```

- Camera mounting: **eye-to-hand**, fixed above the workspace. (Document the choice; eye-in-hand would invert which frame `T_base_camera` is published relative to.)
- Calibration produced offline via `easy_handeye2` and stored as `config/hand_eye_calibration.yaml`:
  ```yaml
  parent_frame: base_link
  child_frame: mecheye_color_optical_frame
  translation: { x: 0.621, y: 0.014, z: 1.150 }   # meters
  rotation: { x: 0.0, y: 0.0, z: 0.7071, w: 0.7071 }  # quaternion
  ```
- `hand_eye_tf_broadcaster` node loads this YAML and publishes a static TF at startup.

---

## 5. Depth Unit Convention  🟢 **NEW SECTION**

- Mech-Eye depth: `16UC1`, **1 unit = 1 mm**.
- Open3D, PCL, and ICP assume **meters**.
- All back-projection code MUST multiply by `0.001f` before constructing a point cloud. Wrap this in a single utility function `mecheye_depth_to_points()` to prevent unit drift across nodes.

---

## 6. Custom Messages (changed)

```
# REMOVED
# vision_msgs/SyncedRGBD.msg  ← no longer needed, Mech-Eye triggered directly

# ADDED
# vision_msgs/AssemblyTask.msg
std_msgs/Header header
string object_class           # e.g. "object_heart"
string cavity_class           # e.g. "cavity_heart"
geometry_msgs/Pose object_pose
geometry_msgs/Pose cavity_pose
uint8 priority                # 0=highest — circle=0, triangle=1, heart=2
```

---

## 7. Launch Architecture

```
vision_pipeline.launch.py                 ← ROS2 (Python), not .launch (ROS1 XML)
├── sensor_fusion_node        (Node 1)    param: mecheye_ip, plc_trigger_topic
├── detection_node            (Node 2)    param: model=config/yolo_weights.pt
├── object_pose_node          (Node 3A)   param: model=config/gdrn_weights.pth,
│                                                mesh_registry=config/mesh_registry.yaml
├── cavity_pose_node          (Node 3B)   param: mesh_registry=config/mesh_registry.yaml
├── pick_grasp_node           (Node 4)    param: mesh_registry=config/mesh_registry.yaml
├── place_grasp_node          (Node 5)    param: mesh_registry=config/mesh_registry.yaml
├── task_assignment_node      (Node 7)    param: assembly_order=[circle,triangle,heart]
├── visual_confirmation_node  (Node 6)    param: model=config/confirmation_weights.pt
└── static_tf_broadcaster                 param: calibration=config/hand_eye_calib.yaml
```

---

## 8. Compute Placement Policy  🟢 **NEW SECTION**

| Component | Host | Reason |
|---|---|---|
| Node 1 (Mech-Eye SDK) | x86 PC | Mech-Eye SDK requires x86 Linux/Windows |
| Node 2 (YOLOv8) | Jetson OR x86 | YOLOv8n/s runs fine on Jetson Nano @ ~5 FPS |
| Node 3A (ICP default) | Jetson OR x86 | ICP CPU-bound, ~200 ms per object |
| Node 3A (FoundationPose) | **x86 + RTX 3060+** | Will OOM on Jetson Nano |
| Node 3B (rim+plane) | Jetson OR x86 | OpenCV + small RANSAC, trivial |
| Node 4 / 5 | Jetson OR x86 | Geometry + IK service call |
| Node 6 (ResNet18) | Jetson OR x86 | Lightweight inference |
| Node 7 | Anywhere | Pure logic |

If running fully on a Jetson, **stay on the ICP path**. Do not enable `use_foundation_pose`.

---

## 9. Failure / Retry Paths  🟢 **NEW SECTION**

| Failure | Detected by | Response |
|---|---|---|
| Detection returns 0 objects | Node 2 | Publish empty arrays; Node 7 sends `/plc/vision_done` with `valid=false` |
| ICP fitness below threshold | Node 3A | Drop that pose; flag class as `pose_failed` in `ObjectPoseArray` |
| No valid IK for any approach axis | Node 4 / 5 | Drop that pair; Node 7 re-queues it for a later wave |
| All pairs deferred (e.g. heavy occlusion) | Node 7 | Request operator intervention via task manager |
| Confirmation says `filled=false` | Node 6 | Publish `/vision/retry_request`; task manager re-enters pipeline |
| Mech-Eye capture timeout | Node 1 | Publish error on `/vision/capture_done` with `valid=false`; PLC sees no ACK |

---

## 10. Latency Budget  🟢 **NEW SECTION**

End-to-end target from PLC trigger to `/plc/vision_done`:

| Stage | Budget |
|---|---|
| Mech-Eye capture | 400 ms |
| YOLOv8 inference | 80 ms |
| Pose estimation (per object, parallel pipeline) | 250 ms |
| Task assignment | 20 ms |
| Grasp planning + IK (per pair) | 100 ms |
| **Total (3 shapes, sequential)** | **≤ 1.5 s** |

Anything beyond 2 s should be investigated.

---

## 11. Key Design Decisions (Revised)

| Decision | Choice | Reason |
|---|---|---|
| Sensor interface | Triggered Mech-Eye SDK call | Mech-Eye is structured-light, not streaming |
| Detection model | YOLOv8 | Unchanged |
| Object pose | ICP + PCA init (Jetson-safe); FoundationPose optional on x86+RTX | Compute reality on Jetson Nano |
| Cavity pose | Rim contour + plane fit | Cavities have no fillable mesh for FoundationPose |
| Grasp planning output | `moveit_msgs/Grasp[]` | Standard MoveIt pick/place interface |
| IK feasibility | Pre-publish filter via `compute_ik` | Avoids publishing grasps the robot can't reach |
| Object↔cavity matching | Dedicated Node 7 with Hungarian assignment | v1 had no matching logic at all |
| Gripper specificity | Tesollo 3-finger analytical contact geometry | Parallel-jaw learned grasps are not 3-finger valid |
| Hand-eye TF | Static broadcaster from calibration YAML | Was implicit in v1, now explicit |
| ROS version | ROS 2 Humble | Aligns with current robotics tooling |

---

## 12. What v1 Got Right (Kept Unchanged)

- Class-name string contract between nodes (no integer IDs).
- `classes.yaml` + `mesh_registry.yaml` as the generalization mechanism for new shapes.
- Blender synthetic data pipeline and domain randomization checklist.
- Separation of detection from pose estimation.
- Pipeline gating on PLC (just implemented differently — as a capture trigger rather than a stream gate).

---

## 13. Training Pipeline (BlenderProc + BOP)

### 13.1 Dataset Format
All synthetic data generated in BOP format (BOP Benchmark for 6D Object Pose Estimation).
This format is required by GDR-Net and compatible with the BOP evaluation toolkit.

```
dataset/
├── models/
│   ├── obj_000001.ply          # heart   — real-world dimensions, centered at centroid
│   ├── obj_000002.ply          # circle
│   ├── obj_000003.ply          # triangle
│   └── models_info.json        # diameter, bounding box extents per model
├── train_pbr/                  # BlenderProc PBR renders
│   └── 000000/                 # scene 000000
│       ├── rgb/                # rendered photos (1000 per scene)
│       ├── depth/              # 16-bit depth maps in mm
│       ├── mask/               # full object masks per instance
│       ├── mask_visib/         # visible-only masks (used for training)
│       ├── scene_camera.json   # Mech-Eye K matrix + depth_scale per frame
│       ├── scene_gt.json       # ground truth R, t per object per frame
│       └── scene_gt_info.json  # bbox, visib_fract per object per frame
└── test/                       # real Mech-Eye captures for evaluation
    └── 000001/
        ├── rgb/
        ├── depth/
        ├── scene_camera.json   # real Mech-Eye intrinsics
        └── scene_gt.json       # manually annotated ground truth
```

### 13.2 BlenderProc Scene Generation
- Model each shape in Blender to exact real-world dimensions
- Run blender/generate_bop_data.py — see blender/ folder
- 50 scenes × 1000 frames = 50,000 training images
- Camera: fixed overhead mount ±5° jitter matching real Mech-Eye position
- Depth noise: Gaussian σ=2mm to simulate structured light noise
- depth_scale: 0.001 (Mech-Eye outputs mm, BOP expects meters)

Domain randomization per frame:
- Lighting: HDR environment maps + 2-5 area lights, random color temperature 2700K–6500K
- Object pose: full random Z rotation, small XY tilt ±15°
- Material: random PBR values (roughness, specular, base color HSV jitter ±15%)
- Occlusion: random partial overlaps between objects
- Scale jitter: ±5% object scale variation
- Depth dropout patches: simulate Mech-Eye sensor holes on specular surfaces

### 13.3 Pose Estimator Training
Model: GDR-Net (Geometry-guided Direct Regression Network)
Reason: Strong on textureless industrial parts, fast inference (~50ms/object), BOP-native

| Model        | Framework  | Dataset          | Notes                              |
|--------------|------------|------------------|------------------------------------|
| GDR-Net      | PyTorch    | BlenderProc BOP  | Primary pose estimator             |
| YOLOv8       | Ultralytics| BlenderProc BOP  | Detection only — separate training |
| ResNet18     | PyTorch    | Blender filled/  | Visual confirmation classifier     |
|              |            | empty cavity     |                                    |

### 13.4 BOP Evaluation
Run before deploying any model to the robot.

Metrics:
- AR_VSD:  Visible Surface Discrepancy — rotation accuracy on visible surface
- AR_MSSD: Max Symmetric Surface Distance — handles object symmetry correctly
- AR_MSPD: 2D projection accuracy
- AR:      Mean of above three — primary deployment gate

Target: AR > 0.85 per shape
Evaluate per shape separately — heart will score lowest on first run.
If heart AR < 0.75: add more BlenderProc scenes with heart at 180° orientation variants.

### 13.5 Real Test Set Annotation
Capture 200 real images with Mech-Eye.
Annotate ground truth poses using a calibration board or manual measurement.
Place in dataset/test/ — run BOP evaluation to measure sim-to-real gap.

---

## 14. File Structure (changed sections only)

```
vision_pipeline_fanuc/
├── config/
│   ├── classes.yaml
│   ├── mesh_registry.yaml
│   ├── yolo_weights.pt
│   ├── gdrn_weights.pth            ← replaces confirmation_weights (pose estimator)
│   ├── confirmation_weights.pt
│   └── hand_eye_calib.yaml         ← NEW: hand-eye calibration transform
│
├── dataset/                        ← NEW: BOP format training data
│   ├── models/
│   ├── train_pbr/
│   └── test/
│
├── blender/                        ← NEW: BlenderProc scripts
│   ├── generate_bop_data.py
│   ├── convert_meshes.py
│   └── hdri/                       ← HDR environment maps
│
├── training/
│   ├── train_yolo.py
│   ├── train_gdrn.py               ← replaces no specific pose trainer before
│   └── train_confirmation.py
│
├── msg/
│   ├── ObjectPose.msg
│   ├── ObjectPoseArray.msg
│   ├── AssemblyTask.msg            ← NEW
│   └── PlacementResult.msg
│   (SyncedRGBD.msg removed)
```
