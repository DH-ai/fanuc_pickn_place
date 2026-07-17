# FANUC M-20iD/35 Notes

This document contains development notes, configuration details, lessons learned, useful commands, and known issues encountered while integrating the FANUC M-20iD/35 with ROS 2.

---

# Robot Information

| Item                | Value           |
| ------------------- | --------------- |
| Robot               | FANUC M-20iD/35 |
| Model               | m20_35_18d      |
| Controller Software | V9.40P/81       |
| Framework           | ROS 2           |
| Motion Planning     | MoveIt 2        |

---

# Project Progress

## Initial Setup

* Learned the basics of the FANUC Teach Pendant (TP).
* Explored multiple FANUC ROS 2 drivers and compared their compatibility.
* Installed the FANUC ROS 2 driver on the NVIDIA Jetson.
* Created the project GitHub repository.
* Prepared and shared an 8-week milestone plan with mentors.

---

## ROS 2 Environment

* Successfully built the FANUC ROS workspace.
* Reinstalled the complete ROS environment on the Jetson after configuration issues.
* Replicated the workspace inside a Docker container running Ubuntu 22.04 for debugging and reproducibility.
* Identified build warnings caused by unused parameters.

Useful compiler flag:

```bash
-DCMAKE_CXX_FLAGS="-Wno-unused-parameter"
```

---

## Network Configuration

Successfully configured communication between industrial devices.

Completed:

* Jetson ↔ FANUC controller communication
* Network infrastructure setup
* Cable management
* Device labeling cleanup

One of the most time-consuming parts of the project was configuring reliable networking between all industrial hardware.

---

## Hardware Bring-up

Successfully configured:

* FANUC robot communication
* Tesollo DG-3FB gripper communication
* Force sensor readings
* Mech-Eye 3D camera image capture

Configuration Phase 1 was completed after verifying communication with all hardware components.

---

## Mech-Eye Camera

Successfully captured images from the camera.

While configuring the ROS interface, the following error was encountered:

```text
Failed to obtain the IP address of the computer Ethernet port connected to the device.
```

Setup consisted of multiple devices connected through a network switch, which likely caused interface detection issues.

---

## MoveIt 2

Created a custom MoveIt configuration for the FANUC M-20iD/35.

Important note:

The FANUC workspace must be sourced before launching the MoveIt Setup Assistant because the robot URDF references packages inside `fanuc_description`.

Example:

```bash
source install/setup.bash

moveit_setup_assistant
```

---

## Jetson Build Optimization

Because of limited RAM on the Jetson, the workspace should be built sequentially.

Recommended command:

```bash
MAKEFLAGS="-j4 -l1" colcon build \
    --mixin release \
    --executor sequential
```

This significantly reduces memory usage during compilation.

---

## Driver Compatibility

The robot controller is running:

```
V9.40P/81
```

The newer FANUC ROS 2 drivers were designed for newer controller software and were not fully compatible.

To resolve this:

* Evaluated multiple FANUC driver repositories.
* Switched to the older ROS 2 Driver v1.x series.
* Planned incremental testing across releases until identifying the latest compatible version.

---

## Hardware Interface

Implemented a custom hardware interface after determining the existing driver only supported CRX robots.

Completed work:

* Rewrote the FANUC hardware interface.
* Created a custom MoveIt configuration.
* Successfully controlled the M-20iD/35 through ROS 2.

---

## Gripper

* Successfully established communication with the Tesollo DG-3FB.
* Standalone control was verified.
* Further ROS package development is required for complete integration.

---

## Force Sensor

* Successfully received live force sensor readings.
* Integration into the ROS pipeline remains future work.

---

## Useful Commands

### Source Workspace

```bash
source install/setup.bash
```

### Build Workspace

```bash
MAKEFLAGS="-j4 -l1" colcon build \
    --mixin release \
    --executor sequential
```

---

## Documentation

📚 Follow the complete project documentation here:

- **FANUC Pick-and-Place Documentation:** https://github.com/DH-ai/fanuc_pickn_place/tree/main/docs#readme

---

## Synthetic Data & Machine Learning Pipeline

The perception pipeline (Synthetic Data → YOLO Training → 6D Pose Estimation) is maintained in a separate repository.

➡️ **Follow the complete ML pipeline here:**

https://github.com/DH-ai/synthetic-data-yolo-training_and_pose_estimation/blob/main/README.md

---

## Known Issues

### MOTN-017 Limit Error

Robot alarm:

```text
MOTN-017 Limit error (G:1, A:6)
```

Status:

* Root cause not yet confirmed.
* Appears to be a robot/controller-side issue rather than a ROS issue.

---
