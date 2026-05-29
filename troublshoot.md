bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py robot_model:=m20_35-18d robot_series:=m20 moveit_config:=fanuc_m20_moveit_config use_mock:=true

[INFO] [launch]: All log files can be found below /home/bajajauto/.ros/log/2026-05-29-19-38-48-561595-bajajauto-desktop-54750

[INFO] [launch]: Default logging verbosity is set to INFO

WARNING:root:"File /home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro doesn't exist"

WARNING:root:The robot description will be loaded from /robot_description topic 

Using load_yaml() directly is deprecated. Use xacro.load_yaml() instead.

[ERROR] [launch.actions.declare_launch_argument]: Argument "robot_model" provided value "m20_35-18d" is not valid. Valid options are: ['crx5ia', 'crx10ia', 'crx10ia_l', 'crx20ia_l', 'crx30ia']

[ERROR] [launch]: Caught exception in launch (see debug for traceback): Argument "robot_model" provided value "m20_35-18d" is not valid. Valid options are: ['crx5ia', 'crx10ia', 'crx10ia_l', 'crx20ia_l', 'crx30ia']

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ 

how can this error come if my fanuc_moveit_template.launch file has this specific code ef generate_launch_description():

    declared_arguments = [

        DeclareLaunchArgument(

            "robot_model",

            description="The robot model (required).",

        ),

        DeclareLaunchArgument(

            "robot_series",

            description="The robot model (required).",

        ),

        DeclareLaunchArgument(

            "moveit_config",

            description="The package name for moveit config (required).",

        ),

        DeclareLaunchArgument(

            "robot_ip",

            default_value="192.168.0.20",

            description="The robot's IP address.",

        ),

        DeclareLaunchArgument(

            "ros2_control_config",

            default_value=PathJoinSubstitution(

                [

                    FindPackageShare("fanuc_hardware_interface"),

                    "config",

                    "example_ros2_controllers.yaml",

                ]

            ),

            description="ROS 2 control configuration file the controllers.",

        ),

        DeclareLaunchArgument(

            "gpio_configuration",

            default_value=PathJoinSubstitution(

                [

                    FindPackageShare("fanuc_hardware_interface"),

                    "config",

                    "example_gpio_config_small.yaml",

                ]

            ),

            description="YAML file configuration to specify the GPIO configuration..",

        ),

        DeclareLaunchArgument(

            "use_mock",

            default_value="false",

            description="Whether to use a mock hardware interface.",

        ),

    ]



    return LaunchDescription(

        declared_arguments + [OpaqueFunction(function=launch_setup)]

    )

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ 

It looks like you are running into a common ROS 2 launch trap: the "Shadowed Launch File" or "Outdated Install" problem.

Even though your .py source file in the src directory looks correct (allowing any string for robot_model), the ROS 2 launch system is executing the installed version of that file, which likely contains validation logic or choice restrictions.

Here is why this is happening and how to fix it:

1. The Validation Mismatch
The error message Valid options are: ['crx5ia', ...] is very specific. This happens when a DeclareLaunchArgument has a choices parameter set.

While the code you pasted doesn't show a choices list, the terminal output confirms that the launch system is seeing one. This means:

You might be editing the file in ~/ws_fanuc_1.0.0/src/... but the system is running the one in ~/ws_fanuc_1.0.0/install/....

Or, the choices logic is hidden inside the launch_setup OpaqueFunction or a helper script being called by the launch file.

2. Immediate Solution: Rebuild and Source
The most likely culprit is that you modified your source code but didn't update the install folder.

Clean and Rebuild:

cd ~/ws_fanuc_1.0.0
colcon build --packages-select fanuc_m20_moveit_config --symlink-install

    *(Using `--symlink-install` allows you to edit Python files in `src` and see changes without rebuilding every time).*

2.  **Source the Workspace:**
    ```bash
source install/setup.bash

Verify the Launch File:
Run this command to see exactly what the installed file contains:

cat ~/ws_fanuc_1.0.0/install/fanuc_m20_moveit_config/share/fanuc_m20_moveit_config/launch/fanuc_moveit_template.launch.py


---

### 3. Check for Hidden Logic in `launch_setup`
If the installed file matches your source and you still get the error, the validation is happening inside the **`OpaqueFunction(function=launch_setup)`**.

In many Fanuc ROS 2 packages, the `launch_setup` function calls a helper function (like `get_robot_description`) that includes a hardcoded check for supported models. 

**Look for a line like this in your `launch_setup` function:**
```python
# Check if there is logic similar to this inside launch_setup:
if robot_model not in ['crx5ia', 'crx10ia', ...]:
    raise LaunchConfigurationError("Argument 'robot_model' provided value is not valid...")
4. The URDF Path Warning
Even if you fix the launch argument, you have another issue flagged in your logs:
"File .../m20_35-18d.urdf.xacro doesn't exist"

This suggests that while you are passing m20_35-18d as an argument, the package fanuc_hardware_interface does not actually have that XACRO file in its robot folder.

To fix this:

Ensure the file m20_35-18d.urdf.xacro exists in src/fanuc_hardware_interface/robot/.

Check for typos (e.g., underscores vs dashes).

Summary Checklist
[ ] Did you rebuild and source after editing the launch file?

[ ] Is there a choices=[...] argument hidden in a different part of the script?

[ ] Does the launch_setup function contain a manual if/else check for the robot model?

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ cat ../.ros/log/2026-05-29-20-57-56-613843-bajajauto-desktop-66946/launch.log 

1780068476.6168704 [INFO] [launch]: All log files can be found below /home/bajajauto/.ros/log/2026-05-29-20-57-56-613843-bajajauto-desktop-66946

1780068476.6173613 [INFO] [launch]: Default logging verbosity is set to INFO

1780068477.0167253 [ERROR] [launch.actions.declare_launch_argument]: Argument "robot_model" provided value "m20_35-18d" is not valid. Valid options are: ['crx5ia', 'crx10ia', 'crx10ia_l', 'crx20ia_l', 'crx30ia']

1780068477.0189133 [ERROR] [launch]: Caught exception in launch (see debug for traceback): Argument "robot_model" provided value "m20_35-18d" is not valid. Valid options are: ['crx5ia', 'crx10ia', 'crx10ia_l', 'crx20ia_l', 'crx30ia']

The log confirms that the error is occurring at the declaration stage (specifically in launch.actions.declare_launch_argument). This is a "smoking gun" that proves the code you are running is fundamentally different from the code you showed me.

In ROS 2, DeclareLaunchArgument will only throw that specific "not valid" error if the choices parameter is populated. Since your snippet doesn't have it, the system is executing an old or different version of the file.

The Fix: Force an Update
Run these commands in order to purge any cached or mismatched build artifacts:

Bash
cd ~/ws_fanuc_1.0.0
# 1. Remove old build/install artifacts for this package
rm -rf build/fanuc_m20_moveit_config/ install/fanuc_m20_moveit_config/

# 2. Rebuild with symlink-install (crucial for Python launch files)
colcon build --packages-select fanuc_m20_moveit_config --symlink-install

# 3. Source the workspace again
source install/setup.bash

# 4. Try the launch again
ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py \
    robot_model:=m20_35-18d \
    robot_series:=m20 \
    moveit_config:=fanuc_m20_moveit_config \
    use_mock:=true
Why is this happening?
There are three likely scenarios:

1. The "Shadow" Package
You might have a version of fanuc_m20_moveit_config installed in your underlay (e.g., /opt/ros/humble/... or a different workspace). When you run ros2 launch, it might be picking up the "official" CRX-only version instead of your modified M20 version.

Check this with: ros2 pkg prefix fanuc_m20_moveit_config

It should point to ~/ws_fanuc_1.0.0/install/fanuc_m20_moveit_config. If it points to /opt/ros/..., your local workspace isn't sourced correctly.

2. The setup.py Trap
If you added fanuc_moveit_template.launch.py to your src folder but didn't list it in the data_files section of your setup.py, colcon build won't copy the new version to the install folder.

Check your setup.py: Ensure it includes:

(os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),


