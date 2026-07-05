# Fanuc + Tesollo MoveIt Cell

ROS 2 packages to attach the Tesollo DG-3FB gripper to a Fanuc M-20iD/35 and run MoveIt with a planning scene.

## Packages

| Package | Role |
|---------|------|
| `fanuc_tesollo_description` | Combined URDF: Fanuc `m20_35_18d` + Delto 3F + mount transforms |
| `df3fb_moveit_config` | MoveIt SRDF, controllers, demo launch, planning scene setup |

The original `launch/gripper_*.py` notes were design stubs. The working MoveIt stack lives in these two packages.

## Quick start (on robot PC with ROS 2 Humble)

```bash
bash external/gripper_ros_driver/scripts/setup_moveit_workspace.bash ~/ws_fanuc_tesollo
source ~/ws_fanuc_tesollo/install/setup.bash
ros2 launch df3fb_moveit_config demo.launch.py
```

This starts:

- Mock `ros2_control` (arm + 12 gripper joints) — no real hardware required
- `move_group` with planning groups: **arm**, **gripper**, **arm_with_gripper**
- RViz with MotionPlanning
- Planning scene: table, pick/place bins, placeholder objects

## MoveIt groups

| Group | Joints | Use |
|-------|--------|-----|
| `arm` / `manipulator` | J1–J6 | Reach poses; tip = `ee_link` |
| `gripper` | F1M1–F3M4 | Finger trajectories, named states `gripper_open`, `gripper_ball` |
| `arm_with_gripper` | All 18 | Combined planning |

End-effector frame for pick/place: **`tesollo_tool0`** (230 mm above palm per Tesollo default TCP).

## Tune gripper mount

Edit `fanuc_tesollo_description/config/gripper_mount.yaml` then rebuild:

```yaml
gripper_mount:
  xyz: "0 0 0"    # ee_link -> delto_base_link
  rpy: "0 0 0"
tesollo_palm:
  xyz: "0 0 0.23"
  rpy: "0 0 0"
```

## Next steps (real hardware)

1. Replace mock `ros2_control` with Fanuc hardware interface + Modbus gripper driver (see `docs/gripper/tesollo_gripper_control_comparison.md`).
2. Launch with real controllers instead of `demo.launch.py` mock stack.
3. Regenerate SRDF collision matrix in MoveIt Setup Assistant if needed.

See `docs/gripper/moveit_integration.md` for full integration guide.
