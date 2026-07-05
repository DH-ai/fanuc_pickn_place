# Fanuc M20 + Tesollo DG-3FB — MoveIt Integration Guide

This guide explains how the combined MoveIt cell is structured and how to run it on your Fanuc pick-and-place system.

---

## What Was Created

The `external/gripper_ros_driver/` folder previously contained **design notes only** (`df3fb_moveit_config` was listed but not implemented). These packages now exist:

```
external/gripper_ros_driver/
├── fanuc_tesollo_description/     # Combined URDF + mount config
├── df3fb_moveit_config/         # MoveIt config + demo launch
├── scripts/setup_moveit_workspace.bash
└── README.md
```

### Kinematic chain

```
world
 └── base_link … J6_link … ee_link          (Fanuc M-20iD/35)
      └── delto_base_link … F*_TIP           (Tesollo DG-3FB, 12 DoF)
           └── tesollo_palm
                └── tesollo_tool0           (planning / vision TCP)
```

Matches the vision pipeline frame tree: `base_link → tool0/tesollo_palm → finger tips`.

---

## Prerequisites

On the machine that runs MoveIt (Ubuntu 22.04 + ROS 2 Humble):

```bash
sudo apt install ros-humble-moveit ros-humble-moveit-configs-utils \
  ros-humble-moveit-planners-ompl ros-humble-ros2-control \
  ros-humble-ros2-controllers ros-humble-joint-state-publisher-gui
```

---

## One-Time Workspace Setup

From this repository:

```bash
bash external/gripper_ros_driver/scripts/setup_moveit_workspace.bash ~/ws_fanuc_tesollo
```

This script:

1. Clones `fanuc_description`, `fanuc_driver` (humble), `delto_b_ros2` (devel)
2. Symlinks `fanuc_tesollo_description` and `df3fb_moveit_config` from this repo
3. Runs `colcon build --packages-up-to df3fb_moveit_config`

---

## Run the MoveIt Demo

```bash
source ~/ws_fanuc_tesollo/install/setup.bash
ros2 launch df3fb_moveit_config demo.launch.py
```

### What launches

| Node | Purpose |
|------|---------|
| `ros2_control_node` | Mock hardware for 6 arm + 12 gripper joints |
| `joint_state_broadcaster` | Publishes `/joint_states` |
| `fanuc_arm_controller` | Arm trajectory execution |
| `delto_controller` | Gripper trajectory execution |
| `move_group` | MoveIt planning server |
| `rviz2` | MotionPlanning UI |
| `setup_planning_scene.py` | Adds table + bins + objects to scene |

### Planning scene objects

| Object ID | Description |
|-----------|-------------|
| `table` | Workspace table (1.5 × 1.0 m) |
| `pick_bin` | Left bin region |
| `place_bin` | Right bin region |
| `object_circle` / `object_triangle` / `object_heart` | Placeholder parts |

Adjust positions in `df3fb_moveit_config/scripts/setup_planning_scene.py` to match your Mech-Eye calibrated workspace.

---

## Using MoveIt in RViz

1. In **MotionPlanning** panel, select planning group:
   - **`arm`** — plan arm motion only (gripper moves as attached body)
   - **`gripper`** — plan finger joints only
   - **`arm_with_gripper`** — plan all 18 DOF (slower, higher-dimensional)

2. Set **Planning Library** to OMPL, planner **RRTConnect**.

3. Use **Planning** tab → drag interactive marker → **Plan** → **Execute**.

4. Named gripper states (dropdown **Select Goal State** when group = `gripper`):
   - `gripper_open`
   - `gripper_ball` (from working `gripper_code.py` preset)

---

## Attach Gripper to Fanuc — Mechanical / URDF

The mount is a fixed joint in `fanuc_m20_tesollo.urdf.xacro`:

```xml
<joint name="fanuc_ee_tesollo_mount" type="fixed">
  <parent link="ee_link"/>
  <child link="delto_base_link"/>
  ...
</joint>
```

Fanuc's `m20_35_18d` macro attaches `ee_link` directly to the arm flange. Tune `config/gripper_mount.yaml` after physical installation so the simulated TCP matches the real tool center point.

---

## Controllers and MoveIt Mapping

| ros2_control controller | Joints | MoveIt controller |
|-------------------------|--------|-------------------|
| `fanuc_arm_controller` | J1–J6 | `fanuc_arm_controller` |
| `delto_controller` | F1M1–F3M4 | `delto_controller` |

Config files:

- `df3fb_moveit_config/config/ros2_controllers.yaml`
- `df3fb_moveit_config/config/moveit_controllers.yaml`

---

## Moving from Mock Demo to Real Hardware

### Phase 1 — Arm only (Fanuc driver)

Use your existing Fanuc launch with `use_mock:=false` and the combined URDF instead of arm-only URDF. The Fanuc `fanuc_hardware_interface` must expose J1–J6 via `ros2_control` (see `docs/troubleshooting/troublshoot.md` for M20 GPIO / xacro fixes).

### Phase 2 — Gripper (Modbus)

Implement a ROS driver based on `external/gripper_test/main.py` (Modbus Operator Mode). It should:

- Publish gripper joints on `/joint_states` (or use joint_state_publisher merging)
- Expose `FollowJointTrajectory` action for `delto_controller` joints

Do **not** use `gripper_code.py` developer protocol unless the gripper DIP switches are in Developer Mode (see comparison report).

### Phase 3 — Single launch

Replace mock `ros2_control` plugin in `fanuc_tesollo.ros2_control.xacro` with:

- Fanuc hardware plugin for arm
- Custom Tesollo hardware plugin or separate controller node for gripper

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `fanuc_m20_description` not found | Run workspace setup script; clone `fanuc_description` |
| `delto_description` not found | Clone `delto_b_ros2` (devel branch) |
| Xacro error on `mount[...]` | Check `gripper_mount.yaml` syntax |
| No meshes in RViz | Ensure `delto_description/meshes` installed via colcon |
| Planning fails / collisions | Disable extra collision pairs in SRDF via Setup Assistant |
| Controllers not loading | `ros2 control list_controllers` — verify spawner order in launch |

---

## Related Docs

- [Gripper control comparison](./tesollo_gripper_control_comparison.md) — why Modbus works vs developer protocol
- [Vision pipeline v3](../vision_pipline/vision_pipiline_fanuc_v3.md) — `tesollo_tool0`, grasp planning nodes
- [Fanuc troubleshooting](../troubleshooting/troublshoot.md) — M20 ros2_control bring-up
