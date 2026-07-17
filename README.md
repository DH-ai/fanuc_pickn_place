FANUC M-20iD/35 Pick n Place 
# FANUC M-20iD/35 ROS 2 Pick-and-Place
 
ROS 2 integration for a **FANUC M-20iD/35**, NVIDIA Jetson, Tesollo
DG-3FB gripper, Mech-Eye 3D camera, force sensing, and MoveIt 2.
 
> **Safety:** Validate the robot model, payload, TCP, joint limits, trajectory,
> and cell clearance before physical motion. Start in mock mode, then test at
> low speed under qualified supervision with an emergency stop available.

## [Documentaion](https://github.com/DH-ai/fanuc_pickn_place/tree/main/docs#readme)



Next Follow for ML pipiline - [Synthetic-Data-Yolo_training-and-pose-estimation](https://github.com/DH-ai/synthetic-data-yolo-training_and_pose_estimation/blob/main/README.md)


## Current project status
 
| Area | Status |
|------|--------|
| Target robot | **FANUC M-20iD/35** (`m20_35_18d`) |
| Controller | Software recorded as `V9.40P/81`; reconfirm controller family and options on the teach pendant |
| Jetson | ROS 2 workspace was built and used for robot/peripheral networking; model and JetPack version still need recording |
| Robot network | Jetson ↔ controller communication was observed on May 25 |
| MoveIt model | Combined M-20iD/35 + Tesollo DG-3FB model and mock MoveIt demo are present |
| Real M-20 driver launch | **Not complete on current `main`**; vendored hardware launch files still accept CRX models only |
| Gripper | Standalone Modbus test exists; full ROS 2 hardware driver remains incomplete |
| Force sensor | Live readings were reported, but no force-sensor ROS package is present on current `main` |
| Mech-Eye | Photos were captured; current repo contains sample data/viewer and pipeline design, not the live ROS driver |
| Open robot issue | `MOTN-017 Limit error (G:1, A:6)` needs a verified root cause |
 