#### 3. Validation inside `launch_setup`
Even though your `DeclareLaunchArgument` looks clean, if the `launch_setup` function (which you've passed into `OpaqueFunction`) contains logic that checks the `robot_model` string against a list, it will crash. 

Look further down in your `fanuc_moveit_template.launch.py` file for the `launch_setup` definition and see if it looks like this:
```python
def launch_setup(context, *args, **kwargs):
    robot_model = LaunchConfiguration("robot_model").perform(context)
    # If this list exists, you MUST add 'm20_35-18d' to it manually
    valid_models = ['crx5ia', 'crx10ia', 'crx10ia_l', 'crx20ia_l', 'crx30ia']
    if robot_model not in valid_models:
        # This is where the error message is likely being generated
        ...
Recommendation: After rebuilding, search your entire workspace for the string crx5ia to find exactly where that restricted list is hidden:

Bash
grep -r "crx5ia" ~/ws_fanuc_1.0.0/src
Did the colcon build finish without errors, and did the cat command on the installed file show your changes?

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py     robot_model:=m20_35-18d     robot_series:=m20     moveit_config:=fanuc_m20_moveit_config     use_mock:=true

[INFO] [launch]: All log files can be found below /home/bajajauto/.ros/log/2026-05-29-21-09-45-240119-bajajauto-desktop-67628

[INFO] [launch]: Default logging verbosity is set to INFO

Using load_yaml() directly is deprecated. Use xacro.load_yaml() instead.

[ERROR] [launch]: Caught exception in launch (see debug for traceback): executed command failed. Command: /opt/ros/humble/bin/xacro /home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robotm20_35-18d.urdf.xacro robot_ip:=1.1.1.1 use_mock:=true 

Captured stderr output: Traceback (most recent call last):

  File "/opt/ros/humble/local/lib/python3.10/dist-packages/xacro/__init__.py", line 1026, in parse

    inp = f = open(os.path.join(root_dir, filename))

FileNotFoundError: [Errno 2] No such file or directory: '/home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robotm20_35-18d.urdf.xacro'



During handling of the above exception, another exception occurred:



Traceback (most recent call last):

  File "/opt/ros/humble/local/lib/python3.10/dist-packages/xacro/__init__.py", line 1138, in _process

    doc = process_file(input_file_name, **opts)

  File "/opt/ros/humble/local/lib/python3.10/dist-packages/xacro/__init__.py", line 1110, in process_file

    doc = parse(None, input_file_name)

  File "/opt/ros/humble/local/lib/python3.10/dist-packages/xacro/__init__.py", line 1030, in parse

    raise XacroException(e.strerror + ": " + e.filename, exc=e)

xacro.XacroException: No such file or directory: /home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robotm20_35-18d.urdf.xacro [Errno 2] No such file or directory: '/home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robotm20_35-18d.urdf.xacro'



During handling of the above exception, another exception occurred:



Traceback (most recent call last):

  File "/opt/ros/humble/bin/xacro", line 33, in <module>

    sys.exit(load_entry_point('xacro==2.1.1', 'console_scripts', 'xacro')())

  File "/opt/ros/humble/local/lib/python3.10/dist-packages/xacro/__init__.py", line 1190, in main

    _process(input_file_name, vars(opts))

  File "/opt/ros/humble/local/lib/python3.10/dist-packages/xacro/__init__.py", line 1143, in _process

    except xml.parsers.expat.ExpatError as e:

AttributeError: module 'xml' has no attribute 'parsers'

You have successfully moved past the "Invalid Argument" error! Now you are facing a Path Concatenation Error in your launch script.

Look closely at the path in the error message:
.../share/fanuc_hardware_interface/robotm20_35-18d.urdf.xacro

Notice that there is a missing forward slash (/) between the folder name robot and the model name m20_35-18d. The system is looking for a file named robotm20... instead of a file inside the robot/ folder.

The Fix: Update your launch_setup function
Inside your fanuc_moveit_template.launch.py, find the section where the robot_description is being constructed. It likely uses PathJoinSubstitution.

You probably have something like this:

Python
# INCORRECT
robot_description_content = Command(
    [
        PathJoinSubstitution([FindPackageShare("fanuc_hardware_interface"), "robot"]),
        LaunchConfiguration("robot_model"),
        ".urdf.xacro",
        ...
    ]
)
Change it to this:

Python
# CORRECT
robot_description_content = Command(
    [
        PathJoinSubstitution([FindPackageShare("xacro")]), " ",
        PathJoinSubstitution(
            [
                FindPackageShare("fanuc_hardware_interface"),
                "robot",  # The folder
                PythonExpression(["'", LaunchConfiguration("robot_model"), ".urdf.xacro'"]) # The filename
            ]
        ),
        " robot_ip:=", LaunchConfiguration("robot_ip"),
        " use_mock:=", LaunchConfiguration("use_mock"),
    ]
)
Alternative: Quick Fix in the Launch Command
If you want to test if this is the only issue without changing the code yet, you can try adding a leading slash to your command line argument (though this is a "dirty" fix):

Bash
ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py \
    robot_model:=/m20_35-18d \
    robot_series:=m20 \
    moveit_config:=fanuc_m20_moveit_config \
    use_mock:=true
Why the AttributeError?
The AttributeError: module 'xml' has no attribute 'parsers' at the end of your log is a side effect. When xacro fails to find a file, it tries to handle the exception and sometimes runs into a secondary issue with Python's XML library in certain ROS 2 Humble environments. Ignore this for now; once the file path is correct, this error will disappear.

To-Do List:
Check the path: Ensure the file m20_35-18d.urdf.xacro is actually inside ~/ws_fanuc_1.0.0/src/fanuc_hardware_interface/robot/.

Fix the Slash: Edit the launch file to ensure PathJoinSubstitution correctly joins the robot directory and the .xacro filename with a separator.

Rebuild: Run colcon build --packages-select fanuc_m20_moveit_config fanuc_hardware_interface.

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ cat src/fanuc_driver/fanuc_hardware_interface/launch/fanuc_mock_control.launch.py 

# SPDX-FileCopyrightText: 2025, FANUC America Corporation

# SPDX-FileCopyrightText: 2025, FANUC CORPORATION

#

# SPDX-License-Identifier: Apache-2.0



from launch import LaunchDescription

from launch.actions import (

    DeclareLaunchArgument,

    OpaqueFunction,

    ExecuteProcess,

)

from launch.conditions import IfCondition

from launch.substitutions import (

    Command,

    FindExecutable,

    LaunchConfiguration,

    PathJoinSubstitution,

)

from launch_ros.parameter_descriptions import ParameterValue

from launch_ros.actions import Node

from launch_ros.substitutions import FindPackageShare





def launch_setup(context, *args, **kwargs):

    robot_model = LaunchConfiguration("robot_model")

    ros2_control_config = LaunchConfiguration("ros2_control_config")

    launch_rviz = LaunchConfiguration("launch_rviz")



    robot_description = Command(

        [

            PathJoinSubstitution([FindExecutable(name="xacro")]),

            " ",

            PathJoinSubstitution(

                [FindPackageShare("fanuc_hardware_interface"), "robot", ""]

            ),

            robot_model,

            ".urdf.xacro",

            " ",

            "robot_ip:=1.1.1.1",

            " ",

            "use_mock:=true",

            " ",

        ]

    )

    robot_description = {

        "robot_description": ParameterValue(value=robot_description, value_type=str)

    }



    ros_parameters = [robot_description, ros2_control_config]

    nodes_to_launch = []

    control_node = Node(

        package="controller_manager",

        executable="ros2_control_node",

        parameters=ros_parameters,

        output="both",

    )

    nodes_to_launch.append(control_node)



    robot_state_pub_node = Node(

        package="robot_state_publisher",

        executable="robot_state_publisher",

        output="both",

        parameters=[robot_description],

    )

    nodes_to_launch.append(robot_state_pub_node)



    rviz_file = PathJoinSubstitution(

        [FindPackageShare("fanuc_crx_description"), "rviz", "view_crx.rviz"]

    )

    rviz_node = Node(

        package="rviz2",

        executable="rviz2",

        name="rviz2",

        output="both",

        arguments=["--display-config", rviz_file],

        condition=IfCondition(launch_rviz),

    )

    nodes_to_launch.append(rviz_node)



    slider_test_node = Node(

        package="slider_publisher",

        executable="slider_gui_node",

        name="slider_gui_node",

        output="both",

    )

    nodes_to_launch.append(slider_test_node)



    controller_spawner_processes = [

        ExecuteProcess(

            cmd=[

                "ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster"

            ],

            shell=True,

            output="screen",

        ),

        ExecuteProcess(

            cmd=[

                "ros2 run controller_manager spawner --controller-manager-timeout 180 joint_trajectory_controller"

            ],

            shell=True,

            output="screen",

        ),

        ExecuteProcess(

            cmd=[

                "ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller"

            ],

            shell=True,

            output="screen",

        ),

    ]



    return nodes_to_launch + controller_spawner_processes





def generate_launch_description():

    declared_arguments = [

        DeclareLaunchArgument(

            "robot_model",

            description="The robot model (required).",

            # choices=["crx5ia", "crx10ia", "crx10ia_l", "crx20ia_l", "crx30ia"],

        ),

        DeclareLaunchArgument(

            "ros2_control_config",

            default_value=PathJoinSubstitution(

                [

                    FindPackageShare("fanuc_hardware_interface"),

                    "config",

                    "ros2_controllers.yaml",

                ]

            ),

            description="ROS 2 control configuration file the controllers.",

        ),

        DeclareLaunchArgument(

            "launch_rviz",

            default_value="true",

            description="Specify whether or not to open RVIZ.",

        ),

    ]



    return LaunchDescription(

        declared_arguments + [OpaqueFunction(function=launch_setup)]

    )

bajajaut

I see exactly where the bug is hiding. It’s a subtle interaction between PathJoinSubstitution and how Python strings are being appended in your Command list.

In your fanuc_mock_control.launch.py, look at this block:

Python
PathJoinSubstitution(
    [FindPackageShare("fanuc_hardware_interface"), "robot", ""]
),
robot_model,
".urdf.xacro",
The Problem
When PathJoinSubstitution finishes, it creates a path. By adding "" (an empty string) at the end of the list, it ensures the path ends in a folder-level string, but the very next item in your Command list is robot_model.

Because robot_model and ".urdf.xacro" are raw LaunchConfiguration and string objects outside of a PathJoinSubstitution call, the Command action concatenates them literally. If the substitution evaluates to /.../robot/ and your model is m20_35-18d, it should work, but because of how PathJoinSubstitution handles the trailing slash, it’s resulting in /.../robotm20_35-18d.

The Fix
You should wrap the model and extension inside the PathJoinSubstitution so ROS handles the slashes correctly. Change your robot_description block to this:

Python
    robot_description = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [
                    FindPackageShare("fanuc_hardware_interface"), 
                    "robot", 
                    PythonExpression(["'", robot_model, ".urdf.xacro'"])
                ]
            ),
            " ",
            "robot_ip:=1.1.1.1",
            " ",
            "use_mock:=true",
            " ",
        ]
    )
Why this works:
PythonExpression: This evaluates 'm20_35-18d' + '.urdf.xacro' into a single filename string first.

PathJoinSubstitution: It then takes the package path, the robot folder, and that new filename, and joins them using the correct system slashes (/).

One more thing to check
The error also shows:
FileNotFoundError: .../install/fanuc_hardware_interface/share/fanuc_hardware_interface/robotm20_35-18d.urdf.xacro

Even after you fix the slash, ensure the file exists at:
~/ws_fanuc_1.0.0/src/fanuc_driver/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro

If the folder in your src is named urdf instead of robot, update the launch file accordingly.

Final Step:
Since you are editing a file in src/fanuc_driver/fanuc_hardware_interface/..., make sure to build that specific package:

Bash
colcon build --packages-select fanuc_hardware_interface --symlink-install
source install/setup.bash
Give that a shot—it should resolve the FileNotFoundError and the path smashing!



bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py     robot_model:=m20_35-18d     robot_series:=m20     moveit_config:=fanuc_m20_moveit_config     use_mock:=true

[INFO] [launch]: All log files can be found below /home/bajajauto/.ros/log/2026-05-29-21-27-59-676306-bajajauto-desktop-69100

[INFO] [launch]: Default logging verbosity is set to INFO

[ERROR] [launch]: Caught exception in launch (see debug for traceback): No such file or directory: /home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/m20_35-18d.ros2_control.xacro [Errno 2] No such file or directory: '/home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/m20_35-18d.ros2_control.xacro'

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py     robot_model:=m20_35-18d     robot_series:=m20     moveit_config:=fanuc_m20_moveit_config     use_mock:=true

[INFO] [launch]: All log files can be found below /home/bajajauto/.ros/log/2026-05-29-21-28-15-473166-bajajauto-desktop-69121

[INFO] [launch]: Default logging verbosity is set to INFO

Using load_yaml() directly is deprecated. Use xacro.load_yaml() instead.

[ERROR] [launch]: Caught exception in launch (see debug for traceback): [Errno 2] No such file or directory: '/home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/initial_positions.yaml' 

when evaluating expression 'load_yaml(initial_positions_file)['initial_positions']' 

when evaluating expression 'initial_positions['J1']'

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py     robot_model:=m20_35-18d     robot_series:=m20     moveit_config:=fanuc_m20_moveit_config     use_mock:=true

[INFO] [launch]: All log files can be found below /home/bajajauto/.ros/log/2026-05-29-21-28-30-370397-bajajauto-desktop-69143

[INFO] [launch]: Default logging verbosity is set to INFO

Using load_yaml() directly is deprecated. Use xacro.load_yaml() instead.

[ERROR] [launch]: Caught exception in launch (see debug for traceback): executed command showed stderr output. Command: /opt/ros/humble/bin/xacro /home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro robot_ip:=1.1.1.1 use_mock:=true 

Captured stderr output:

warning: Using load_yaml() directly is deprecated. Use xacro.load_yaml() instead.

well i copy pasted the files at correct places now wtf is wrong

I feel your frustration—this is the "classic" Xacro chain reaction. You fixed the path, so now Xacro is actually opening the file, but as it reads the code, it's finding internal references to other files that don't exist or are incorrectly named.

The error [Errno 2] No such file or directory: '.../initial_positions.yaml' inside a Xacro execution means the .urdf.xacro file contains a line trying to load_yaml a file that isn't where it expects it to be.

Here is the "WTF" breakdown of what's happening and how to fix it:

1. The initial_positions.yaml Missing Link
In Fanuc's ROS 2 templates, the main Xacro file usually tries to load default joint positions.

The Problem:
Inside your m20_35-18d.urdf.xacro, there is likely a line like this:

XML
<xacro:property name="initial_positions_file" default="$(find fanuc_hardware_interface)/robot/initial_positions.yaml" />
Because you moved or renamed files to support the M20, that specific .yaml file is missing from that exact directory in the install space.

The Fix:

Check if initial_positions.yaml exists in src/fanuc_hardware_interface/robot/.

If it doesn't, copy it from one of the CRX folders or create a simple one.

Crucial: After copying, you must run:

colcon build --packages-select fanuc_hardware_interface


---

### 2. The `ros2_control.xacro` Reference
One of your earlier errors mentioned:
`No such file or directory: .../m20_35-18d.ros2_control.xacro`

**The Problem:**
Most Fanuc URDFs are modular. The `m20_35-18d.urdf.xacro` likely has an `<xacro:include>` tag at the bottom pointing to a hardware interface file that you haven't created or renamed yet.

**The Fix:**
Open `m20_35-18d.urdf.xacro` and look for the `<xacro:include>` lines. Ensure the filename it is looking for actually exists in your `src` folder. If the URDF expects `m20_35-18d.ros2_control.xacro`, but your file is named `m20.ros2_control.xacro`, it will crash.

---

### 3. Why it still says "Executed command showed stderr output"
When Xacro says `Captured stderr output: warning: Using load_yaml() directly is deprecated`, it's actually just a warning, but ROS 2 Launch sometimes treats **any** stderr output as a failure if the process exits with a non-zero code. 

The real "killer" is the `AttributeError: module 'xml' has no attribute 'parsers'` which happens when Xacro crashes midway through parsing due to those missing files.

---

### The "Clean Slate" Troubleshooting Steps

1.  **Check the Install Directory directly:**
    Run this to see exactly what files made it into the build:
    ```bash
ls ~/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/
You should see:
*   `m20_35-18d.urdf.xacro`
*   `m20_35-18d.ros2_control.xacro`
*   `initial_positions.yaml`
Verify the setup.py or CMakeLists.txt:
If those files are in your src but not in the install folder after a build, your build system isn't "installing" them.

If using Python/ament_python: Check setup.py under data_files.

If using C++/ament_cmake: Check CMakeLists.txt for an install(DIRECTORY ...) command.

The "Nuclear" Rebuild:
Sometimes symlinks get messy. Clear the deck:

cd ~/ws_fanuc_1.0.0
rm -rf build/ install/ log/
colcon build --symlink-install
source install/setup.bash


**Try running that `ls` command first.** If `initial_positions.yaml` is missing from the `install` folder, that is 100% your culprit. If it's there, we need to check the paths inside the Xacro file itself.
crx10ia_l.urdf.xacro  crx10ia.urdf.xacro  crx20ia_l.urdf.xacro  crx30ia.urdf.xacro  crx5ia.urdf.xacro  initial_positions.yaml  m20_35-18d.ros2_control.xacro  m20_35-18d.urdf.xacro

The files are all there, which is good news. The fact that you are still getting an error during the xacro command—even though the files exist in the install folder—usually points to a path mismatch inside the Xacro file itself.

When Xacro runs, it evaluates $(find fanuc_hardware_interface). If your workspace hasn't updated its environment hooks, it might be looking at an old version of the package or failing to resolve the internal load_yaml path.

The "Smoking Gun" Check
Open your m20_35-18d.urdf.xacro and look for the line that loads initial_positions.yaml. It probably looks like this:

XML
<xacro:arg name="initial_positions_file" default="$(find fanuc_hardware_interface)/robot/initial_positions.yaml"/>
The problem is likely one of two things:

The Path Variable: In some Fanuc templates, the path is constructed using a series variable. If robot_series is set to m20, but the folder structure in the Xacro logic expects crx, it will fail.

The Directory Context: Xacro's load_yaml is very picky about relative vs. absolute paths.

How to fix it
Step 1: Fix the Xacro internal paths
In m20_35-18d.urdf.xacro, find the initial_positions loading logic. Change it to use an absolute path via the find substitution to be safe:

XML
<!-- Ensure it looks exactly like this -->
<xacro:property name="initial_positions_file" value="$(find fanuc_hardware_interface)/robot/initial_positions.yaml" />
<xacro:property name="initial_positions" value="${xacro.load_yaml(initial_positions_file)['initial_positions']}"/>
Step 2: Debug the Xacro output manually
Instead of launching the whole MoveIt stack (which masks the error), run the Xacro command directly in your terminal. This will show you exactly which line is failing:

Bash
ros2 run xacro xacro ~/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro robot_ip:=1.1.1.1 use_mock:=true
If this command fails: It will print a specific line number in the Xacro file. Look at that line.
If this command succeeds: It will vomit a huge amount of XML text. If that happens, the Xacro is fine, and the issue is how the Launch file is passing the result to MoveIt.

Step 3: Check for the "Double Quote" Trap
In your fanuc_mock_control.launch.py, you have:

Python
robot_description = {
    "robot_description": ParameterValue(value=robot_description, value_type=str)
}
Sometimes, if the Command output contains warnings (like that "load_yaml is deprecated" warning), the ParameterValue gets corrupted with the warning text instead of just the XML.

Try this to clean the output:
In the launch file, you can tell ROS to ignore stderr for the command:

Python
robot_description = Command(
    [
        # ... your existing command parts ...
    ],
    on_stderr='ignore' # Add this to ignore the deprecation warnings
)
Summary of "What is wrong"
The xacro tool is finding the file, but it's crashing while parsing the content of m20_35-18d.urdf.xacro because a load_yaml call inside that file is pointing to a path that Python's os.path doesn't like.

Run the manual ros2 run xacro... command from Step 2. What is the exact error it gives at the very bottom?

Summary: 1 package finished [1.62s]

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py     robot_model:=m20_35-18d     robot_series:=m20     moveit_config:=fanuc_m20_moveit_config     use_mock:=true

[INFO] [launch]: All log files can be found below /home/bajajauto/.ros/log/2026-05-29-21-33-44-588430-bajajauto-desktop-69314

[INFO] [launch]: Default logging verbosity is set to INFO

[ERROR] [launch]: Caught exception in launch (see debug for traceback): name 'xarco' is not defined 

when evaluating expression 'xarco.load_yaml(initial_positions_file)['initial_positions']' 

when evaluating expression 'initial_positions['J1']'

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ ros2 run xacro xacro ~/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro robot_ip:=1.1.1.1 use_mock:=true

name 'xarco' is not defined 

when evaluating expression 'xarco.load_yaml(initial_positions_file)['initial_positions']' 

when evaluating expression 'initial_positions['J1']'

when instantiating macro: m20_35-18d_ros2_control (/home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/m20_35-18d.ros2_control.xacro)

in file: /home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro

[ros2run]: Process exited with failure 2

You’ve found the "WTF" moment! It is a simple, classic typo.

The error message says:
name 'xarco' is not defined

You (or the template) accidentally typed xarco instead of xacro. In the world of programming, that one swapped letter is enough to bring the whole robot down.

The Fix
Open this file:
~/ws_fanuc_1.0.0/src/fanuc_driver/fanuc_hardware_interface/robot/m20_35-18d.ros2_control.xacro
(The error trace shows it's happening inside the m20_35-18d_ros2_control macro).

Search for the word xarco. You will likely find a line that looks like this:

<xacro:property name="initial_positions" value="${xarco.load_yaml(initial_positions_file)['initial_positions']}"/>


3.  Change **`xarco`** to **`xacro`**:
    ```xml
<xacro:property name="initial_positions" value="${xacro.load_yaml(initial_positions_file)['initial_positions']}"/>
Save and Build:

cd ~/ws_fanuc_1.0.0
colcon build --packages-select fanuc_hardware_interface
source install/setup.bash


### Why this happened
Xacro is a Python-based parser. When you use the `${}` syntax, you are writing a small snippet of Python. Xacro provides a built-in object called `xacro` that has the `load_yaml` method. Because of the typo `xarco`, Python looks for an object with that name, can't find it, and throws the `NameError`.

### Verification
Once you fix the typo, run the manual check again. It should now output the full XML instead of an error:
```bash
ros2 run xacro xacro ~/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro robot_ip:=1.1.1.1 use_mock:=true
If that works, your ros2 launch command will finally fly!

[ros2_control_node-1]  F/29

[ros2_control_node-1]  F/30

[ros2_control_node-1]  F/31

[ros2_control_node-1]  F/32

[ros2_control_node-1]  FloatReg/3

[ros2_control_node-1]  FloatReg/4

[ros2_control_node-1]  FloatReg/5

[ros2_control_node-1] ]

[ros2_control_node-1] 

[ros2_control_node-1] [ERROR] [1780071051.388593659] [controller_manager]: Could not switch controllers since prepare command mode switch was rejected.

[ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-6] [ERROR] [1780071051.391100653] [spawner_fanuc_gpio_controller]: Failed to activate controller : fanuc_gpio_controller

[ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-6] [ros2run]: Process exited with failure 1

[ERROR] [ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-6]: process has died [pid 69877, exit code 1, cmd 'ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller'].

[move_group-7] [WARN] [1780071052.319256762] [moveit.plugins.ros_control_interface]: Failed to read controllers from /controller_manager/list_controllers within 3 seconds

[move_group-7] [INFO] [1780071052.322665504] [moveit_ros.trajectory_execution_manager]: Trajectory execution is managing controllers

[move_group-7] [INFO] [1780071052.322753638] [move_group.move_group]: MoveGroup debug mode is ON

[move_group-7] [INFO] [1780071052.373557017] [move_group.move_group]: 

[move_group-7] 

[move_group-7] ********************************************************

[move_group-7] * MoveGroup using: 

You are so close! The robot is "alive," but the Controller Manager is having a disagreement with your hardware interface.

The error prepare command mode switch was rejected usually means the ros2_control node tried to start the GPIO controller, but the hardware interface (your M20 configuration) didn't tell the controller manager that it supports the specific "interfaces" (the inputs/outputs) the controller is looking for.

Why this is happening
Since you switched from a CRX (which has specific built-in tablet/EE I/O) to an M20, there is likely a mismatch between:

The Controller Config: example_gpio_config_small.yaml (which defines which pins to look for).

The XACRO: m20_35-18d.ros2_control.xacro (which defines which pins the hardware actually "offers").

Step 1: Check the GPIO Mismatch
Open your m20_35-18d.ros2_control.xacro. Look for the <gpio name="fanuc_gpio"> section.

If that section is missing or has different names than what the CRX had, the fanuc_gpio_controller will fail to activate because it's looking for "command interfaces" that don't exist in your URDF.

Quick Fix:
If you don't actually need GPIO right now and just want to see the arm move in RViz/Mock mode, you can simply disable the GPIO controller spawner in your launch file:

Open src/fanuc_driver/fanuc_hardware_interface/launch/fanuc_mock_control.launch.py.

Comment out the fanuc_gpio_controller block:

ExecuteProcess(
cmd=[
"ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller"
],
...
),

---

### Step 2: Fix the "Failed to read controllers" Warning
The `move_group` warning `Failed to read controllers from /controller_manager/list_controllers` happens because the `controller_manager` is still "unstable" from the GPIO failure.

Once you disable the GPIO controller (or fix its XACRO entries), the `joint_state_broadcaster` and `joint_trajectory_controller` should turn **green**.

### Step 3: Verify Controller Status
Run the launch again, and in a **separate terminal**, run this command to see what’s actually happening:
```bash
ros2 control list_controllers
If joint_trajectory_controller is active: You can move the robot!

If it is unconfigured or inactive: It means your ros2_controllers.yaml has joint names that don't match the joint names in your m20_35-18d.urdf.xacro.

Checklist for M20 Joint Names
Make sure the names in your m20_35-18d.urdf.xacro (e.g., joint_1, joint_2...) match exactly with the names listed in:

fanuc_m20_moveit_config/config/ros2_controllers.yaml

fanuc_m20_moveit_config/config/joint_limits.yaml

Try disabling the GPIO controller first. It’s the most common "blocker" when porting Fanuc's CRX-designed driver to a standard industrial arm like the M20. Does joint_trajectory_controller show as active after doing that?

[ros2_control_node-1] [ERROR] [1780071448.388917977] [resource_manager]: Not acceptable command interfaces combination: 

[ros2_control_node-1] Start interfaces: 

[ros2_control_node-1] [

[ros2_control_node-1]   DO/101

[ros2_control_node-1]   DO/102

[ros2_control_node-1]   DO/103

[ros2_control_node-1]   DO/104

[ros2_control_node-1]   DO/105

[ros2_control_node-1]   DO/106

[ros2_control_node-1]   DO/107

[ros2_control_node-1]   DO/108

[ros2_control_node-1]   DO/109

[ros2_control_node-1]   DO/110

[ros2_control_node-1]   DO/111

[ros2_control_node-1]   DO/112

[ros2_control_node-1]   RO/1

[ros2_control_node-1]   RO/2

[ros2_control_node-1]   F/1

[ros2_control_node-1]   F/2

[ros2_control_node-1]   F/3

[ros2_control_node-1]   F/4

[ros2_control_node-1]   F/5

[ros2_control_node-1]   F/6

[ros2_control_node-1]   F/7

[ros2_control_node-1]   F/8

[ros2_control_node-1]   F/9

[ros2_control_node-1]   F/10

[ros2_control_node-1]   F/11

[ros2_control_node-1]   F/12

[ros2_control_node-1]   F/13

[ros2_control_node-1]   F/14

[ros2_control_node-1]   F/15

[ros2_control_node-1]   F/16

[ros2_control_node-1]   F/17

[ros2_control_node-1]   F/18

[ros2_control_node-1]   F/19

[ros2_control_node-1]   F/20

[ros2_control_node-1]   F/21

[ros2_control_node-1]   F/22

[ros2_control_node-1]   F/23

[ros2_control_node-1]   F/24

[ros2_control_node-1]   F/25

[ros2_control_node-1]   F/26

[ros2_control_node-1]   F/27

[ros2_control_node-1]   F/28

[ros2_control_node-1]   F/29

[ros2_control_node-1]   F/30

[ros2_control_node-1]   F/31

[ros2_control_node-1]   F/32

[ros2_control_node-1]   FloatReg/3

[ros2_control_node-1]   FloatReg/4

[ros2_control_node-1]   FloatReg/5

[ros2_control_node-1] ]

[ros2_control_node-1] Stop interfaces: 

[ros2_control_node-1] [

[ros2_control_node-1] ]

[ros2_control_node-1] Not existing: 

[ros2_control_node-1] [

[ros2_control_node-1]  DO/101

[ros2_control_node-1]  DO/102

[ros2_control_node-1]  DO/103

[ros2_control_node-1]  DO/104

[ros2_control_node-1]  DO/105

[ros2_control_node-1]  DO/106

[ros2_control_node-1]  DO/107

[ros2_control_node-1]  DO/108

[ros2_control_node-1]  DO/109

[ros2_control_node-1]  DO/110

[ros2_control_node-1]  DO/111

[ros2_control_node-1]  DO/112

[ros2_control_node-1]  RO/1

[ros2_control_node-1]  RO/2

[ros2_control_node-1]  F/1

[ros2_control_node-1]  F/2

[ros2_control_node-1]  F/3

[ros2_control_node-1]  F/4

[ros2_control_node-1]  F/5

[ros2_control_node-1]  F/6

[ros2_control_node-1]  F/7

[ros2_control_node-1]  F/8

[ros2_control_node-1]  F/9

[ros2_control_node-1]  F/10

[ros2_control_node-1]  F/11

[ros2_control_node-1]  F/12

[ros2_control_node-1]  F/13

[ros2_control_node-1]  F/14

[ros2_control_node-1]  F/15

[ros2_control_node-1]  F/16

[ros2_control_node-1]  F/17

[ros2_control_node-1]  F/18

[ros2_control_node-1]  F/19

[ros2_control_node-1]  F/20

[ros2_control_node-1]  F/21

[ros2_control_node-1]  F/22

[ros2_control_node-1]  F/23

[ros2_control_node-1]  F/24

[ros2_control_node-1]  F/25

[ros2_control_node-1]  F/26

[ros2_control_node-1]  F/27

[ros2_control_node-1]  F/28

[ros2_control_node-1]  F/29

[ros2_control_node-1]  F/30

[ros2_control_node-1]  F/31

[ros2_control_node-1]  F/32

[ros2_control_node-1]  FloatReg/3

[ros2_control_node-1]  FloatReg/4

[ros2_control_node-1]  FloatReg/5

[ros2_control_node-1] ]

[ros2_control_node-1] 

[ros2_control_node-1] [ERROR] [1780071448.389093122] [controller_manager]: Could not switch controllers since prepare command mode switch was rejected.



I got this error on running ros2 control  set_controller_state fanuc_gpio_controller active 

 this command in a seperate terminal

The terminal is telling you the exact reason for the "rejection": The controller is asking for hardware pins that your URDF doesn't know exist.

Look at the "Not existing" list in your log. It lists every single I/O pin (DO/101, RO/1, F/1, etc.). Because the fanuc_gpio_controller is trying to claim control over these pins, and the ros2_control resource manager can't find them in your loaded Robot Description, it rejects the "switch" to protect the system.

Here is how to align your M20 setup with the GPIO controller:

1. The Disconnect
The fanuc_gpio_controller is configured (likely in example_gpio_config_small.yaml) to expect a specific set of Fanuc-style I/O. However, your m20_35-18d.ros2_control.xacro either:

Completely lacks a <gpio name="fanuc_gpio"> block.

Or has a block, but the labels inside don't match (e.g., it has digital_output_1 instead of DO/101).

2. The Solution: Update your XACRO
Open src/fanuc_driver/fanuc_hardware_interface/robot/m20_35-18d.ros2_control.xacro. You need to ensure it defines the interfaces the controller wants.

Add (or update) the GPIO block inside the <ros2_control> tag to look like this (abbreviated for brevity):

XML
<gpio name="fanuc_gpio">
  <!-- Digital Outputs -->
  <command_interface name="DO/101"/>
  <command_interface name="DO/102"/>
  <!-- ... repeat for all DOs listed in your error ... -->

  <!-- Robot Outputs -->
  <command_interface name="RO/1"/>
  <command_interface name="RO/2"/>

  <!-- Flags -->
  <command_interface name="F/1"/>
  <!-- ... repeat for all F/ interfaces listed ... -->

  <!-- State Interfaces (Optional but recommended for feedback) -->
  <state_interface name="DI/101"/>
  <state_interface name="RI/1"/>
</gpio>
3. The "I just want it to work" Shortcut
If you are currently just trying to test the motion of the M20 and don't care about the Digital I/O yet, the best move is to stop trying to activate the GPIO controller.

Stop the manual activation: Don't run set_controller_state ... active.

Verify Motion Controllers: Instead, check if your motion controllers are ready:

ros2 control list_controllers

    If `joint_state_broadcaster` and `joint_trajectory_controller` are **active**, you can already plan and execute paths in MoveIt. The GPIO error is a "non-fatal" error for robot movement; it only prevents you from toggling I/O pins.

### Why is it specifically "Not acceptable command interfaces"?
In ROS 2 Control, there is a "Request vs. Offer" handshake:
*   **The Controller (Request):** "I need to write to `DO/101`."
*   **The Hardware/URDF (Offer):** "I only have `joint_1` through `joint_6`."
*   **Result:** `ros2_control` says "Rejected" because the hardware doesn't offer the interface the controller requested.

**Recommendation:** Since you are porting an M20 (Industrial) from a CRX (Collaborative) template, you should probably compare your `ros2_controllers.yaml` with your XACRO. If you don't need those specific Fanuc Flags (`F/1-32`) or Robot Outputs, remove them from the YAML configuration file so the controller stops asking for things that aren't there.
bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$  cat src/fanuc_driver/fanuc_hardware_interface/config/example_gpio_config.yaml 

gpio_topic_config:

  io_state:

    - type: DI

      start: 101

      length: 12

    - type: DO

      start: 101

      length: 12

    - type: RI

      start: 1

      length: 2

    - type: RO

      start: 1

      length: 2

    - type: F

      start: 1

      length: 32

  io_cmd:

    - type: DO

      start: 101

      length: 12

    - type: RO

      start: 1

      length: 2

    - type: F

      start: 1

      length: 32

  num_reg_state:

    - start: 1

      length: 3

  num_reg_cmd:

    - start: 3

      length: 3

look at my gpi o config

Your GPIO configuration is a perfect mirror of the error message you just saw. This YAML file is the "Request"—it tells the fanuc_gpio_controller to go out and find exactly 12 Digital Outputs, 2 Robot Outputs, and 32 Flags.

The problem is that your XACRO (the "Offer") doesn't match this list. To fix the "Not acceptable command interfaces" error, you have to make sure your hardware description provides exactly what this YAML asks for.

The Conflict Mapping
Based on your example_gpio_config.yaml, here is exactly what needs to be in your m20_35-18d.ros2_control.xacro file:

Type	Range	Total Count	Interface Name in XACRO
DO (Digital Out)	101 to 112	12	DO/101, DO/102, ... DO/112
RO (Robot Out)	1 to 2	2	RO/1, RO/2
F (Flags)	1 to 32	32	F/1, F/2, ... F/32
FloatReg	3 to 5	3	FloatReg/3, FloatReg/4, FloatReg/5
How to Fix your XACRO
Open src/fanuc_driver/fanuc_hardware_interface/robot/m20_35-18d.ros2_control.xacro and find the <gpio name="fanuc_gpio"> section. It needs to contain every single interface mentioned in your YAML.

Instead of typing out 50 lines manually, you can use Xacro loops to generate them:

XML
<gpio name="fanuc_gpio">
  <!-- Generate DO 101-112 -->
  <xacro:macro name="gen_do" params="i">
    <command_interface name="DO/${i}"/>
    <state_interface name="DO/${i}"/>
    <xacro:if value="${i < 112}">
      <xacro:gen_do i="${i+1}"/>
    </xacro:if>
  </xacro:macro>
  <xacro:gen_do i="101"/>

  <!-- Generate Flags 1-32 -->
  <xacro:macro name="gen_f" params="i">
    <command_interface name="F/${i}"/>
    <state_interface name="F/${i}"/>
    <xacro:if value="${i < 32}">
      <xacro:gen_f i="${i+1}"/>
    </xacro:if>
  </xacro:macro>
  <xacro:gen_f i="1"/>

  <!-- Manual entries for the smaller sets -->
  <command_interface name="RO/1"/><state_interface name="RO/1"/>
  <command_interface name="RO/2"/><state_interface name="RO/2"/>
  
  <command_interface name="FloatReg/3"/>
  <command_interface name="FloatReg/4"/>
  <command_interface name="FloatReg/5"/>
</gpio>
Alternative: Simplify the Config
If you are working with a real M20 and you don't actually have 32 flags or 12 DOs wired up yet, it is much easier to shrink the YAML to match what is actually in your XACRO.

For example, if you only need 2 Digital Outputs, change the length: 12 to length: 2 in the YAML.

Why did it work for CRX but not M20?
The CRX packages usually come with a very bloated GPIO block in their URDF by default. When you created the m20_35-18d.urdf.xacro, you likely started with a clean/minimal URDF that only defines the joints and forgot to carry over the massive GPIO interface list that the Fanuc driver expects.

Quick Check: If you just want to move the robot arm right now, simply stop trying to activate the fanuc_gpio_controller. If joint_trajectory_controller is active, you are ready to plan paths!

Does ros2 control list_controllers show the joint_trajectory_controller as active?

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ cat ~/ws_fanuc/src/fanuc_driver/fanuc_hardware_interface/config/crx_mock_ros2_control_macro.xacro 

<?xml version="1.0"?>



<robot xmlns:xacro="http://wiki.ros.org/xacro">

  <xacro:macro name="crx_control" params="name prefix=''">

    <ros2_control name="${name}" type="system">

      <joint name="${prefix}J1">

        <command_interface name="position"/>

        <state_interface name="position"/>

        <state_interface name="velocity"/>

      </joint>

      <joint name="${prefix}J2">

        <command_interface name="position"/>

        <state_interface name="position"/>

        <state_interface name="velocity"/>

      </joint>

      <joint name="${prefix}J3">

        <command_interface name="position"/>

        <state_interface name="position"/>

        <state_interface name="velocity"/>

      </joint>

      <joint name="${prefix}J4">

        <command_interface name="position"/>

        <state_interface name="position"/>

        <state_interface name="velocity"/>

      </joint>

      <joint name="${prefix}J5">

        <command_interface name="position"/>

        <state_interface name="position"/>

        <state_interface name="velocity"/>

      </joint>

      <joint name="${prefix}J6">

        <command_interface name="position"/>

        <state_interface name="position"/>

        <state_interface name="velocity"/>

      </joint>



      <gpio name="DI">

        <state_interface name="101"/>

        <state_interface name="102"/>

        <state_interface name="103"/>

        <state_interface name="104"/>

        <state_interface name="105"/>

        <state_interface name="106"/>

        <state_interface name="107"/>

        <state_interface name="108"/>

        <state_interface name="109"/>

        <state_interface name="110"/>

        <state_interface name="111"/>

        <state_interface name="112"/>

      </gpio>



      <gpio name="DO">

        <state_interface name="101"/>

        <state_interface name="102"/>

        <state_interface name="103"/>

        <state_interface name="104"/>

        <state_interface name="105"/>

        <state_interface name="106"/>

        <state_interface name="107"/>

        <state_interface name="108"/>

        <state_interface name="109"/>

        <state_interface name="110"/>

        <state_interface name="111"/>

        <state_interface name="112"/>



        <command_interface name="101"/>

        <command_interface name="102"/>

        <command_interface name="103"/>

        <command_interface name="104"/>

        <command_interface name="105"/>

        <command_interface name="106"/>

        <command_interface name="107"/>

        <command_interface name="108"/>

        <command_interface name="109"/>

        <command_interface name="110"/>

        <command_interface name="111"/>

        <command_interface name="112"/>

      </gpio>



      <gpio name="RO">

        <state_interface name="1"/>

        <state_interface name="2"/>



        <command_interface name="1"/>

        <command_interface name="2"/>

      </gpio>



      <gpio name="RI">

        <state_interface name="1"/>

        <state_interface name="2"/>

      </gpio>



      <gpio name="F">

        <state_interface name="1"/>

        <state_interface name="2"/>

        <state_interface name="3"/>

        <state_interface name="4"/>

        <state_interface name="5"/>

        <state_interface name="6"/>

        <state_interface name="7"/>

        <state_interface name="8"/>

        <state_interface name="9"/>

        <state_interface name="10"/>

        <state_interface name="11"/>

        <state_interface name="12"/>

        <state_interface name="13"/>

        <state_interface name="14"/>

        <state_interface name="15"/>

        <state_interface name="16"/>

        <state_interface name="17"/>

        <state_interface name="18"/>

        <state_interface name="19"/>

        <state_interface name="20"/>

        <state_interface name="21"/>

        <state_interface name="22"/>

        <state_interface name="23"/>

        <state_interface name="24"/>

        <state_interface name="25"/>

        <state_interface name="26"/>

        <state_interface name="27"/>

        <state_interface name="28"/>

        <state_interface name="28"/>

        <state_interface name="29"/>

        <state_interface name="30"/>

        <state_interface name="31"/>

        <state_interface name="32"/>



        <command_interface name="1"/>

        <command_interface name="2"/>

        <command_interface name="3"/>

        <command_interface name="4"/>

        <command_interface name="5"/>

        <command_interface name="6"/>

        <command_interface name="7"/>

        <command_interface name="8"/>

        <command_interface name="9"/>

        <command_interface name="10"/>

        <command_interface name="11"/>

        <command_interface name="12"/>

        <command_interface name="13"/>

        <command_interface name="14"/>

        <command_interface name="15"/>

        <command_interface name="16"/>

        <command_interface name="17"/>

        <command_interface name="18"/>

        <command_interface name="19"/>

        <command_interface name="20"/>

        <command_interface name="21"/>

        <command_interface name="22"/>

        <command_interface name="23"/>

        <command_interface name="24"/>

        <command_interface name="25"/>

        <command_interface name="26"/>

        <command_interface name="27"/>

        <command_interface name="28"/>

        <command_interface name="29"/>

        <command_interface name="30"/>

        <command_interface name="31"/>

        <command_interface name="32"/>

      </gpio>



      <gpio name="FloatReg">

        <command_interface name="1"/>

        <command_interface name="2"/>

        <command_interface name="3"/>

        <command_interface name="4"/>

        <command_interface name="5"/>

        <command_interface name="6"/>

        <state_interface name="1"/>

        <state_interface name="2"/>

        <state_interface name="3"/>

      </gpio>



      <gpio name="ConnectionStatus">

        <state_interface name="is_connected"/>

      </gpio>



      <gpio name="Status">

        <state_interface name="collaborative_speed_scaling"/>

        <state_interface name="contact_stop_mode"/>

        <state_interface name="e_stopped"/>

        <state_interface name="in_error"/>

        <state_interface name="motion_possible"/>

        <state_interface name="tp_enabled"/>

      </gpio>



      <sensor name="Force">

        <state_interface name="force_x"/>

        <state_interface name="force_y"/>

        <state_interface name="force_z"/>

        <state_interface name="moment_x"/>

        <state_interface name="moment_y"/>

        <state_interface name="moment_z"/>

        <state_interface name="fs_type"/>

      </sensor>



      <sensor name="ft_sensor">

        <state_interface name="force.x"/>

        <state_interface name="force.y"/>

        <state_interface name="force.z"/>

        <state_interface name="torque.x"/>

        <state_interface name="torque.y"/>

        <state_interface name="torque.z"/>

      </sensor>



      <hardware>

        <plugin>mock_components/GenericSystem</plugin>

        <param name="state_following_offset">0.0</param>

        <param name="calculate_dynamics">true</param>

      </hardware>

    </ros2_control>

  </xacro:macro>

</robot>

this is how the crx ros control file is written and this is how my file is written

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ cat src/fanuc_driver/fanuc_hardware_interface/config/m20_35-18d.ros2_control.xacro 

<?xml version="1.0"?>

<robot xmlns:xacro="http://www.ros.org/wiki/xacro">

    <xacro:macro name="m20_35-18d_ros2_control" params="name initial_positions_file">

        <xacro:property name="initial_positions" value="${load_yaml(initial_positions_file)['initial_positions']}"/>



        <ros2_control name="${name}" type="system">

            <hardware>

                <!-- By default, set up controllers for simulation. This won't work on real hardware -->

                <plugin>mock_components/GenericSystem</plugin>

            </hardware>

            <joint name="J1">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J1']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <joint name="J2">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J2']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <joint name="J3">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J3']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <joint name="J4">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J4']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <joint name="J5">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J5']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <joint name="J6">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J6']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>



        </ros2_control>

    </xacro:macro>

</robot>

Bingo. That is the exact reason for the Rejected error.

Look at the comparison: your CRX file has massive <gpio> blocks for DI, DO, RO, RI, F, and FloatReg, but your M20 file has absolutely nothing but the 6 joints.

When the fanuc_gpio_controller starts, it looks at your example_gpio_config.yaml, sees you want 32 flags and 12 digital outputs, and then looks at your M20 XACRO. Since your M20 XACRO doesn't "offer" those pins, the Controller Manager refuses to start the controller.

The Fix
You need to copy those <gpio> blocks from the CRX file into your m20_35-18d.ros2_control.xacro, but you have to make a critical adjustment to the naming convention to match what the controller expects.

In the CRX file, the pins are named just by numbers (e.g., <state_interface name="101"/> inside a <gpio name="DO">). The controller manager sees this as DO/101.

Paste this into your m20_35-18d.ros2_control.xacro right after the last <joint> tag but before the </ros2_control> tag:

XML
      <!-- Digital Inputs -->
      <gpio name="DI">
        <xacro:macro name="gen_di" params="i">
          <state_interface name="${i}"/>
          <xacro:if value="${i < 112}">
            <xacro:gen_di i="${i+1}"/>
          </xacro:if>
        </xacro:macro>
        <xacro:gen_di i="101"/>
      </gpio>

      <!-- Digital Outputs -->
      <gpio name="DO">
        <xacro:macro name="gen_do" params="i">
          <state_interface name="${i}"/>
          <command_interface name="${i}"/>
          <xacro:if value="${i < 112}">
            <xacro:gen_do i="${i+1}"/>
          </xacro:if>
        </xacro:macro>
        <xacro:gen_do i="101"/>
      </gpio>

      <!-- Robot I/O -->
      <gpio name="RO">
        <state_interface name="1"/><command_interface name="1"/>
        <state_interface name="2"/><command_interface name="2"/>
      </gpio>
      <gpio name="RI">
        <state_interface name="1"/><state_interface name="2"/>
      </gpio>

      <!-- Flags (1 to 32) -->
      <gpio name="F">
        <xacro:macro name="gen_f" params="i">
          <state_interface name="${i}"/>
          <command_interface name="${i}"/>
          <xacro:if value="${i < 32}">
            <xacro:gen_f i="${i+1}"/>
          </xacro:if>
        </xacro:macro>
        <xacro:gen_f i="1"/>
      </gpio>

      <!-- Float Registers -->
      <gpio name="FloatReg">
        <state_interface name="1"/><state_interface name="2"/><state_interface name="3"/>
        <command_interface name="3"/><command_interface name="4"/><command_interface name="5"/>
      </gpio>
Why use my "Macro" version instead of copy-pasting the CRX file?
The CRX file you showed has a typo in it! Look closely:
 <state_interface name="28"/>
 <state_interface name="28"/>
 <state_interface name="29"/>
It repeats 28 twice and skips a number. If you copy-paste that directly, ROS 2 might complain about duplicate interfaces. My version using the <xacro:macro> loop is cleaner and prevents typos.

One final catch: The Hardware Plugin
Your CRX file has:
<plugin>mock_components/GenericSystem</plugin>

Your M20 file has:
<plugin>mock_components/GenericSystem</plugin>

This is fine for testing (mock mode). However, the GenericSystem mock plugin in older versions of ROS 2 Humble sometimes doesn't know how to handle <gpio> interfaces, which can also cause a rejection.

If it still fails after adding the code above:
Try changing the plugin to the Fanuc-specific hardware interface (if you have it installed) or ensure you are running the launch with use_mock:=true.

Build and try again:

Bash
colcon build --packages-select fanuc_hardware_interface
source install/setup.bash
ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py ...
Does the fanuc_gpio_controller show up as active now when you run ros2 control list_controllers?

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py     robot_model:=m20_35-18d     robot_series:=m20     moveit_config:=fanuc_m20_moveit_config     use_mock:=true

[INFO] [launch]: All log files can be found below /home/bajajauto/.ros/log/2026-05-29-22-06-51-191010-bajajauto-desktop-72331

[INFO] [launch]: Default logging verbosity is set to INFO

[ERROR] [launch]: Caught exception in launch (see debug for traceback): not well-formed (invalid token): line 57, column 37

The error not well-formed (invalid token) means there is a syntax error in your XML (XACRO) file. Specifically, line 57, column 37.

When using the xacro:if logic I gave you, the most common mistake is using the < symbol directly inside the expression. In XML, you cannot use < because the parser thinks you are starting a new tag. You must use the entity &lt; (less than).

The Fix
Open your m20_35-18d.ros2_control.xacro and find the xacro:if lines.

Change this:
 <xacro:if value="${i < 112}">

To this:
 <xacro:if value="${i &lt; 112}">

Corrected Code Block
Update your macros to look exactly like this:

XML
      <!-- Digital Inputs -->
      <gpio name="DI">
        <xacro:macro name="gen_di" params="i">
          <state_interface name="${i}"/>
          <xacro:if value="${i &lt; 112}">
            <xacro:gen_di i="${i+1}"/>
          </xacro:if>
        </xacro:macro>
        <xacro:gen_di i="101"/>
      </gpio>

      <!-- Digital Outputs -->
      <gpio name="DO">
        <xacro:macro name="gen_do" params="i">
          <state_interface name="${i}"/>
          <command_interface name="${i}"/>
          <xacro:if value="${i &lt; 112}">
            <xacro:gen_do i="${i+1}"/>
          </xacro:if>
        </xacro:macro>
        <xacro:gen_do i="101"/>
      </gpio>

      <!-- Flags (1 to 32) -->
      <gpio name="F">
        <xacro:macro name="gen_f" params="i">
          <state_interface name="${i}"/>
          <command_interface name="${i}"/>
          <xacro:if value="${i &lt; 32}">
            <xacro:gen_f i="${i+1}"/>
          </xacro:if>
        </xacro:macro>
        <xacro:gen_f i="1"/>
      </gpio>
Why this happened
In XML/XACRO:

&lt; stands for < (less than)

&gt; stands for > (greater than)

If you use the raw < symbol inside a string value, the XML parser crashes immediately.

One Final Verification
Before launching, run this command to make sure the XML is "well-formed":

Bash
ros2 run xacro xacro ~/ws_fanuc_1.0.0/src/fanuc_driver/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro
If it doesn't throw a "not well-formed" error, you are finally ready to launch.

Did the &lt; fix clear the launch exception?

fanuc_gpio_controller       fanuc_controllers/FanucGPIOController              unconfigured now this and while running moviet inside in logs this error is coming [move_group-7] [INFO] [1780073193.435936475] [moveit.plugins.ros_control_interface]: Using service call timeout 3 seconds

[ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-6] [INFO] [1780073193.463299684] [spawner_fanuc_gpio_controller]: Loaded fanuc_gpio_controller

[ros2_control_node-1] [INFO] [1780073193.469227616] [controller_manager]: Configuring controller 'fanuc_gpio_controller'

[ros2_control_node-1] [ERROR] [1780073193.471428029] [fanuc_gpio_controller]: Caught exception in callback for transition 10

[ros2_control_node-1] [ERROR] [1780073193.471633990] [fanuc_gpio_controller]: Original error: Failed to parse GPIO configuration yaml file with error: Unable to open file '/home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/config/example_gpio_config_small.yaml' or file could not be found.

[ros2_control_node-1] [WARN] [1780073193.471732874] [fanuc_gpio_controller]: Callback returned ERROR during the transition: configure

[ros2_control_node-1] [ERROR] [1780073193.471798797] [controller_manager]: After configuring, controller 'fanuc_gpio_controller' is in state 'unconfigured' , expected inactive.

[ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-6] [ERROR] [1780073193.476054370] [spawner_fanuc_gpio_controller]: Failed to configure controller

We are in the home stretch! The error has shifted from a logic problem to a missing file problem.

The fanuc_gpio_controller is looking for a specific file:
.../share/fanuc_hardware_interface/config/example_gpio_config_small.yaml

However, in your previous cat command, you showed that your file is named:
src/fanuc_driver/fanuc_hardware_interface/config/example_gpio_config.yaml (without the _small).

The Fix
You have two options to resolve this:

Option 1: Rename the file (Recommended)
Rename your YAML file in the source directory to match what the launch file is expecting.

Bash
cd ~/ws_fanuc_1.0.0/src/fanuc_driver/fanuc_hardware_interface/config/
mv example_gpio_config.yaml example_gpio_config_small.yaml
Option 2: Update the Launch File
If you want to keep the name example_gpio_config.yaml, you must tell the launch file to look for that name instead.

Open fanuc_m20_moveit_config/launch/fanuc_moveit_template.launch.py and find the DeclareLaunchArgument for gpio_configuration:

Python
# Change the default_value from:
"example_gpio_config_small.yaml"
# To:
"example_gpio_config.yaml"
Why is it "unconfigured"?
In ROS 2 Control, a controller goes through states: Unconfigured -> Inactive -> Active.

The spawner Loaded the code.

The manager tried to Configure it.

The controller tried to open that YAML file to read the pin mappings.

Because the file wasn't found, the on_configure callback crashed (Transition 10).

The controller fell back to unconfigured.

Rebuild and Verify
After renaming the file or updating the code, you must rebuild so the file is copied to the install directory:

Bash
cd ~/ws_fanuc_1.0.0
colcon build --packages-select fanuc_hardware_interface --symlink-install
source install/setup.bash
Double check the install folder before launching:

Bash
ls ~/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/config/
Ensure example_gpio_config_small.yaml (or the name you chose) is actually there.

Once that file is found, the fanuc_gpio_controller will be able to parse the pins you added to the XACRO, and it should transition to active.

How does it look after the rebuild?

er]: Loaded fanuc_gpio_controller

[ros2_control_node-1] [INFO] [1780074666.232354569] [controller_manager]: Configuring controller 'fanuc_gpio_controller'

[ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster-4] [INFO] [1780074666.381495326] [spawner_joint_state_broadcaster]: waiting for service /controller_manager/list_controllers to become available...

[ros2_control_node-1] [ERROR] [1780074666.491370353] [controller_manager]: Can't activate controller 'fanuc_gpio_controller': State interface with key 'ConnectionStatus/is_connected' does not exist

[ros2_control_node-1] [ERROR] [1780074666.494703609] [controller_manager]: Could not activate controller : 'fanuc_gpio_controller'

[ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-6] [ERROR] [1780074666.502879927] [spawner_fanuc_gpio_controller]: Failed to activate controller : fanuc_gpio_controller

You have successfully cleared the "File Not Found" hurdle! Now, the fanuc_gpio_controller is actually running, but it’s failing at the very last step of activation because it is looking for a status interface that it considers mandatory.

The specific error is:
State interface with key 'ConnectionStatus/is_connected' does not exist

Why this is happening
The Fanuc GPIO controller doesn't just manage I/O pins; it also monitors the connection status of the robot. Even though you are in mock mode, the controller code still expects to find a state interface named is_connected under a GPIO group called ConnectionStatus.

Since you recently cleaned up your m20_35-18d.ros2_control.xacro, you likely didn't include this specific status block.

The Fix
You need to add the ConnectionStatus and Status blocks to your XACRO. These are purely for feedback and don't require command interfaces.

Open src/fanuc_driver/fanuc_hardware_interface/robot/m20_35-18d.ros2_control.xacro and add this block inside the <ros2_control> tag:

XML
      <!-- Connection Status (Required by Fanuc GPIO Controller) -->
      <gpio name="ConnectionStatus">
        <state_interface name="is_connected"/>
      </gpio>

      <!-- General Robot Status -->
      <gpio name="Status">
        <state_interface name="collaborative_speed_scaling"/>
        <state_interface name="contact_stop_mode"/>
        <state_interface name="e_stopped"/>
        <state_interface name="in_error"/>
        <state_interface name="motion_possible"/>
        <state_interface name="tp_enabled"/>
      </gpio>
Why does this fix it?
When the controller_manager tries to activate a controller, it does a "handshake." It asks the controller, "What do you need?" and the controller says, "I need ConnectionStatus/is_connected." If the Resource Manager (which reads your URDF/XACRO) doesn't see that specific string, it kills the activation.

Pro-Tip: Check the Motion Controllers
While the GPIO controller is still being stubborn, check if your robot can move. Usually, the motion controllers (joint_state_broadcaster and joint_trajectory_controller) do not depend on the GPIO status.

In a separate terminal, run:

Bash
ros2 control list_controllers
If those two motion controllers are active, you can actually start planning in MoveIt right now! The GPIO error is annoying, but it shouldn't stop you from moving the arm.

Final Step
Add the ConnectionStatus block to the XACRO.

Build: colcon build --packages-select fanuc_hardware_interface.

Source and Launch.

Once ConnectionStatus/is_connected is present, the GPIO controller should finally transition to active.

Did the motion controllers manage to turn active despite the GPIO error?

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py     robot_model:=m20_35-18d     robot_series:=m20     moveit_config:=fanuc_m20_moveit_config     robot_ip:=192.168.0.20 use_mock:=false

[INFO] [launch]: All log files can be found below /home/bajajauto/.ros/log/2026-05-29-23-18-48-420151-bajajauto-desktop-76029

[INFO] [launch]: Default logging verbosity is set to INFO

[INFO] [ros2_control_node-1]: process started with pid [76031]

[INFO] [robot_state_publisher-2]: process started with pid [76033]

[INFO] [ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster-3]: process started with pid [76035]

[INFO] [ros2 run controller_manager spawner --controller-manager-timeout 180 joint_trajectory_controller-4]: process started with pid [76037]

[INFO] [ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-5]: process started with pid [76040]

[INFO] [move_group-6]: process started with pid [76044]

[INFO] [rviz2-7]: process started with pid [76046]

[ros2_control_node-1] [WARN] [1780076930.065263721] [controller_manager]: [Deprecated] Passing the robot description parameter directly to the control_manager node is deprecated. Use '~/robot_description' topic from 'robot_state_publisher' instead.

[ros2_control_node-1] [INFO] [1780076930.075199569] [resource_manager]: Loading hardware 'FakeSystem' 

[ros2_control_node-1] [INFO] [1780076930.083754699] [resource_manager]: Initialize hardware 'FakeSystem' 

[ros2_control_node-1] [INFO] [1780076930.085790894] [resource_manager]: Successful initialization of hardware 'FakeSystem'

[ros2_control_node-1] [INFO] [1780076930.100574006] [resource_manager]: 'configure' hardware 'FakeSystem' 

[ros2_control_node-1] [INFO] [1780076930.102825185] [resource_manager]: Successful 'configure' of hardware 'FakeSystem'

[ros2_control_node-1] [INFO] [1780076930.109716004] [resource_manager]: 'activate' hardware 'FakeSystem' 

[ros2_control_node-1] [INFO] [1780076930.111198645] [resource_manager]: Successful 'activate' of hardware 'FakeSystem'

[ros2_control_node-1] [INFO] [1780076930.154168544] [controller_manager]: update rate is 500 Hz

[ros2_control_node-1] [INFO] [1780076930.155903353] [controller_manager]: Spawning controller_manager RT thread with scheduler priority: 50

[ros2_control_node-1] [WARN] [1780076930.165358033] [controller_manager]: Could not enable FIFO RT scheduling policy: with error number <1>(Operation not permitted). See [https://control.ros.org/master/doc/ros2_control/controller_manager/doc/userdoc.html] for details on how to enable realtime scheduling.

[robot_state_publisher-2] [INFO] [1780076930.383925409] [robot_state_publisher]: got segment J1_link

[robot_state_publisher-2] [INFO] [1780076930.384263437] [robot_state_publisher]: got segment J2_link

[robot_state_publisher-2] [INFO] [1780076930.384312270] [robot_state_publisher]: got segment J3_link

[robot_state_publisher-2] [INFO] [1780076930.384331407] [robot_state_publisher]: got segment J4_link

[robot_state_publisher-2] [INFO] [1780076930.384345711] [robot_state_publisher]: got segment J5_link

[robot_state_publisher-2] [INFO] [1780076930.384358832] [robot_state_publisher]: got segment J6_link

[robot_state_publisher-2] [INFO] [1780076930.384372368] [robot_state_publisher]: got segment base_link

[robot_state_publisher-2] [INFO] [1780076930.384385169] [robot_state_publisher]: got segment ee_link

[robot_state_publisher-2] [INFO] [1780076930.384398609] [robot_state_publisher]: got segment fanuc_flange

[robot_state_publisher-2] [INFO] [1780076930.384411761] [robot_state_publisher]: got segment flange

[robot_state_publisher-2] [INFO] [1780076930.384425042] [robot_state_publisher]: got segment wbase

[robot_state_publisher-2] [INFO] [1780076930.384437554] [robot_state_publisher]: got segment world

[move_group-6] [INFO] [1780076930.641983657] [moveit_rdf_loader.rdf_loader]: Loaded robot model in 0.246139 seconds

[move_group-6] [INFO] [1780076930.642220881] [moveit_robot_model.robot_model]: Loading robot model 'm20_35-18d'...

[move_group-6] [INFO] [1780076930.642257458] [moveit_robot_model.robot_model]: No root/virtual joint specified in SRDF. Assuming fixed joint

[move_group-6] [INFO] [1780076931.226363657] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Publishing maintained planning scene on 'monitored_planning_scene'

[move_group-6] [INFO] [1780076931.226839256] [moveit.ros_planning_interface.moveit_cpp]: Listening to 'joint_states' for joint states

[move_group-6] [INFO] [1780076931.229493712] [moveit_ros.current_state_monitor]: Listening to joint states on topic 'joint_states'

[move_group-6] [INFO] [1780076931.231846430] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Listening to '/attached_collision_object' for attached collision objects

[move_group-6] [INFO] [1780076931.231914592] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Starting planning scene monitor

[move_group-6] [INFO] [1780076931.233722716] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Listening to '/planning_scene'

[move_group-6] [INFO] [1780076931.233778014] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Starting world geometry update monitor for collision objects, attached objects, octomap updates.

[move_group-6] [INFO] [1780076931.235504663] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Listening to 'collision_object'

[move_group-6] [INFO] [1780076931.237287601] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Listening to 'planning_scene_world' for planning scene world geometry

[move_group-6] [WARN] [1780076931.241151889] [moveit.ros.occupancy_map_monitor.middleware_handle]: Resolution not specified for Octomap. Assuming resolution = 0.1 instead

[move_group-6] [ERROR] [1780076931.241250676] [moveit.ros.occupancy_map_monitor.middleware_handle]: No 3D sensor plugin(s) defined for octomap updates

[move_group-6] [INFO] [1780076931.264361392] [moveit.ros_planning_interface.moveit_cpp]: Loading planning pipeline 'ompl'

[move_group-6] [INFO] [1780076931.339627525] [moveit.ros_planning.planning_pipeline]: Using planning interface 'OMPL'

[move_group-6] [INFO] [1780076931.359459732] [moveit_ros.add_time_optimal_parameterization]: Param 'ompl.path_tolerance' was not set. Using default value: 0.100000

[move_group-6] [INFO] [1780076931.359557943] [moveit_ros.add_time_optimal_parameterization]: Param 'ompl.resample_dt' was not set. Using default value: 0.100000

[move_group-6] [INFO] [1780076931.359575352] [moveit_ros.add_time_optimal_parameterization]: Param 'ompl.min_angle_change' was not set. Using default value: 0.001000

[move_group-6] [INFO] [1780076931.359675835] [moveit_ros.fix_workspace_bounds]: Param 'ompl.default_workspace_bounds' was not set. Using default value: 10.000000

[move_group-6] [INFO] [1780076931.359725213] [moveit_ros.fix_start_state_bounds]: Param 'ompl.start_state_max_bounds_error' was set to 0.100000

[move_group-6] [INFO] [1780076931.359741213] [moveit_ros.fix_start_state_bounds]: Param 'ompl.start_state_max_dt' was not set. Using default value: 0.500000

[move_group-6] [INFO] [1780076931.359772254] [moveit_ros.fix_start_state_collision]: Param 'ompl.start_state_max_dt' was not set. Using default value: 0.500000

[move_group-6] [INFO] [1780076931.359786911] [moveit_ros.fix_start_state_collision]: Param 'ompl.jiggle_fraction' was set to 0.050000

[move_group-6] [INFO] [1780076931.359850945] [moveit_ros.fix_start_state_collision]: Param 'ompl.max_sampling_attempts' was not set. Using default value: 100

[move_group-6] [INFO] [1780076931.359888706] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Add Time Optimal Parameterization'

[move_group-6] [INFO] [1780076931.359905475] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Resolve constraint frames to robot links'

[move_group-6] [INFO] [1780076931.359914019] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Fix Workspace Bounds'

[move_group-6] [INFO] [1780076931.359922403] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Fix Start State Bounds'

[move_group-6] [INFO] [1780076931.359930788] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Fix Start State In Collision'

[move_group-6] [INFO] [1780076931.359939268] [moveit.ros_planning.planning_pipeline]: Using planning request adapter 'Fix Start State Path Constraints'

[ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster-3] [INFO] [1780076931.529585094] [spawner_joint_state_broadcaster]: waiting for service /controller_manager/list_controllers to become available...

[move_group-6] [INFO] [1780076931.585073647] [moveit.plugins.ros_control_interface]: Started moveit_ros_control_interface::Ros2ControlManager for namespace 

[move_group-6] [INFO] [1780076931.588744808] [moveit.plugins.ros_control_interface]: Using service call timeout 3 seconds

[ros2_control_node-1] [INFO] [1780076931.674952263] [controller_manager]: Loading controller 'joint_trajectory_controller'

[ros2 run controller_manager spawner --controller-manager-timeout 180 joint_trajectory_controller-4] [INFO] [1780076931.856194344] [spawner_joint_trajectory_controller]: Loaded joint_trajectory_controller

[ros2_control_node-1] [INFO] [1780076931.864973514] [controller_manager]: Configuring controller 'joint_trajectory_controller'

[ros2_control_node-1] [INFO] [1780076931.865608031] [joint_trajectory_controller]: No specific joint names are used for command interfaces. Using 'joints' parameter.

[ros2_control_node-1] [INFO] [1780076931.865715490] [joint_trajectory_controller]: Command interfaces are [position] and state interfaces are [position].

[ros2_control_node-1] [INFO] [1780076931.866188178] [joint_trajectory_controller]: Using 'splines' interpolation method.

[ros2_control_node-1] [INFO] [1780076931.873255099] [joint_trajectory_controller]: Controller state will be published at 100.00 Hz.

[ros2_control_node-1] [INFO] [1780076931.891113033] [joint_trajectory_controller]: Action status changes will be monitored at 20.00 Hz.

[ros2_control_node-1] [INFO] [1780076931.931390971] [joint_trajectory_controller]: Time scale subscriber created for topic: speed_scaling_factor

[ros2 run controller_manager spawner --controller-manager-timeout 180 joint_trajectory_controller-4] [INFO] [1780076931.934859150] [spawner_joint_trajectory_controller]: Configured and activated joint_trajectory_controller

[rviz2-7] [INFO] [1780076932.165773176] [rviz2]: Stereo is NOT SUPPORTED

[rviz2-7] [INFO] [1780076932.166246824] [rviz2]: OpenGl version: 4.6 (GLSL 4.6)

[rviz2-7] [INFO] [1780076932.252419366] [rviz2]: Stereo is NOT SUPPORTED

[ros2_control_node-1] [INFO] [1780076932.255673554] [controller_manager]: Loading controller 'fanuc_gpio_controller'

[ros2_control_node-1] [INFO] [1780076932.324231594] [controller_manager]: Loading controller 'joint_state_broadcaster'

[INFO] [ros2 run controller_manager spawner --controller-manager-timeout 180 joint_trajectory_controller-4]: process has finished cleanly [pid 76037]

[ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster-3] [INFO] [1780076932.410618384] [spawner_joint_state_broadcaster]: Loaded joint_state_broadcaster

[ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-5] [INFO] [1780076932.412786967] [spawner_fanuc_gpio_controller]: Loaded fanuc_gpio_controller

[ros2_control_node-1] [INFO] [1780076932.419403154] [controller_manager]: Configuring controller 'fanuc_gpio_controller'

[ros2_control_node-1] [INFO] [1780076932.540258250] [controller_manager]: Configuring controller 'joint_state_broadcaster'

[ros2_control_node-1] [INFO] [1780076932.540470929] [joint_state_broadcaster]: 'joints' or 'interfaces' parameter is empty. All available state interfaces will be published

[ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-5] [INFO] [1780076932.559242301] [spawner_fanuc_gpio_controller]: Configured and activated fanuc_gpio_controller

[ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster-3] [INFO] [1780076932.564710066] [spawner_joint_state_broadcaster]: Configured and activated joint_state_broadcaster

[rviz2-7] Warning: class_loader.impl: SEVERE WARNING!!! A namespace collision has occurred with plugin factory for class rviz_default_plugins::displays::InteractiveMarkerDisplay. New factory will OVERWRITE existing one. This situation occurs when libraries containing plugins are directly linked against an executable (the one running right now generating this message). Please separate plugins out into their own library or just don't link against the library and use either class_loader::ClassLoader/MultiLibraryClassLoader to open.

[rviz2-7]          at line 253 in /opt/ros/humble/include/class_loader/class_loader/class_loader_core.hpp

[INFO] [ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-5]: process has finished cleanly [pid 76040]

[INFO] [ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster-3]: process has finished cleanly [pid 76035]

[move_group-6] [WARN] [1780076934.599241189] [moveit.plugins.ros_control_interface]: Failed to read controllers from /controller_manager/list_controllers within 3 seconds

[move_group-6] [INFO] [1780076934.626080380] [moveit_ros.trajectory_execution_manager]: Trajectory execution is managing controllers

[move_group-6] [INFO] [1780076934.626171231] [move_group.move_group]: MoveGroup debug mode is ON

[move_group-6] [INFO] [1780076934.681342750] [move_group.move_group]: 

[move_group-6] 

[move_group-6] ********************************************************

[move_group-6] * MoveGroup using: 

[move_group-6] *     - ApplyPlanningSceneService

[move_group-6] *     - ClearOctomapService

[move_group-6] *     - CartesianPathService

[move_group-6] *     - ExecuteTrajectoryAction

[move_group-6] *     - GetPlanningSceneService

[move_group-6] *     - KinematicsService

[move_group-6] *     - MoveAction

[move_group-6] *     - MotionPlanService

[move_group-6] *     - QueryPlannersService

[move_group-6] *     - StateValidationService

[move_group-6] ********************************************************

[move_group-6] 

[move_group-6] [INFO] [1780076934.681485187] [moveit_move_group_capabilities_base.move_group_context]: MoveGroup context using planning plugin ompl_interface/OMPLPlanner

[move_group-6] [INFO] [1780076934.681514243] [moveit_move_group_capabilities_base.move_group_context]: MoveGroup context initialization complete

[rviz2-7] [ERROR] [1780076935.803218965] [moveit_ros_visualization.motion_planning_frame]: Action server: /recognize_objects not available

[rviz2-7] [INFO] [1780076935.849460942] [moveit_ros_visualization.motion_planning_frame]: MoveGroup namespace changed: / -> . Reloading params.

[rviz2-7] [INFO] [1780076936.036035205] [moveit_rdf_loader.rdf_loader]: Loaded robot model in 0.100969 seconds

[rviz2-7] [INFO] [1780076936.036218059] [moveit_robot_model.robot_model]: Loading robot model 'm20_35-18d'...

[rviz2-7] [INFO] [1780076936.036266893] [moveit_robot_model.robot_model]: No root/virtual joint specified in SRDF. Assuming fixed joint

[rviz2-7] [INFO] [1780076936.254666305] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Starting planning scene monitor

[rviz2-7] [INFO] [1780076936.259134997] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Listening to '/monitored_planning_scene'

[rviz2-7] [INFO] [1780076936.957330400] [interactive_marker_display_187650680204048]: Connected on namespace: /rviz_moveit_motion_planning_display/robot_interaction_interactive_marker_topic

[rviz2-7] [INFO] [1780076936.981428029] [moveit_ros_visualization.motion_planning_frame]: group group 1

[rviz2-7] [INFO] [1780076936.981514464] [moveit_ros_visualization.motion_planning_frame]: Constructing new MoveGroup connection for group 'group 1' in namespace ''

[rviz2-7] [INFO] [1780076937.026303785] [move_group_interface]: Ready to take commands for planning group group 1.

[rviz2-7] [INFO] [1780076937.029892864] [moveit_ros_visualization.motion_planning_frame]: group group 1

[rviz2-7] [INFO] [1780076937.030452338] [moveit_ros_visualization.motion_planning_frame]: group group 1

[rviz2-7] [INFO] [1780076937.034813218] [interactive_marker_display_187650680204048]: Sending request for interactive markers

[rviz2-7] [INFO] [1780076937.061467092] [interactive_marker_display_187650680204048]: Service response received for initialization



analyze the log for communication

Your communication analysis is in, and it's mostly great news with one minor "handshake" lag to keep an eye on.

1. The Successes
Hardware Initialization: The FakeSystem (Mock Hardware) initialized, configured, and activated perfectly.

GPIO Victory:

[spawner_fanuc_gpio_controller]: Configured and activated fanuc_gpio_controller
The GPIO controller is now Active. This means your XACRO changes (the loops and the ConnectionStatus block) successfully satisfied the controller's requirements.

Trajectory Execution: joint_trajectory_controller is loaded and active, meaning MoveIt can now send joint commands to the hardware interface.

RViz & MoveGroup: MoveGroup is ready, and RViz has successfully connected to the interactive markers. You should see the robot and the "shmball" (interactive marker) in your RViz window.

2. The One Warning: The "3-Second Timeout"
You have this warning in your log:

[move_group-6] [WARN] [moveit.plugins.ros_control_interface]: Failed to read controllers from /controller_manager/list_controllers within 3 seconds

What this means:
MoveIt started up and asked the controller_manager, "Hey, what controllers are available for me to use?" Because your computer was busy spawning three different controllers and starting RViz at the same moment, the controller_manager took longer than 3 seconds to respond.

Is it fatal?
No. Immediately after the warning, you see:
[moveit.plugins.ros_control_interface]: Started moveit_ros_control_interface::Ros2ControlManager
MoveIt eventually got the list and linked up. However, if you find that you cannot execute a motion in RViz (e.g., the "Execute" button is greyed out or fails), this timeout is the reason.

The Fix:
If execution fails, you can increase this timeout in your moveit_controllers.yaml or simply wait a few extra seconds before trying to move the robot in RViz to ensure the background handshake finishes.

3. Real Hardware Check
I noticed you ran the launch with:
robot_ip:=192.168.0.20 use_mock:=false

Crucial Note: Even though you set use_mock:=false, your log shows:
[resource_manager]: Loading hardware 'FakeSystem'

This is because your m20_35-18d.ros2_control.xacro still has the hardcoded plugin:

XML
<hardware>
  <plugin>mock_components/GenericSystem</plugin>
</hardware>
If you intend to talk to the actual Fanuc controller at 192.168.0.20, you must update that XACRO to use the fanuc_hardware_interface/FanucHardwareInterface plugin and pass the robot_ip parameter into it.

Summary of Status
ROS 2 Control: Everything (Joints + GPIO) is Green/Active.

MoveIt: Ready.

Communication: Healthy, though the system is a bit slow on startup (the 3s timeout).

Can you currently move the robot model in RViz using the "Plan and Execute" button?

how to know my rpi port from the tp

To find the port number on a Fanuc Teach Pendant (TP), you aren't looking for a "Raspberry Pi" port, but rather the TCP Port that the KAREL or User Socket Messaging driver is listening on.

For the ROS 2 Fanuc driver, the default port is almost always 11000 (or sometimes 11001 for state). Here is how you verify it on the actual robot controller:

1. Check the HTTP/Port Settings
On the Teach Pendant, press the [ MENU ] key.

Select [ 6 ] SETUP.

Press [ F1 ] [ TYPE ] and select Host Comm.

You will see a list of protocols (TCP/IP, HTTP, etc.).

Highlight HTTP and press [ F3 ] DETAIL.

Look for any entries related to "KAREL" or the "ROS" driver. Often, the port is defined here if the robot is acting as a server.

2. Check the KAREL Variables (Most Reliable)
The ROS driver runs a KAREL program (usually ros_state or ros_relay). These programs store their port numbers in variables.

Press [ MENU ].

Select [ 0 ] NEXT, then [ 6 ] SYSTEM.

Press [ F1 ] [ TYPE ] and select Variables.

Scroll down to find your specific driver variables (e.g., look for ROS_STATE or ROS_RELAY).

Check the PORT or TCP_PORT entry inside those structures.

3. Verify the "User Socket" (Tag) Settings
If your driver uses "Tags" (common in Fanuc Socket Messaging):

Go back to MENU > SETUP > Host Comm.

Highlight TCP/IP and press DETAIL.

Look for S1, S2, S3... (these are the Socket Tags).

If one is named "ROS" or similar, look at the Port column associated with it.

Critical Check for Your MoveIt Setup
In your previous command, you used robot_ip:=192.168.0.20.

Ping Test: From your Ubuntu terminal, run ping 192.168.0.20. If you don't get a response, the port doesn't matter yet; the hardware connection isn't alive.

Port Scan: If the robot is reachable, you can verify which port is open from your PC using:

nmap -p 11000-11005 192.168.0.20

    (You may need to install nmap: `sudo apt install nmap`).

### A Note on Hardware:
Since your logs showed you are still using the `mock_components/GenericSystem` plugin, **ROS 2 is not actually trying to connect to that IP yet.** It's just a string being passed around. 

To bridge to the real M20, you will eventually need to change the `<plugin>` in your `m20_35-18d.ros2_control.xacro` to:
`fanuc_hardware_interface/FanucHardwareInterface` 

Did you find a specific port number (like 11000) listed under the Host Comm settings on your TP?
I got this error ros2 launch fanuc_m20_moveit_config fanuc_moveit_template.launch.py     robot_model:=m20_35-18d     robot_series:=m20     moveit_config:=fanuc_m20_moveit_config     robot_ip:=192.168.0.20 use_mock:=false

[INFO] [launch]: All log files can be found below /home/bajajauto/.ros/log/2026-05-29-23-46-23-625931-bajajauto-desktop-77802

[INFO] [launch]: Default logging verbosity is set to INFO

[INFO] [ros2_control_node-1]: process started with pid [77804]

[INFO] [robot_state_publisher-2]: process started with pid [77806]

[INFO] [ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster-3]: process started with pid [77808]

[INFO] [ros2 run controller_manager spawner --controller-manager-timeout 180 joint_trajectory_controller-4]: process started with pid [77811]

[INFO] [ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-5]: process started with pid [77814]

[INFO] [move_group-6]: process started with pid [77818]

[INFO] [rviz2-7]: process started with pid [77828]

[ros2_control_node-1] [WARN] [1780078585.353909235] [controller_manager]: [Deprecated] Passing the robot description parameter directly to the control_manager node is deprecated. Use '~/robot_description' topic from 'robot_state_publisher' instead.

[ros2_control_node-1] [INFO] [1780078585.355013676] [resource_manager]: Loading hardware 'm20_35-18d' 

[ros2_control_node-1] [INFO] [1780078585.374134945] [resource_manager]: Initialize hardware 'm20_35-18d' 

[ros2_control_node-1] [INFO] [1780078585.375081279] [FR_HW_Interface]: Loading GPIO configuration file: /home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/config/example_gpio_config.yaml

[ros2_control_node-1] [INFO] [1780078585.435103583] [resource_manager]: Successful initialization of hardware 'm20_35-18d'

[ros2_control_node-1] [INFO] [1780078585.450424252] [resource_manager]: 'configure' hardware 'm20_35-18d' 

[ros2_control_node-1] [INFO] [1780078585.452171454] [FR_HW_Interface]: FANUC ROS2 HW interface v3

[ros2_control_node-1] [INFO] [1780078585.453404946] [FR_HW_Interface]: payload_schedule: 1

[ros2_control_node-1] [INFO] [1780078585.454409806] [FR_HW_Interface]: Starting RMI with: 192.168.0.20

[ros2_control_node-1] [INFO] [1780078585.455369675] [FR_HW_Interface]: Connecting to the robot: attempt: 0

[robot_state_publisher-2] Error:   link 'world' is not unique.

[robot_state_publisher-2]          at line 178 in ./urdf_parser/src/model.cpp

[robot_state_publisher-2] Failed to parse robot description using: urdf_xml_parser/URDFXMLParser

[robot_state_publisher-2] terminate called after throwing an instance of 'std::runtime_error'

[robot_state_publisher-2]   what():  Unable to initialize urdf::model from robot description

[ros2_control_node-1] Created UDP socket at: 192.168.0.100:41071

[ros2_control_node-1] Need to reset and abort

[move_group-6] Error:   link 'world' is not unique.

[move_group-6]          at line 178 in ./urdf_parser/src/model.cpp

[move_group-6] Failed to parse robot description using: urdf_xml_parser/URDFXMLParser

[move_group-6] [INFO] [1780078586.090624723] [moveit_rdf_loader.rdf_loader]: Unable to parse URDF

[move_group-6] [ERROR] [1780078586.165804382] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Robot model not loaded

[move_group-6] [ERROR] [1780078586.194591677] [moveit.ros_planning_interface.moveit_cpp]: Planning scene not configured

[move_group-6] [FATAL] [1780078586.196387517] [moveit.ros_planning_interface.moveit_cpp]: Unable to configure planning scene monitor

[move_group-6] terminate called after throwing an instance of 'std::runtime_error'

[move_group-6]   what():  Unable to configure planning scene monitor

[move_group-6] Stack trace (most recent call last):

[move_group-6] #12   Object "/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1", at 0xffffffffffffffff, in 

[move_group-6] #11   Object "/home/bajajauto/ws_moveit/install/moveit_ros_move_group/lib/moveit_ros_move_group/move_group", at 0xaaaabb004a6f, in _start

[move_group-6] #10   Source "../csu/libc-start.c", line 392, in __libc_start_main_impl [0xffffb86374d7]

[move_group-6] #9    Source "../sysdeps/nptl/libc_start_call_main.h", line 58, in __aarch64_ldadd4_acq [0xffffb86373ff]

[move_group-6] #8    Object "/home/bajajauto/ws_moveit/install/moveit_ros_move_group/lib/moveit_ros_move_group/move_group", at 0xaaaabb003cff, in main

[move_group-6] #7    Object "/home/bajajauto/ws_moveit/install/moveit_ros_planning/lib/libmoveit_cpp.so.2.5.9", at 0xffffb909550b, in moveit_cpp::MoveItCpp::MoveItCpp(std::shared_ptr<rclcpp::Node> const&, moveit_cpp::MoveItCpp::Options const&)

[move_group-6] #6    Object "/usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.30", at 0xffffb8892e93, in __cxa_throw

[move_group-6] #5    Object "/usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.30", at 0xffffb8892baf, in std::terminate()

[move_group-6] #4    Object "/usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.30", at 0xffffb8892b4b, in 

[move_group-6] #3    Object "/usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.30", at 0xffffb88953cf, in __gnu_cxx::__verbose_terminate_handler()

[move_group-6] #2    Source "./stdlib/abort.c", line 79, in abort [0xffffb8637133]

[move_group-6] #1    Source "../sysdeps/posix/raise.c", line 26, in raise [0xffffb864a83b]

[move_group-6] #0    Source "./nptl/pthread_kill.c", line 44, in __pthread_kill_implementation [0xffffb8692008]

[move_group-6] Aborted (Signal sent by tkill() 77818 1000)

[ros2_control_node-1] [WARN] [1780078586.853567860] [FR_HW_Interface]: Failed to abort. Timeout waiting for response. 

[ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-5] [INFO] [1780078586.992460226] [spawner_fanuc_gpio_controller]: waiting for service /controller_manager/list_controllers to become available...

[ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster-3] [INFO] [1780078587.361689134] [spawner_joint_state_broadcaster]: waiting for service /controller_manager/list_controllers to become available...

[ros2 run controller_manager spawner --controller-manager-timeout 180 joint_trajectory_controller-4] 2026-05-29 23:46:27.392 [RTPS_TRANSPORT_SHM Error] Failed init_port fastrtps_port7411: open_and_lock_file failed -> Function open_port_internal

[ros2 run controller_manager spawner --controller-manager-timeout 180 joint_trajectory_controller-4] [INFO] [1780078587.573309142] [spawner_joint_trajectory_controller]: waiting for service /controller_manager/list_controllers to become available...

[rviz2-7] [INFO] [1780078587.892615023] [rviz2]: Stereo is NOT SUPPORTED

[rviz2-7] [INFO] [1780078587.893123837] [rviz2]: OpenGl version: 4.6 (GLSL 4.6)

[rviz2-7] [INFO] [1780078587.971546557] [rviz2]: Stereo is NOT SUPPORTED

[rviz2-7] Warning: class_loader.impl: SEVERE WARNING!!! A namespace collision has occurred with plugin factory for class rviz_default_plugins::displays::InteractiveMarkerDisplay. New factory will OVERWRITE existing one. This situation occurs when libraries containing plugins are directly linked against an executable (the one running right now generating this message). Please separate plugins out into their own library or just don't link against the library and use either class_loader::ClassLoader/MultiLibraryClassLoader to open.

[rviz2-7]          at line 253 in /opt/ros/humble/include/class_loader/class_loader/class_loader_core.hpp

[ERROR] [robot_state_publisher-2]: process has died [pid 77806, exit code -6, cmd '/opt/ros/humble/lib/robot_state_publisher/robot_state_publisher --ros-args --params-file /tmp/launch_params_tlep5r8n'].

[ERROR] [move_group-6]: process has died [pid 77818, exit code -6, cmd '/home/bajajauto/ws_moveit/install/moveit_ros_move_group/lib/moveit_ros_move_group/move_group --ros-args --params-file /tmp/launch_params_7wn_73eq'].

[ros2_control_node-1] [INFO] [1780078589.853926848] [FR_HW_Interface]: Connecting to the robot: attempt: 1

[ros2_control_node-1] Created UDP socket at: 192.168.0.100:39551

[ros2_control_node-1] Need to reset and abort

[ros2_control_node-1] [WARN] [1780078589.940182365] [FR_HW_Interface]: Failed to abort. Error: Wait for Command Done.

[rviz2-7] [ERROR] [1780078591.432309831] [moveit_ros_visualization.motion_planning_frame]: Action server: /recognize_objects not available

[rviz2-7] [INFO] [1780078591.502975289] [moveit_ros_visualization.motion_planning_frame]: MoveGroup namespace changed: / -> . Reloading params.

[rviz2-7] Error:   link 'world' is not unique.

[rviz2-7]          at line 178 in ./urdf_parser/src/model.cpp

[rviz2-7] Failed to parse robot description using: urdf_xml_parser/URDFXMLParser

[rviz2-7] [INFO] [1780078591.699910881] [moveit_rdf_loader.rdf_loader]: Unable to parse URDF

[rviz2-7] [ERROR] [1780078591.770237503] [moveit_ros.planning_scene_monitor.planning_scene_monitor]: Robot model not loaded

[ros2_control_node-1] [INFO] [1780078592.940422177] [FR_HW_Interface]: Connecting to the robot: attempt: 2

[ros2_control_node-1] Created UDP socket at: 192.168.0.100:41950

[ros2_control_node-1] Need to reset and abort

[ros2_control_node-1] [WARN] [1780078593.142372478] [FR_HW_Interface]: Failed to abort. Error: Wait for Command Done.

[ros2_control_node-1] [INFO] [1780078596.142666515] [FR_HW_Interface]: Connecting to the robot: attempt: 3

[ros2_control_node-1] Created UDP socket at: 192.168.0.100:41245

[ros2_control_node-1] Need to reset and abort

[ros2_control_node-1] [WARN] [1780078597.368394835] [FR_HW_Interface]: Failed to abort. Timeout waiting for response. 

[ros2_control_node-1] [INFO] [1780078600.368657280] [FR_HW_Interface]: Connecting to the robot: attempt: 4

[ros2_control_node-1] Created UDP socket at: 192.168.0.100:50488

[ros2_control_node-1] Need to reset and abort

[ros2_control_node-1] [WARN] [1780078600.499431925] [FR_HW_Interface]: Failed to abort. Error: Wait for Command Done.

[ros2_control_node-1] [ERROR] [1780078603.499632881] [FR_HW_Interface]: Failed to connect to the robot.

[ros2_control_node-1] [INFO] [1780078603.499845194] [resource_manager]: Failed to 'configure' hardware 'm20_35-18d'

[ros2_control_node-1] terminate called after throwing an instance of 'std::runtime_error'

[ros2_control_node-1]   what():  Failed to set the initial state of the component : m20_35-18d to active

[ros2_control_node-1] Stack trace (most recent call last):

[ros2_control_node-1] #13   Object "/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1", at 0xffffffffffffffff, in 

[ros2_control_node-1] #12   Object "/opt/ros/humble/lib/controller_manager/ros2_control_node", at 0xaaaad486492f, in 

[ros2_control_node-1] #11   Source "../csu/libc-start.c", line 392, in __libc_start_main_impl [0xffff808e74d7]

[ros2_control_node-1] #10   Source "../sysdeps/nptl/libc_start_call_main.h", line 58, in __aarch64_ldadd4_acq [0xffff808e73ff]

[ros2_control_node-1] #9    Object "/opt/ros/humble/lib/controller_manager/ros2_control_node", at 0xaaaad4863eab, in 

[ros2_control_node-1] #8    Object "/opt/ros/humble/lib/libcontroller_manager.so", at 0xffff80fc1993, in controller_manager::ControllerManager::ControllerManager(std::shared_ptr<rclcpp::Executor>, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&, rclcpp::NodeOptions const&)

[ros2_control_node-1] #7    Object "/opt/ros/humble/lib/libcontroller_manager.so", at 0xffff80fbd67b, in controller_manager::ControllerManager::init_resource_manager(std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const&)

[ros2_control_node-1] #6    Object "/usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.30", at 0xffff80b42e93, in __cxa_throw

[ros2_control_node-1] #5    Object "/usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.30", at 0xffff80b42baf, in std::terminate()

[ros2_control_node-1] #4    Object "/usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.30", at 0xffff80b42b4b, in 

[ros2_control_node-1] #3    Object "/usr/lib/aarch64-linux-gnu/libstdc++.so.6.0.30", at 0xffff80b453cf, in __gnu_cxx::__verbose_terminate_handler()

[ros2_control_node-1] #2    Source "./stdlib/abort.c", line 79, in abort [0xffff808e7133]

[ros2_control_node-1] #1    Source "../sysdeps/posix/raise.c", line 26, in raise [0xffff808fa83b]

[ros2_control_node-1] #0    Source "./nptl/pthread_kill.c", line 44, in __pthread_kill_implementation [0xffff80942008]

[ros2_control_node-1] Aborted (Signal sent by tkill() 77804 1000)

[ERROR] [ros2_control_node-1]: process has died [pid 77804, exit code -6, cmd '/opt/ros/humble/lib/controller_manager/ros2_control_node --ros-args --params-file /tmp/launch_params_08ajfvvu --params-file /home/bajajauto/ws_fanuc_1.0.0/install/fanuc_hardware_interface/share/fanuc_hardware_interface/config/ros2_controllers.yaml'].

[INFO] [rviz2-7]: process has finished cleanly [pid 77828]

^C[WARNING] [launch]: user interrupted with ctrl-c (SIGINT)

[ERROR] [ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller-5]: process has died [pid 77814, exit code -2, cmd 'ros2 run controller_manager spawner --controller-manager-timeout 180 fanuc_gpio_controller'].

[ERROR] [ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster-3]: process has died [pid 77808, exit code -2, cmd 'ros2 run controller_manager spawner --controller-manager-timeout 180 joint_state_broadcaster'].

[ERROR] [ros2 run controller_manager spawner --controller-manager-timeout 180 joint_trajectory_controller-4]: process has died [pid 77811, exit code -2, cmd 'ros2 run controller_manager spawner --controller-manager-timeout 180 joint_trajectory_controller'].

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ ^C

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ 





after making these changes to my ros_control file



cat src/fanuc_driver/fanuc_hardware_interface/config/m20_35-18d_physical.ros2_control.xacro 

<?xml version="1.0"?>

<robot xmlns:xacro="http://www.ros.org/wiki/xacro">

    <xacro:macro name="m20_35-18d_ros2_control" params="name initial_positions_file">

        <xacro:property name="initial_positions" value="${xacro.load_yaml(initial_positions_file)['initial_positions']}"/>



        <ros2_control name="${name}" type="system">

            <hardware>

                <!-- By default, set up controllers for simulation. This won't work on real hardware -->

                <plugin>fanuc_robot_driver/FanucHardwareInterface</plugin>

                <param name="robot_ip">$(arg robot_ip)</param>

                <param name="rmi_port">$(arg rmi_port)</param>

                <param name="stream_motion_port">$(arg stream_motion_port)</param>

                <param name="gpio_configuration">$(arg gpio_configuration)</param>

                <param name="payload_schedule">$(arg payload_schedule)</param>

      

            </hardware>







            <joint name="J1">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J1']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <joint name="J2">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J2']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <joint name="J3">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J3']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <joint name="J4">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J4']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <joint name="J5">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J5']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <joint name="J6">

                <command_interface name="position"/>

                <state_interface name="position">

                  <param name="initial_value">${initial_positions['J6']}</param>

                </state_interface>

                <state_interface name="velocity"/>

            </joint>

            <!-- Digital Inputs -->

            <gpio name="DI">

                <xacro:macro name="gen_di" params="i">

                <state_interface name="${i}"/>

                <xacro:if value="${i &lt; 112}">

                    <xacro:gen_di i="${i+1}"/>

                </xacro:if>

                </xacro:macro>

                <xacro:gen_di i="101"/>

            </gpio>



            <!-- Digital Outputs -->

            <gpio name="DO">

                <xacro:macro name="gen_do" params="i">

                <state_interface name="${i}"/>

                <command_interface name="${i}"/>

                <xacro:if value="${i &lt; 112}">

                    <xacro:gen_do i="${i+1}"/>

                </xacro:if>

                </xacro:macro>

                <xacro:gen_do i="101"/>

            </gpio>



            <!-- Robot I/O -->

            <gpio name="RO">

                <state_interface name="1"/><command_interface name="1"/>

                <state_interface name="2"/><command_interface name="2"/>

            </gpio>

            <gpio name="RI">

                <state_interface name="1"/><state_interface name="2"/>

            </gpio>



            <!-- Flags (1 to 32) -->

            <gpio name="F">

                <xacro:macro name="gen_f" params="i">

                <state_interface name="${i}"/>

                <command_interface name="${i}"/>

                <xacro:if value="${i &lt; 32}">

                    <xacro:gen_f i="${i+1}"/>

                </xacro:if>

                </xacro:macro>

                <xacro:gen_f i="1"/>

            </gpio>



            <!-- Float Registers -->

            <gpio name="FloatReg">

                <state_interface name="1"/><state_interface name="2"/><state_interface name="3"/>

                <command_interface name="3"/><command_interface name="4"/><command_interface name="5"/>

            </gpio>

            

            <gpio name="ConnectionStatus">

                <state_interface name="is_connected"/>

            </gpio>





            <gpio name="Status">

                <state_interface name="collaborative_speed_scaling"/>

                <state_interface name="contact_stop_mode"/>

                <state_interface name="e_stopped"/>

                <state_interface name="in_error"/>

                <state_interface name="motion_possible"/>

                <state_interface name="tp_enabled"/>

            </gpio>

        </ros2_control>

    </xacro:macro>

</robot>





nd my urdf.xacro file

bajajauto@bajajauto-desktop:~/ws_fanuc_1.0.0$ cat src/fanuc_driver/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro 

<?xml version="1.0"?>

<robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="m20_35-18d">

    

    <xacro:arg name="robot_ip" default="$(arg robot_ip)"/>

    <xacro:arg name="rmi_port" default="16001"/>

    <xacro:arg name="stream_motion_port" default="60015"/>

    <xacro:arg name="gpio_configuration" default=""/>

    <xacro:arg name="payload_schedule" default="1"/>

    <xacro:arg name="use_mock" default="false"/>

    

    

    

    

    

    

    <xacro:arg name="initial_positions_file" default="initial_positions.yaml" />



    <!-- Import m20_35-18d urdf file -->

    <xacro:include filename="$(find fanuc_m20_description)/robot/m20_35-18d.urdf.xacro" />



    <!-- Import control files @ Dhruv Chaturvedi--> 



    <xacro:if value="$(arg use_mock)">

        <xacro:include filename="$(find fanuc_hardware_interface)/config/m20_35-18d_mock.ros2_control.xacro"/>

    </xacro:if>

    <xacro:unless value="$(arg use_mock)">

        <xacro:include filename="$(find fanuc_hardware_interface)/config/m20_35-18d_physical.ros2_control.xacro"/>

    </xacro:unless>

    <link name="world"/>

    <link name="end_effector"/>

    <xacro:m20_35-18d parent="world" child="end_effector">

        <origin xyz="0 0 0" rpy="0 0 0"/>

    </xacro:m20_35-18d>









    <xacro:m20_35-18d_ros2_control name="m20_35-18d" initial_positions_file="$(arg initial_positions_file)"/>



</robot>

You’ve hit two distinct walls here: a URDF structure error (software) and a Connection timeout (hardware).

Here is the breakdown of how to fix both:

1. The URDF Error: "Link 'world' is not unique"
Your robot_state_publisher and move_group are crashing because the link name world is defined twice.

The Cause:

In your m20_35-18d.urdf.xacro, you manually added <link name="world"/>.

The file you included, fanuc_m20_description/robot/m20_35-18d.urdf.xacro, likely already defines a world link or a base link that conflicts.

The Fix:
Open src/fanuc_driver/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro and remove the redundant link. Change that section to look like this:

XML
<!-- REMOVE THIS LINE: <link name="world"/> -->

<link name="end_effector"/>

<!-- Check the included file's macro arguments -->
<xacro:m20_35-18d prefix="" /> 

<!-- If you need to attach it to a world link, use a joint, 
     but only if the included macro doesn't do it for you -->
<joint name="virtual_joint" type="fixed">
  <parent link="world"/>
  <child link="base_link"/> <!-- or whatever the Fanuc base link is named -->
  <origin xyz="0 0 0" rpy="0 0 0"/>
</joint>
Note: Most Fanuc URDFs use base_link as the root. If you define world, you must connect world to base_link via a joint.

2. The Hardware Error: "Failed to connect to the robot"
The ros2_control_node is successfully trying to use the real hardware driver now, but it can't "handshake" with the Fanuc controller.

The Evidence:

[FR_HW_Interface]: Starting RMI with: 192.168.0.20
[FR_HW_Interface]: Connecting to the robot: attempt: 0
[FR_HW_Interface]: Failed to abort. Timeout waiting for response.

How to solve the connection:

Check the RMI Port: In your URDF, you set rmi_port to 16001. On the Fanuc Teach Pendant, verify that the RMI (Remote Motion Interface) is actually running and listening on 16001. (Standard Fanuc ports are often 11000-11005; 16001 is specific to certain versions of the driver).

Verify the PC IP: Your log shows the PC is creating a socket at 192.168.0.100.

Is your Ubuntu PC's IP manually set to 192.168.0.100?

Can you ping 192.168.0.20 from your terminal?

Teach Pendant State: Ensure the robot is in Auto mode (or T1 with the deadman pressed) and the KAREL programs for the ROS driver are actually RUNNING. If the KAREL program isn't in a "RUN" state, the port won't open.

3. The XACRO Argument Bug
In your m20_35-18d.urdf.xacro, you have this:
<xacro:arg name="robot_ip" default="$(arg robot_ip)"/>

This is circular logic and can cause the string to break. Instead, define it simply:

XML
<xacro:arg name="robot_ip" default="192.168.0.20"/>
And in your m20_35-18d_physical.ros2_control.xacro, ensure the params are being passed correctly into the hardware block:

XML
<hardware>
  <plugin>fanuc_robot_driver/FanucHardwareInterface</plugin>
  <param name="robot_ip">$(arg robot_ip)</param>
  <!-- ... other params ... -->
</hardware>
Summary of Next Steps:
Fix URDF: Remove the link name="world" in your top-level xacro to stop the crash.

Verify Network: Ping the robot.

Check TP: Ensure the KAREL driver is started on the Fanuc controller and check which port it says it is using.

Quick check: When you ping 192.168.0.20, do you get a response?

Look for S1, S2, S3... (these are the Socket Tags). fir this i do get the name ros but the ports are not number they are like rs232-c p2 port2 p3 jd17 p4 and none

If you see names like RS232-C, P2, P3 (JD17), you are looking at the Physical Port Assignment screen rather than the TCP/IP Protocol screen.

On Fanuc controllers, there is a distinction between the hardware connector (the physical plug) and the logical socket (the port number used by the software).

Here is how to find the actual TCP port number (e.g., 11000) instead of the hardware name:

1. The Correct "Host Comm" Path
Instead of looking at the Tags list directly, follow this exact sequence:

Press [ MENU ].

Select [ 6 ] SETUP.

Press [ F1 ] TYPE and select Host Comm.

Highlight TCP/IP and press [ F3 ] DETAIL.

Stop here: You should see IP Address, Subnet Mask, and Router IP.

Now, look for a button labeled [ F3 ] PORT (it might be under [ F2 ] or [ F3 ] depending on your version). This toggles between Port 1 (JD17/CD38A) and Port 2.

Check which one has your 192.168.0.20 address.

2. Finding the "Server" Port Number
If the ROS driver is running as a Server on the robot:

In the same Host Comm menu, highlight HTTP and press DETAIL.

Look for lines labeled KAREL. Often, there is a port assignment there.

Alternatively, go back to the Host Comm main list, highlight SOCKET (if available) and press DETAIL.

3. The "System Variables" Method (The "No-Fail" Way)
If the UI is confusing, the port number is definitely stored in the system memory.

Press [ MENU ].

Select [ 0 ] NEXT -> [ 6 ] SYSTEM.

Press [ F1 ] TYPE -> Variables.

Find $HOSTCFG. Press Enter.

You will see multiple indices (usually 1 through 8). These correspond to the "Tags" you saw earlier (S1, S2, etc.).

Find the index where the name was "ROS".

Look for $SERVER_PORT. The number listed there (e.g., 11000 or 18789) is the port you must put in your launch command.

Why you saw "RS232-C"
In Fanuc terminology, "Port 2" or "JD17" refers to the physical Ethernet port on the main CPU board. When a Tag (like S1) is assigned to a physical port, it just tells the robot "Send this data out of the Ethernet cable." It doesn't tell you the address or port number.

Next Steps to fix your connection:

Find that $SERVER_PORT value using the Variables method above.

Make sure your RMI Port in the launch command matches it exactly.

Crucial: Ensure the KAREL program (likely named ROS_STATE or ROS_RELAY) is actually Running. If it's just "Loaded," the port won't open. You can check this in [ MENU ] -> [ 0 ] NEXT -> [ 4 ] STATUS -> [ F1 ] TYPE -> [ KAREL ].

What is the value of $HOSTCFG[x].$SERVER_PORT for your ROS tag?

Look for $SERVER_PORT. The number listed there (e.g., 11000 or 18789) is the port you must put in your launch command. for this do i have to type the port its empty, i did not find these prorgram Ensure the KAREL program (likely named ROS_STATE or ROS_RELAY

If $SERVER_PORT is empty (0) and you cannot find programs named ROS_STATE or ROS_RELAY in the Status/KAREL menu, it means the Fanuc Driver (KAREL scripts) has not been installed on the robot controller yet.

The ROS 2 driver on your PC is trying to call a "phone number" (the IP and Port) that hasn't been set up on the robot side.

1. How the Fanuc-ROS Connection Works
For ROS 2 to talk to a Fanuc robot, two things must happen:

PC Side: You run the fanuc_moveit_template.launch.py (This is what you are doing now).

Robot Side: A set of KAREL programs (.pc files) must be running to "listen" for the PC's commands.

If those programs aren't there, the robot is just a standard industrial machine that doesn't know ROS exists.

2. How to check if the driver is installed
To be 100% sure the driver is missing:

Press [ SELECT ] on the Teach Pendant.

Press [ F1 ] TYPE and select KAREL Progs.

Look for any files starting with ROS (e.g., ROS_INTERFACE, ROS_STATE, RMI_...).

If the list is empty or doesn't show ROS files, you need to load them.

3. How to install the Driver (The missing step)
You need to get the KAREL files from the fanuc_driver package on your PC and move them to the robot.

Locate the files: In your workspace, look for a folder usually named karel or robot_interface inside the fanuc_driver source. You are looking for .pc files.

Transfer: Put these files on a USB stick and plug it into the Teach Pendant.

Load:

Go to [ MENU ] -> [ 7 ] FILE.

Find your files on the USB (UT1:).

Highlight the .pc files and press [ F3 ] LOAD.

Set Ports: Once loaded, you go back to the $HOSTCFG variables we discussed. Now that the programs exist, you can type 11000 into the $SERVER_PORT field.

4. Why your Launch Crashed (The "world" link)
Even if the hardware connects, your code will still crash because of the URDF error. Since you are in the terminal, let's fix that now so it's ready when the robot is:

Edit this file: ~/ws_fanuc_1.0.0/src/fanuc_driver/fanuc_hardware_interface/robot/m20_35-18d.urdf.xacro

Change this:

XML
<link name="world"/>
<link name="end_effector"/>
<xacro:m20_35-18d parent="world" child="end_effector">
To this:

XML
<!-- Remove the world link line entirely -->
<link name="end_effector"/>
<xacro:m20_35-18d prefix=""/> 
<!-- The macro inside the included file usually creates its own base_link -->
Summary of the situation
Your PC is trying to talk to a robot that doesn't have the "ROS translation software" installed.

Do you have the .pc (KAREL) or .tp files that came with the Fanuc ROS driver package? They are usually located in the fanuc_driver source folder under a robot or karel directory.


