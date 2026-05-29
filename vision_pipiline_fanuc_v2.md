# Vision Pipeline — FANUC Robot Shape Sorting (v2 — Patched)

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
| `/plc/trigger` | `std_msgs/Header` (rising edge = capture) | PLC ROS bridge | Node 1 |
| `/plc/vision_done` | `std_msgs/Header` (ACK back to PLC) | Node 7 | PLC ROS bridge |
| `/mecheye/rgb` | `sensor_msgs/Image` (rgb8) | Node 1 | Node 2, Node 6 |
| `/mecheye/depth` | `sensor_msgs/Image` (16UC1, **mm**) | Node 1 | Node 3A, Node 3B |
| `/mecheye/points` | `sensor_msgs/PointCloud2` | Node 1 | Node 3A, Node 3B |
| `/mecheye/camera_info` | `sensor_msgs/CameraInfo` | Node 1 | Node 3A, Node 3B |
| `/vision/capture_done` | `std_msgs/Header` (seq id) | Node 1 | Node 2 |
| `/vision/detections/objects` | `vision_msgs/Detection2DArray` (+ occlusion_score in `results[].hypothesis.score_2`) | Node 2 | Node 3A |
| `/vision/detections/cavities` | `vision_msgs/Detection2DArray` | Node 2 | Node 3B |
| `/vision/poses/objects` | `fanuc_vision_msgs/ObjectPoseArray` | Node 3A | Node 7 |
| `/vision/poses/cavities` | `fanuc_vision_msgs/CavityPoseArray` | Node 3B | Node 7 |
| `/vision/task_pairs` | `fanuc_vision_msgs/PickPlacePairArray` | Node 7 | Node 4, Node 5 |
| `/grasp/pick_poses` | `moveit_msgs/Grasp[]` (wrapped in `PickPlanArray`) | Node 4 | **MoveIt** |
| `/grasp/place_poses` | `moveit_msgs/PlaceLocation[]` (wrapped in `PlacePlanArray`) | Node 5 | **MoveIt** |
| `/task/placement_done` | `std_msgs/Header` + cavity_id | Task Manager | Node 6 |
| `/vision/confirmation` | `fanuc_vision_msgs/PlacementResult` | Node 6 | Task Manager |
| `/vision/retry_request` | `fanuc_vision_msgs/RetryRequest` | Node 6 | Task Manager |
| `/tf_static` | `tf2_msgs/TFMessage` (T_base_camera) | hand_eye_tf_broadcaster | All TF consumers |

> Note: `moveit_msgs/Grasp[]` is not directly a topic type — it is published inside a small wrapper array message. v1 incorrectly listed `geometry_msgs/PoseStamped[]` as a topic type, which is invalid in ROS 2.

---

## 3. Node Specifications (Revised)

### Node 1 — Mech-Eye Capture Driver  🔴 **REDESIGNED**

**Role:** Drive the Mech-Eye in triggered mode. There is no continuous stream.

- Subscribes: `/plc/trigger` (edge-detected).
- On rising edge:
  1. `CameraClient::Capture()` — atomic structured-light shot, hardware-synchronized RGB + depth + point cloud.
  2. Publishes `/mecheye/rgb`, `/mecheye/depth`, `/mecheye/points`, `/mecheye/camera_info` with a shared header (same `stamp`, monotonically increasing `frame_id`-suffixed seq).
  3. Publishes `/vision/capture_done` as the downstream gate.
- **No `ApproximateTimeSynchronizer`.** Hardware sync makes it unnecessary.
- **No `SyncedRGBD` bundle.** Downstream nodes subscribe to Mech-Eye topics directly; the per-capture header on `/vision/capture_done` correlates frames.
- Capture latency budget: ≤ 400 ms from PLC edge to `capture_done`.

### Node 2 — Object Detection (YOLOv8)

**Role:** Unchanged from v1 except:

- Subscribes to `/vision/capture_done` as a trigger; only consumes the *latest* `/mecheye/rgb` matching that header.
- For each detection, computes `occlusion_score = max IoU with any other detection bbox`. Stored in the second hypothesis score slot.
- NMS threshold and confidence threshold loaded from config.

### Node 3A — Object Pose Estimation  🔴 **REDESIGNED**

**Role:** Lift 2D detections to 6DoF poses, on Jetson-class compute.

