# Tesollo DG-3FB Gripper Control — Comparative Analysis Report

**Date:** 2026-07-06  
**Scope:** Static code review of three gripper control approaches in this repository (no hardware access).  
**Hardware:** Tesollo Delto DG-3FB (3-finger, 12-DoF) on Fanuc M-20iD/35 cell  
**Default network:** `169.254.186.72:502`

---

## Executive Summary

The three variants in this repo are **not three implementations of the same protocol**. They target **two fundamentally different gripper control modes** that Tesollo documents as mutually exclusive at the hardware level:

| Mode | Protocol | Typical port | Who implements it in this repo |
|------|----------|--------------|--------------------------------|
| **Operator Mode** | Standard Modbus TCP (FC03/04/06/16, coils) | **502** (firmware ≥ 2.0.0) or **10000** (older) | `external/gripper_test/main.py` |
| **Developer / External Mode** | Proprietary Tesollo binary TCP + CRC-16 | **10000** (official SDK default) | `external/gripper_code.py` |

**Why variant 3 works:** `gripper_test/main.py` speaks **Modbus TCP on port 502**, which matches a gripper configured in **Operator Mode** (built-in controller, register-based commands).

**Why variant 1 fails:** `gripper_code.py` sends **raw developer-protocol frames** (`0x03 0x28` duty, `0x01 0x05 0xEE` read) to **port 502**. On Operator Mode hardware, port 502 expects Modbus ADU framing — raw bytes are ignored or rejected. Even in Developer Mode, the official external driver defaults to **port 10000**, not 502.

**Why variant 2 fails:** `external/gripper_ros_driver/` is **not a working driver** — it is design notes and stubs that plan to wrap `DeltoGripper` from variant 1. The referenced ROS package `tesollo_df3fb_driver` does not exist in this repo. Any attempt to run it would inherit variant 1’s protocol mismatch.

