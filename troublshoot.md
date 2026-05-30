You got it. Let’s bypass the high-level summary and build a comprehensive, production-grade troubleshooting document.

Based on the complete log of your session, porting a Fanuc CRX ROS 2 template to an M20 industrial arm triggers a very specific chain reaction of errors—from build system caching to Xacro parsing, ROS 2 Control hardware handshakes, and finally physical controller networking.

Here is the exhaustive troubleshooting guide you can use as your `troubleshoot.md` file.

---

# Fanuc M20 ROS 2 Integration: Comprehensive Troubleshooting Guide

This guide documents a complete debugging sequence for configuring a Fanuc M20 industrial robot (specifically the `m20_35-18d`) in ROS 2 Humble using MoveIt and `ros2_control`, particularly when adapting templates originally designed for CRX collaborative robots.

---

## Phase 1: Launch System & Build Artifacts

### Error: Invalid Robot Model Argument

```text
[ERROR] [launch.actions.declare_launch_argument]: Argument "robot_model" provided value "m20_35-18d" is not valid. Valid options are: ['crx5ia', 'crx10ia', 'crx10ia_l', 'crx20ia_l', 'crx30ia']

```

**The Cause:**
ROS 2 launch files are cached in the `install/` directory. Even if you update the Python code in your `src/` folder to remove the `choices=[...]` restriction, the system will execute the outdated installed file. Alternatively, validation logic is hardcoded inside the `launch_setup` opaque function.

**The Fix:**

1. **Purge the shadow environment:** Clear old build artifacts to force the build system to recognize the structural changes.
```bash
cd ~/ws_fanuc_1.0.0
rm -rf build/fanuc_m20_moveit_config/ install/fanuc_m20_moveit_config/

```


2. **Rebuild with Symlinks:** This allows future Python edits to take effect immediately without rebuilding.
```bash
colcon build --packages-select fanuc_m20_moveit_config --symlink-install
source install/setup.bash

```



---

## Phase 2: URDF & Xacro Parsing Failures

### Error 2.1: The Missing Path Slash

```text
FileNotFoundError: [Errno 2] No such file or directory: '.../share/fanuc_hardware_interface/robotm20_35-18d.urdf.xacro'

```

**The Cause:**
When building the `robot_description` parameter using `PathJoinSubstitution`, appending an empty string `""` to cap off a folder path does not automatically insert a trailing slash before raw strings evaluated outside the substitution block.

**The Fix:**
Wrap the dynamic filename inside a `PythonExpression` *within* the `PathJoinSubstitution` block so the ROS launch system handles the OS-level slashes correctly.

```python
robot_description = Command([
    PathJoinSubstitution([FindExecutable(name="xacro")]), " ",
    PathJoinSubstitution([
        FindPackageShare("fanuc_hardware_interface"), 
        "robot", 
        PythonExpression(["'", robot_model, ".urdf.xacro'"]) # Evaluates to 'm20_35-18d.urdf.xacro'
        # or f"{robot_model}.urdf.xacro"
    ]),
    " robot_ip:=1.1.1.1 use_mock:=true "
])

```

### Error 2.2: Missing Configuration Files

```text
[Errno 2] No such file or directory: '.../install/fanuc_hardware_interface/share/fanuc_hardware_interface/robot/initial_positions.yaml'

```

**The Cause:**
The top-level URDF attempts to load default joint states via `<xacro:property name="initial_positions_file" default="initial_positions.yaml"/>`. When creating a new robot package, this file is often overlooked and not copied from the template `src` directory to the target package.

**The Fix:**
Ensure `initial_positions.yaml` exists in `src/fanuc_driver/fanuc_hardware_interface/robot/`, then run `colcon build --packages-select fanuc_hardware_interface`.

### Error 2.3: The Xacro Typo

```text
name 'xarco' is not defined when evaluating expression 'xarco.load_yaml(initial_positions_file)['initial_positions']'

```

**The Cause:**
A syntax error in the Python evaluation block (`${...}`). `xacro` was misspelled as `xarco`, causing a Python `NameError` during URDF compilation.

**The Fix:**
Correct the spelling in `m20_35-18d.ros2_control.xacro`:

```xml
<xacro:property name="initial_positions" value="${xacro.load_yaml(initial_positions_file)['initial_positions']}"/>

```

---

## Phase 3: ROS 2 Control & The Hardware Handshake

