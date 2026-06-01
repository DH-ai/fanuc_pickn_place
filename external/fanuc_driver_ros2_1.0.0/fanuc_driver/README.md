<!-- SPDX-FileCopyrightText: 2025 FANUC America Corp.
     SPDX-FileCopyrightText: 2025 FANUC CORPORATION

     SPDX-License-Identifier: Apache-2.0
-->
<!-- markdownlint-disable MD013 -->
# fanuc_driver

## About

This repository hosts the source code of the FANUC ROS 2 Driver project.
This project will allow users to develop a ROS 2 application to control a
FANUC virtual or real robot.

## System Requirements

- **Operating System:** Ubuntu 22.04 LTS with real-time kernel (PREEMPT_RT) installed
- **ROS 2 Distribution:** Humble Hawksbill
- **FANUC Robot Controller:** R-30iB Mini Plus
- **FANUC Robot:** CRX series

## Instructions

### Installation

```bash
echo "Installing and configuring git-lfs"
sudo apt install git-lfs
git lfs install

echo "Checking out GitHub repositories"
mkdir ~/ws_fanuc/src -p
cd ~/ws_fanuc/src
git clone git@github.com:FANUC-CORPORATION/fanuc_description.git
git clone --recurse-submodules git@github.com:FANUC-CORPORATION/fanuc_driver.git

echo "Installing FANUC dependencies"
cd ~/ws_fanuc
sudo apt update
rosdep update
rosdep install --ignore-src --from-paths src -y

echo "Building FANUC libraries"
colcon build --symlink-install --cmake-args -DBUILD_TESTING=1 -DBUILD_EXAMPLES=1
```

### Launching with Mock Hardware

The `fanuc_moveit` launch file starts ROS processes to control a URDF model using ros2_control and MoveIt2.

```bash
source install/setup.bash
ros2 launch fanuc_moveit_config fanuc_moveit.launch.py robot_model:=crx10ia use_mock:=true
```

![Starting RViz view after running view_crx.launch.py.](/images/joint_state_publisher.png "RViz with JointStatePublisher")

RViz will launch with a visualization of the CRX-10iA.

![Starting RViz view after running fanuc_moveit.launch.py.](/images/mock_hw_start.png "Starting RViz view")

Drag the 3D arrows to set a goal pose for the robot.
Then click `Plan & Execute` to simulate the robot planning and executing a trajectory to the goal.

![RViz view after moving IMarker.](/images/mock_hw_trajectory.png "Dragging IMarker")

### Dynamically scaling trajectory execution

The `fanuc_moveit` launch file configures a Scaled Joint Trajectory Controller (SJTC), which enables us to slow down and pause trajectories while they are executed.

Set the trajectory speed scaling factor to 10% by setting the Slider Publisher value.
Drag the IMarker to a new location and click `Plan & Execute`.
The robot will move slowly to the goal.
Now, set the speed scaling factor to 0% and see it pause its motion.
Set it back to 100% and the robot will complete the remainder of the trajectory at its nominal speed.

## Launching with Physical Hardware

Now we will use the same `fanuc_moveit` launch file, but provide a different set of arguments that will use the physical hardware interface instead of mock hardware.

### Network Setup

First we will now set IP addresses for each of the ethernet connections.

If your computer has two network interfaces (one to connect to the Internet and another to connect to robot controller) each needs a different connection profile.
To set these up, click the arrow at the upper right corner of the screen, and then click "Settings" > "Network".

First, unplug the ethernet cable between the computer and your network infrastructure.
One of the two Wired interfaces will now show up as "Cable unplugged".
Click the gear icon next to that Wired adapter.

- Under the "Identity" tab, give this profile a name (like "Internet").
- Click "Apply" to accept the default values for the other settings.
- Plug the ethernet cable back in.

Now, click the gear icon next to the other network adapter.

- Under the "Identity" tab, assign a name to the connection profile, such as "Robot".
- Under the "IPv4" tab, select "Manual" as the "IPv4 Method".
- Enter `192.10.1.100` for the Address, and `255.255.255.0` for the Netmask.
- Click "Apply".

Adjust the following launch command with the IP for your robot.

```bash
source install/setup.bash
ros2 launch fanuc_moveit_config fanuc_moveit.launch.py robot_model:=crx10ia robot_ip:="192.168.1.100"
```

## Licensing

The original FANUC ROS 2 Driver source code and associated documentation
including these web pages are Copyright (C) 2025 FANUC America Corporation
and FANUC CORPORATION.

Any modifications or additions to source code or documentation
contributed to this project are Copyright (C) the contributor,
and should be noted as such in the comments section of the modified file(s).

FANUC ROS 2 Driver is licensed under
     [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)

Exceptions:

- The sockpp library is licensed under the terms of the [BSD 3-Clause License](https://opensource.org/license/BSD-3-Clause).

- The readwriterqueue library is licensed under the terms of
  the [Simplified BSD License](https://opensource.org/license/BSD-2-Clause).

- The reflect-cpp and yaml-cpp libraries are licensed under the
  terms of the [MIT License](https://opensource.org/license/mit).

Please see the LICENSE folder in the root directory for the full texts of these licenses.