**Recommended path for a custom ROS 2 driver:** Build on **Modbus Operator Mode** (variant 3’s transport), but replace the placeholder register map with the **official Tesollo register definitions** from `delto_3f_enum.py` in [tesollodelto/delto_b_ros2](https://github.com/tesollodelto/delto_b_ros2).

---

## 1. Repository Variants at a Glance

| # | Path | Status | Protocol | Abstraction | Lines of working code |
|---|------|--------|----------|-------------|----------------------|
| 1 | `external/gripper_code.py` | **Does not work** | Tesollo External / Developer binary TCP | 12 joint angles (deg), custom PD loop, duty -1000..1000 | ~457 (complete script) |
| 2 | `external/gripper_ros_driver/` | **Does not work** | Intended: same as #1 via `DeltoGripper` | ROS 2 topics/services/action (design only) | ~50 (notes/stubs only) |
| 3 | `external/gripper_test/main.py` | **Works** | Modbus TCP (Operator Mode) | High-level: open/close/move, position 0–255 per finger group | ~294 (complete script) |

---

## 2. Tesollo Hardware Control Modes (Manufacturer Documentation)

Per [Tesollo FAQ](https://en.tesollo.com/faq/) and DG-3F manuals:

### Operator Mode (switch position ① + Modbus TCP ④)
- Gripper uses **built-in controller** for joint coordination, grasp modes, and safety.
- Host sends **Modbus** read/write to holding registers, input registers, and coils.
- Gripper is Modbus **slave**; default **slave ID = 1**.
- Port **502** for firmware ≥ 2.0.0; port **10000** for older firmware.

### Developer Mode (switch position ② + external program)
- Built-in motion planner is **bypassed**.
- Host sends **proprietary binary packets** over TCP (same CRC-16 as Modbus RTU).
- Direct per-motor **duty cycle** control; host must implement control loop.
- Intended for R&D; no built-in grasp protection.

### Physical DIP switches (bottom of gripper)
From UR/TM manuals — **must match the software protocol**:

```
Left switch:  ① = internal program (Operator)   ② = external program (Developer)
Right switch: ③ = Modbus RTU   ④ = Modbus TCP   ⑤ = I/O
```

If switches are set to **① + ④** (Operator + Modbus TCP), only Modbus on port 502 will work. Developer binary packets will never be processed correctly regardless of code quality.

---

## 3. Variant 1 — `external/gripper_code.py` (DeltoGripper)

### 3.1 Architecture

- Raw `socket.socket(AF_INET, SOCK_STREAM)` — no Modbus library.
- Background **PD control thread** (`start_hold_loop`) targeting 12 joint angles in degrees.
- **Override API** for motors 4, 8, 12 (distal joints per finger) — used for HOLD/RELEASE grasp assist.
- Predefined poses: `HOME`, `BALL`, `BLOCK`, `CLIP`, `VISITING_CARD`.

### 3.2 Wire Protocol

**Set motor duties (12 motors):**
```
[0x03, 0x28] + for motor 1..12: [motor_id: u8] [duty: int16 BE] + [CRC16 LE]
```
- Duty range clamped to ±1000.
- CRC: CRC-16/ARC (polynomial 0xA001) — **matches official Tesollo external driver**.

**Read motor positions:**
```
[0x01, 0x05, 0xEE] + [CRC16 LE]  →  verified CRC = D2 DC (correct)
```
- Response parsed as 12 × 5-byte blocks from index 2; position = `(high<<8|low)`, signed, × 0.1 deg.

### 3.3 Comparison with Official External Driver

Tesollo publishes an equivalent implementation in  
[`delto_external_TCP.py`](https://github.com/tesollodelto/delto_b_ros2/blob/devel/delto_3f_driver/delto_utility/delto_external_TCP.py):

| Aspect | `gripper_code.py` | Official `delto_external_TCP.py` |
|--------|-------------------|----------------------------------|
| Default port | **502** | **10000** |
| Read command | `01 05 EE` + computed CRC | `01 05 EE D2 DC` (identical) |
| Duty command header | `03 28` + dynamic build | `03 28` + fixed template |
| CRC algorithm | Manual CRC-16/ARC | `crcmod` CRC-16 (same result) |
| Position parsing | Uniform stride `base = 2 + i*5` | Fixed byte offsets per finger (msg[3,4], msg[8,9], …) |
| Control loop | Custom P-gain (error × 20) | Reference uses separate PD (not in utility file) |

**Verified:** CRC computation in `gripper_code.py` is **correct** for both read and zero-duty packets (cross-checked against official byte sequences).

### 3.4 Identified Failure Modes (ranked by likelihood)

#### F1 — Control mode / port mismatch (**primary root cause**)
- Sends developer-protocol frames to **port 502**.
- Operator Mode on port 502 expects Modbus ADU: `[Transaction ID][Protocol ID][Length][Unit ID][FC][...]`.
- Raw `03 28 ...` bytes are **not valid Modbus** → no motion, possible silent ignore.
- Official external driver connects on **port 10000**.

#### F2 — Hardware switch not in Developer Mode
- Even with port 10000, Developer protocol requires switch **②** (external program).
- Operator switch **①** routes commands to internal Modbus handler only.

#### F3 — Response parsing may be incorrect
Official driver uses **non-uniform byte offsets** (grouped by finger, 5-byte spacing within groups).  
`gripper_code.py` assumes uniform 5-byte records — may misread positions if Developer Mode were enabled, causing unstable or zero duty output.

#### F4 — No SDK initialization sequence
Official Operator SDK flow (C++ / ROS bridge):
1. `SetGripperSystem` (IP, port, mode, slave ID)
2. `ConnectToGripper`
3. `SetGripperOption` (model, joint count, offsets)
4. `SystemStart` (called twice in official example)

Developer mode may not require all of these, but `gripper_code.py` has **no handshake** — only `socket.connect()`.

#### F5 — Control loop starvation on read failure
If `read_motor_positions()` returns `None`, the loop sleeps 0.1 s and retries indefinitely without logging — appears as “connected but gripper dead”.

### 3.5 What Would Need to Change for Developer Mode

1. Confirm DIP switches: **② + ④** or Developer TCP as per manual.
2. Change default port to **10000** (or read `ETHERNET_PORT` holding register 14 after Modbus connect).
3. Fix position parsing to match official byte layout.
4. Add connection validation (expect ~60+ byte response on position read).

---

## 4. Variant 2 — `external/gripper_ros_driver/` (Planned ROS Driver)

### 4.1 What Exists

This folder contains **design notes only**, not runnable code:

| File | Content |
|------|---------|
| `launch/gripper_hardware.py` | 12-line stub listing `DeltoGripper` method names |
| `launch/gripper_driver.py` | ROS interface spec: `/joint_states`, `/gripper_target`, services, action server |
| `launch/gripper_launch.[y` | Launch snippet referencing non-existent package `tesollo_df3fb_driver` |

### 4.2 Planned ROS Interface (from design notes)

**Publish:**
- `/joint_states` (`sensor_msgs/JointState`) — 12 joints: `finger{1,2,3}_joint{1,2,3,4}`

**Subscribe:**
- `/gripper_target` (`std_msgs/Float64MultiArray`) — 12 target angles → `update_target()`

**Services:** `/open`, `/close`, `/home`, `/hold`, `/release`

**Action:** `control_msgs/GripperCommand` variant with `float64[12]` goal (non-standard extension)

**Hardware layer:** `DeltoGripper` from variant 1 (developer protocol).

### 4.3 Why It Cannot Work Today

1. **No implementation** — no `rclpy` node, no `setup.py`, no `package.xml`.
2. **Wrong protocol foundation** — wraps `DeltoGripper` (developer binary), not Modbus.
3. **Missing package** — launch references `tesollo_df3fb_driver` which is not in the repo.
4. **Filename typo** — `gripper_launch.[y` is not a valid launch file extension.

### 4.4 Relation to Official Tesollo ROS Drivers

If “official driver” refers to downloaded [delto_b_ros2](https://github.com/tesollodelto/delto_b_ros2):

| Issue | Detail |
|-------|--------|
| Firmware ≥ 2.3 on DG-3FB | **Incompatible** with `delto_b_ros2`; must use [DELTO_M_ROS2](https://github.com/tesollodelto/DELTO_M_ROS2) + SDK bridge |
| Default port in launch | Official defaults to **10000**; your gripper uses **502** |
| Default slave ID | Official uses **1**; your `gripper_test` uses **12** for some calls |
| Protocol | Official `delto_3f_driver` uses **Modbus** via `delto_modbus_TCP.py`, not `DeltoGripper` |

Official Modbus driver joint command flow:
```
write_registers(address=72, values=intPosion[12])  # holding regs 72–83
write_coil(address=1, value=True)                    # GRASP coil to execute
read_input_registers(address=2, count=12)            # feedback in degrees × 0.1
```

This is **completely different** from variant 1’s duty-cycle loop.

---

## 5. Variant 3 — `external/gripper_test/main.py` (TesolloGripper)

### 5.1 Architecture

- **pymodbus** `ModbusTcpClient` — standard Modbus TCP.
- High-level API: `activate()`, `set_mode()`, `move()`, `open()`, `close()`, `get_status()`.
- Shape presets: `grasp_circle`, `grasp_triangle`, `grasp_heart`.
- Comments explicitly state: **Operator Control Mode**, verify registers from USB manual.

### 5.2 Connection Parameters

```python
GRIPPER_IP   = "169.254.186.72"
GRIPPER_PORT = 502
SLAVE_ID     = 12   # official default is 1
```

### 5.3 Register Map Used (Placeholder / Robotiq-Inspired)

| Symbol | Address | Intended purpose |
|--------|---------|-------------------|
| `REG_CONTROL` | 0 | rACT / rGTO control bits |
| `REG_GRIP_MODE` | 1 | basic/pinch/wide/scissor |
| `REG_TARGET_POS` | 2 | 0=open, 255=closed |
| `REG_TARGET_SPEED` | 3 | speed |
| `REG_TARGET_FORCE` | 4 | force |
| `REG_STATUS` | 0 (input) | status byte |
| `REG_POS_FINGER_A/B/C` | 2–4 (input) | per-finger position |

**Important:** This map does **not** match the official Tesollo enum (`delto_3f_enum.py`):

| Official holding register | Address | Variant 3 uses address for |
|---------------------------|---------|----------------------------|
| `RS485_BAUDRATE` | 0 | REG_CONTROL ← **wrong** |
| `MOTOR1_TARGET_POSITION` … | **72–83** | not used |
| `GRASP_MODE` | **67** | REG_GRIP_MODE (addr 1) ← **wrong** |
| `START_MOTION` | **63** | not used |

Official feedback:
- Input reg **2–13**: motor positions (0.1° units, signed)
- Input reg **14–25**: motor currents

### 5.4 Inconsistencies Within variant 3

| Issue | Location | Risk |
|-------|----------|------|
| `device_id` omitted on single register write | `write_register()` line 65 | May default to slave 1 — **works if slave ID is 1** |
| `device_id=SLAVE_ID` (12) on multi-write/read | `write_registers`, `read_*` | **Fails if slave ID is not 12** |
| `exit(1)` after `activate()` | `main` line 260–261 | **Blocks full test sequence** in current file |
| `move()` never sets rGTO bit | `move()` | May not trigger motion on some firmware without separate control-byte write |
| Robotiq-style 0–255 position | `move()` | Official uses per-joint degrees × 10 at holding 72–83 |

### 5.5 Why It Still Works (Inference)

Despite register map discrepancies vs official enum, variant 3 succeeds because:

1. **Correct transport:** Modbus TCP on port 502 matches Operator Mode + firmware ≥ 2.0.0.
2. **TCP connect succeeds** — proves network, IP, and port are correct.
3. **User may have verified registers against USB manual** — comments say addresses need manual verification; working values may differ from what's written in code vs what was tested on hardware.
4. **`activate()` path** uses single `write_register` without explicit slave ID — if actual slave ID is **1** (factory default), activation writes succeed.
5. Partial testing: `exit(1)` suggests only **connect + activate** was the last confirmed test — full open/close/grasp may still need validation.

---

## 6. Side-by-Side Protocol Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OPERATOR MODE (Variant 3)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Host (pymodbus)  ──Modbus TCP:502──►  Gripper Modbus Server               │
│                                                                             │
│  FC06: write holding reg 72..83  (12 × target position, 0.1° units)         │
│  FC05: write coil 1             (GRASP = execute motion)                    │
│  FC04: read input reg 2..13     (12 × current position)                     │
│  FC04: read input reg 14..25    (12 × motor current)                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                   DEVELOPER MODE (Variant 1)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Host (raw socket)  ──Binary TCP:10000──►  Gripper External Server          │
│                                                                             │
│  TX: 01 05 EE [CRC]              → read all joint positions                 │
│  TX: 03 28 [id,duty]×12 [CRC]   → set 12 motor duty cycles                 │
│  Host runs PD loop at ~20 Hz                                              │
└─────────────────────────────────────────────────────────────────────────────┘

         ▲                              ▲
         │                              │
   gripper_test/main.py          gripper_code.py
   (WORKS on your hardware)      (FAILS — wrong mode/port)
```

---

## 7. Joint / Motor Indexing Reference

Both variant 1 and the official driver use **12 motors** arranged as 3 fingers × 4 joints:

| Index (0-based) | Motor ID (1-based) | Official name | Role in variant 1 HOLD |
|-----------------|-------------------|---------------|------------------------|
| 0–3 | 1–4 | F1M1–F1M4 | Finger 1 |
| 4–7 | 5–8 | F2M1–F2M4 | Finger 2 |
| 8–11 | 9–12 | F3M1–F3M4 | Finger 3 |
| 3, 7, 11 | 4, 8, 12 | F*M4 (distal) | Override targets for grasp HOLD |

Variant 1 predefined poses (degrees, 12 values):

```python
HOME           = [0.0] * 12
BALL           = [-5, -2.3, 62, 69, -60, -1.6, 57.5, 69.2, 60, -2.3, 54.8, 68.4]
BLOCK          = [5, 0.4, 84, 40.6, -90, 6.5, 75, 49, 90, -8.7, 81.2, 46.3]
CLIP           = [0, 0, 140, 110, -83.5, 8.8, 81, 52, 88.3, -11, 83.5, 47.9]
VISITING_CARD  = [-4.8, 1.2, 103.1, 114.7, -100, 0, 62.2, 55, 82.6, 0.7, 82.1, 45.1]
```

For a ROS driver, these become valuable **named configurations** once joint-level Modbus commanding (regs 72–83) is implemented.

---

## 8. Root Cause Summary

| Failure | Root cause | Evidence |
|---------|------------|----------|
| `gripper_code.py` | Developer binary protocol on Operator Mode port | Port 502 + opcodes `03 28` / `01 05 EE`; official external uses port 10000 |
| `gripper_code.py` | Possible wrong hardware switch | Tesollo docs: Developer requires switch ② |
| `gripper_code.py` | Position parse layout differs from official | Uniform stride vs finger-grouped offsets |
| `gripper_ros_driver` | Not implemented | Only stubs; no ROS node code |
| `gripper_ros_driver` | Built on broken variant 1 | `DeltoGripper` wrapper in design notes |
| Official `delto_b_ros2` (if tried) | Wrong port / firmware branch | Default port 10000; DG-3FB fw ≥ 2.3 needs DELTO_M_ROS2 |
| `gripper_test/main.py` **works** | Correct Modbus TCP on 502 | Matches Operator Mode for fw ≥ 2.0.0 |

---

## 9. Recommendations for Custom ROS 2 Driver

### 9.1 Foundation: Operator Mode Modbus (not Developer protocol)

Align with what works on your hardware:

```python
# Transport (proven)
ModbusTcpClient(host="169.254.186.72", port=502)

# Official register map (from delto_3f_enum.py)
HOLDING_TARGET_JOINTS = 72      # 12 registers, value = angle_deg × 10 (signed int16)
HOLDING_GRASP_MODE    = 67
HOLDING_MOTION_STEP   = 64
COIL_GRASP              = 1     # pulse True to execute motion
INPUT_JOINT_POSITIONS = 2       # 12 registers, feedback deg × 0.1
SLAVE_ID                = 1     # verify on hardware; variant 3 uses 12 inconsistently
```

**Typical move sequence:**
1. Connect Modbus TCP.
2. Write 12 target positions to holding registers 72–83.
3. Optionally set `GRASP_MODE` (67) and `GRASP_TORQUE` (68).
4. Write coil `GRASP` (1) = True.
5. Poll input registers 2–13 until positions stabilize.
6. Publish `sensor_msgs/JointState` (convert degrees → radians).

### 9.2 Suggested ROS 2 Interface

Reuse useful ideas from `gripper_ros_driver` design notes, but implement against Modbus:

| Interface | Type | Maps to |
|-----------|------|---------|
| `/gripper/joint_states` | `JointState` pub | Input regs 2–13 |
| `/gripper/command/joint_targets` | `Float64MultiArray` sub | Holding 72–83 |
| `/gripper/grasp` | `std_srvs/Trigger` or `SetBool` | Coil 1 |
| `/gripper/load_preset` | custom srv | Named pose from variant 1 constants |
| `follow_joint_trajectory` | action | Official driver pattern for MoveIt |

### 9.3 Do Not Mix Protocols

- Never send raw `03 28` bytes on port 502.
- Never use pymodbus on port 10000 unless gripper is confirmed in Operator Mode on that port.
- Pick one mode via DIP switch; document the setting on the robot cell.

### 9.4 Fix variant 3 Before Porting to ROS

1. Remove `exit(1)` at line 260.
2. Unify `device_id` / `slave` to one verified value (likely **1**).
3. Replace placeholder register map with official addresses (§9.1).
4. Add `START_MOTION` or `GRASP` coil after writing targets.
5. Read firmware version from input reg 1 at connect — branch to DELTO_M_ROS2 SDK if ≥ 2.3.

### 9.5 Integration with Fanuc / MoveIt

Vision pipeline docs (`docs/vision_pipline/`) already assume:
- URDF chain: `tool0 → tesollo_palm → tesollo_finger_{1,2,3}_tip`
- 12 joint states in radians
- Named grasp postures per shape (circle, heart, triangle)

The ROS driver should publish radians on `/joint_states` and accept trajectory goals compatible with `control_msgs/FollowJointTrajectory` (as official `delto_3f_driver` does).

---

## 10. On-Hardware Verification Checklist

Run these on the robot cell to confirm this analysis:

### Network & mode
- [ ] `ping 169.254.186.72`
- [ ] Photograph gripper DIP switch positions (left + right)
- [ ] Note firmware version: read Modbus input register 1 after connect

### Modbus (expect success — variant 3 path)
- [ ] `python3 external/gripper_test/main.py` after removing `exit(1)`
- [ ] Try `slave=1` and `slave=12` — record which responds
- [ ] Read input regs 0–25 and compare to official enum layout
- [ ] Write holding 72–83 with small delta from current; pulse coil 1

### Developer protocol (expect failure if Operator Mode)
- [ ] `python3 external/gripper_code.py` — note: connect OK but no motion?
- [ ] Retry with port **10000** in `DeltoGripper.__init__`
- [ ] Only if switch ②: retry developer protocol

### Register map validation
- [ ] Compare working register addresses with USB manual Modbus section
- [ ] Document actual slave ID, port, firmware version in `config/gripper_params.yaml`

---

## 11. File Reference Index

| File | Role |
|------|------|
| `external/gripper_code.py` | Developer-mode PD controller (non-functional on current setup) |
| `external/gripper_test/main.py` | Modbus Operator-mode test (functional) |
| `external/gripper_ros_driver/launch/*` | Unimplemented ROS design notes |
| Official: `delto_modbus_TCP.py` | Reference Modbus implementation |
| Official: `delto_external_TCP.py` | Reference developer protocol (port 10000) |
| Official: `delto_3f_enum.py` | Authoritative register/coil addresses |
| Official: `DELTO_M_ROS2/dg_sdk_ros2_bridge` | Required for DG-3FB firmware ≥ 2.3 |

---

## 12. Conclusion

The gripper control problem in this repository is **not a bug in CRC math or threading** — it is a **protocol and mode mismatch**. The working code (`gripper_test/main.py`) uses **Modbus Operator Mode on TCP port 502**. The non-working code (`gripper_code.py` and planned `gripper_ros_driver`) uses **Developer Mode binary frames** associated with **port 10000** and a different hardware switch setting.

The path to a production ROS 2 driver is:

1. **Keep Modbus TCP / port 502** (proven on your cell).
2. **Adopt official register addresses** from Tesollo’s `delto_3f_enum.py`.
3. **Port variant 1’s named poses** as configuration presets.
4. **Implement the ROS interface** sketched in `gripper_ros_driver` design notes on top of Modbus, not `DeltoGripper`.
5. **Confirm firmware version** — if ≥ 2.3, evaluate `DELTO_M_ROS2` SDK bridge instead of raw pymodbus.

---

*Report generated by static analysis. All hardware-specific conclusions marked as inference should be validated on the Fanuc cell using §10 checklist.*