### Error 3.1: GPIO Controller Rejection

```text
[ERROR] [controller_manager]: Could not switch controllers since prepare command mode switch was rejected.
[ros2_control_node-1] Not existing: [ DO/101 DO/102 ... RO/1 ... F/1 ... FloatReg/3 ]

```

**The Cause:**
The Fanuc driver uses a "Request vs. Offer" handshake. The controller config (`example_gpio_config.yaml`) requests specific Fanuc I/O pins (e.g., 12 Digital Outputs, 32 Flags). However, the streamlined M20 `ros2_control.xacro` only defined the 6 mechanical joints and did not "offer" the requested GPIO pins, causing the Resource Manager to abort the activation for safety.

**The Fix:**
Populate the `m20_35-18d.ros2_control.xacro` with the exact pins requested by the YAML file. Use Xacro macros to generate them dynamically and prevent manual errors.

*Note: Ensure you use the `&lt;` HTML entity in the `xacro:if` statements; using a raw `<` will cause a `not well-formed (invalid token)` XML crash.*

```xml
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


```

### Error 3.2: Missing Connection Status

```text
[ERROR] [controller_manager]: Can't activate controller 'fanuc_gpio_controller': State interface with key 'ConnectionStatus/is_connected' does not exist

```

**The Cause:**
The Fanuc GPIO controller acts as the safety and state monitor for the driver. It requires specific logical state interfaces to exist in the URDF, even if running in Mock mode.

**The Fix:**
Add the required status blocks to your `ros2_control.xacro`:

```xml
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

```

---

## Phase 4: MoveIt URDF Parsing Collision

### Error: Link 'world' is not unique

```text
[move_group-6] Error: link 'world' is not unique.
[move_group-6] Failed to parse robot description using: urdf_xml_parser/URDFXMLParser

```

**The Cause:**
The top-level `m20_35-18d.urdf.xacro` file manually defined a `<link name="world"/>`. However, the nested Fanuc description macro (`<xacro:include filename=".../m20_35-18d.urdf.xacro" />`) already handled the world generation or explicitly defined a conflicting root link.

**The Fix:**
Remove the redundant manual `world` link definition in the top-level file. Rely on the included macro to build the kinematic chain.

```xml
<link name="end_effector"/>
<xacro:m20_35-18d prefix="" /> 

```

---

## Phase 5: Physical Hardware Networking

### Error: Timeout Waiting for Response

```text
[FR_HW_Interface]: Connecting to the robot: attempt: 0
[FR_HW_Interface]: Failed to abort. Timeout waiting for response.
[FR_HW_Interface]: Failed to connect to the robot.

```

**The Cause (Hardware Disconnect):**
When `use_mock:=false` is set, the `fanuc_hardware_interface` attempts a real UDP/TCP connection to the Fanuc controller. If it times out, one of three things is happening:

1. Network unreachability (IP mismatch).
2. The Fanuc Teach Pendant (TP) is not running the ROS KAREL server programs.
3. The port requested by ROS 2 (`rmi_port:=16001`) does not match the port configured on the Fanuc controller.

**The Fix & Physical Verification Steps:**

1. **Verify the PC IP:** Ensure the Ubuntu PC is physically on the same subnet (e.g., `192.168.0.100`) and can `ping 192.168.0.20`.
2. **Install KAREL Programs:** * Transfer the Fanuc ROS driver `.pc` files from your PC to a USB.
* On the TP, navigate to `[MENU] -> [7] FILE` and `[F3] LOAD` the `.pc` files onto the controller.


3. **Configure the TP Port:**
* Do not look at the physical ports (e.g., "JD17", "Port 2"). You need the Software Socket Port.
* Go to `[MENU] -> [0] NEXT -> [6] SYSTEM -> [F1] TYPE -> Variables`.
* Open `$HOSTCFG`. Find the index assigned to your ROS connection tag.
* Locate the `$SERVER_PORT` variable. Ensure this number (e.g., `11000` or `16001`) exactly matches the `rmi_port` passed in your URDF.


4. **Run the Server:** Ensure the `ROS_STATE` or `ROS_RELAY` program is actively `RUNNING` in the `STATUS -> KAREL` menu.
5. **Fix Circular Arguments:** Ensure your top-level URDF actually passes the IP rather than creating a circular reference.
```xml
<xacro:arg name="robot_ip" default="192.168.0.20"/>

```