- Default method: **PCA-initialized ICP** against the class CAD mesh.
  1. Crop point cloud to bbox + small margin.
  2. Statistical outlier removal.
  3. PCA on the crop → initial rotation (principal axis alignment with mesh's principal axis from registry).
  4. ICP refine (point-to-plane, max 50 iterations, fitness threshold from config).
  5. Transform pose from `camera_optical_frame` → `base_link` via TF.
- Optional method (opt-in via param `use_foundation_pose: true`): **FoundationPose** — only on x86 hosts with ≥ RTX 3060. Documented as not viable on Jetson Nano.
- **Threading:** single-threaded callback group. Drop-newest policy: if a detection arrives while ICP is running on the previous one, the new detection is queued (depth=1) and any older queued one is discarded.
- Publishes `fanuc_vision_msgs/ObjectPoseArray` with `class_name`, `pose`, `mesh_path`, `fit_score`, and `T_gripper_object_hint` (a CAD-frame anchor used by Node 5).

### Node 3B — Cavity Pose Estimation  🔴 **REDESIGNED**

**Role:** Cavities are negative space. Treat them geometrically as a hole in a plane.

- Per cavity detection:
  1. Crop RGB to bbox.
  2. Canny edges + contour fit → cavity rim polygon.
  3. Sample depth points in an annulus around the rim (board surface, not the hole).
  4. RANSAC plane fit on the annulus depth → board normal **n**.
  5. Project rim contour onto the plane → 2D centroid.
  6. Cavity pose = (centroid, orientation aligned to **n** with cavity's principal in-plane axis from the contour's PCA).
- **No CAD mesh required for cavities**, only the board surface plane and the rim.
- Publishes `fanuc_vision_msgs/CavityPoseArray` with `class_name`, `pose`, `board_normal`, `rim_diameter`.
- Single-threaded callback group, same drop-newest policy as 3A.

**Why 3A and 3B cannot be a single parametrized node:** the input modality (point cloud crop vs RGB rim + plane fit) and algorithm are fundamentally different. Sharing utilities via a library is fine; sharing the node is not.

### Node 4 — Pick Grasp Planner  🔴 **PATCHED**

**Role:** Produce a complete `moveit_msgs/Grasp` per pick task.

For each object pose received from Node 7:

1. Load mesh from registry.
2. Compute 3-finger Tesollo contact triple on the largest stable grasp axis (analytical, from the mesh).
3. Build the grasp sequence:
   - `pre_grasp_pose`   — grasp_pose translated 150 mm along `-approach_vector`.
   - `grasp_pose`       — contact-point centroid with gripper aligned to the grasp axis.
   - `lift_pose`        — grasp_pose translated 100 mm along `+world_z`.
4. Populate `moveit_msgs/Grasp`:
   - `grasp_pose` → `grasp_pose`.
   - `pre_grasp_approach` → vector + min/desired distance.
   - `post_grasp_retreat` → vector + min/desired distance.
   - `pre_grasp_posture` → Tesollo open joint state.
   - `grasp_posture` → Tesollo closed joint state (shape-specific from config).
5. **IK feasibility filter** — call MoveIt's `compute_ik` service for `pre_grasp_pose`, `grasp_pose`, and `lift_pose`. Reject the candidate if any IK fails or if FANUC J5 is within ±5° of 0° (wrist singularity).
6. If primary candidate is rejected, try alternate approach axes (top, side+90°, side-90°) before giving up.
7. Optional fallback: ContactGraspNet on the local point cloud — but use only its approach-vector output. Finger placement is overridden with the Tesollo-specific 3-finger geometry.
8. Also publishes `T_gripper_object` (the object's pose expressed in the gripper frame at the moment of grasp) onto the task pair, so Node 5 knows how the object is held.

### Node 5 — Place Grasp Planner  🔴 **PATCHED**

**Role:** Produce a complete `moveit_msgs/PlaceLocation` per place task.

- Inputs: cavity pose (from Node 3B), the held object's class, and `T_gripper_object` from Node 4.
- Compute the desired object-in-cavity pose: insertion axis aligned with cavity normal, in-plane orientation matched to cavity principal axis.
- Compute required end-effector pose: `T_base_ee_at_place = T_base_cavity × T_cavity_object × T_object_gripper`. (Without `T_gripper_object`, the planner cannot know where the wrist must be — this was the missing piece in v1.)
- Build the sequence:
  - `pre_place_pose`  — place pose + 80 mm along `+cavity_normal`.
  - `place_pose`      — final insertion pose.
  - `retreat_pose`    — place pose + 120 mm along `+cavity_normal`.
- Populate `moveit_msgs/PlaceLocation` (`place_pose`, `pre_place_approach`, `post_place_retreat`, `post_place_posture` = Tesollo open).
- **IK feasibility filter** same as Node 4.

### Node 6 — Visual Confirmation  🟡 **PATCHED**

**Role:** Verify cavity is filled after a place. Now with explicit topic-map presence and retry path.

- Trigger: `/task/placement_done` (now declared in the topic map).
- Re-triggers a Mech-Eye capture (it issues a one-shot capture to Node 1 over an internal service `/mecheye/single_capture`, since the PLC is not driving this loop).
- Crops cavity ROI using the last known cavity pose; runs ResNet18 binary classifier.
- Publishes `/vision/confirmation`.
- If `filled == false`: publishes `/vision/retry_request` with the failed cavity_id; task manager re-enters the pipeline for that cavity.

### Node 7 — Task Assignment  🆕 **NEW**

**Role:** Bridge between perception and motion. The piece v1 omitted.

- Subscribes to `/vision/poses/objects` and `/vision/poses/cavities`. Joins them by shape suffix: `object_triangle` ↔ `cavity_triangle`.
- For each candidate pair, compute a priority:
  1. Assembly-order rank — default `circle (0) < triangle (1) < heart (2)`, configurable.
  2. Penalize objects with `occlusion_score > 0.15` — defer them (publish in a later wave).
  3. Penalize objects far from the workspace centroid (longer travel).
- Emits a `PickPlacePairArray` in priority order.
- Publishes `/plc/vision_done` after the array is dispatched, so the PLC knows the vision cycle completed.
- Handles the multi-instance case (two `object_triangle` and two `cavity_triangle`) by Hungarian assignment on Euclidean cost in the table plane.

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

## 6. Custom Message Definitions (Revised)

Package: `fanuc_vision_msgs` (renamed from `vision_msgs` to avoid collision with upstream).

```
# fanuc_vision_msgs/ObjectPose.msg
std_msgs/Header header
string class_name
float32 confidence
geometry_msgs/Pose pose                # in base_link
string mesh_path
float32 fit_score                      # ICP fitness
geometry_msgs/Transform t_gripper_object_hint
```

```
# fanuc_vision_msgs/ObjectPoseArray.msg
std_msgs/Header header
fanuc_vision_msgs/ObjectPose[] poses
```

```
# fanuc_vision_msgs/CavityPose.msg
std_msgs/Header header
string class_name
geometry_msgs/Pose pose                # in base_link
geometry_msgs/Vector3 board_normal
float32 rim_diameter
```

```
# fanuc_vision_msgs/CavityPoseArray.msg
std_msgs/Header header
fanuc_vision_msgs/CavityPose[] poses
```

```
# fanuc_vision_msgs/PickPlacePair.msg
std_msgs/Header header
string shape                           # e.g. "triangle"
fanuc_vision_msgs/ObjectPose object
fanuc_vision_msgs/CavityPose cavity
int32 priority                         # lower = pick first
bool deferred                          # true if occlusion forces a later wave
```

```
# fanuc_vision_msgs/PickPlacePairArray.msg
std_msgs/Header header
fanuc_vision_msgs/PickPlacePair[] pairs
```

```
# fanuc_vision_msgs/PlacementResult.msg
std_msgs/Header header
string cavity_id
bool filled
float32 confidence
```

```
# fanuc_vision_msgs/RetryRequest.msg
std_msgs/Header header
string cavity_id
string reason                          # "not_filled", "wrong_shape", etc.
int32 attempt_count
```

> `SyncedRGBD` from v1 is removed.

---

## 7. Launch Architecture (ROS 2)  🟡 **PATCHED**

```
launch/vision_pipeline.launch.py
├── hand_eye_tf_broadcaster      (loads config/hand_eye_calibration.yaml)
├── mecheye_capture_node         (Node 1)
├── detection_node               (Node 2) model: config/yolo_weights.pt
├── object_pose_node             (Node 3A) mesh_registry: config/mesh_registry.yaml
├── cavity_pose_node             (Node 3B) — no mesh registry needed
├── task_assignment_node         (Node 7) assembly_order: [circle, triangle, heart]
├── pick_grasp_node              (Node 4) gripper_config: config/tesollo.yaml
├── place_grasp_node             (Node 5) gripper_config: config/tesollo.yaml
└── visual_confirmation_node     (Node 6) model: config/confirmation_weights.pt
```

Filename is `.launch.py` (Python), not `.launch` (XML/ROS1).

All paths and thresholds flow through ROS 2 parameters; no hardcoded paths in node code.

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
