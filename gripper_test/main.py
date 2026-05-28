#!/usr/bin/env python3
"""
Tesollo DG-3F Gripper — Modbus TCP Communication
Operator Control Mode (gripper acts as Modbus Slave/Server)

Default IP  : 169.254.186.72
Default Port: 502

IMPORTANT: Register addresses marked with [REG: ???] must be verified
against the manual that came on the USB stick with your gripper.
The manual has the full register map in the Modbus section.
"""

from pymodbus.client import ModbusTcpClient
import time

# ─── CONNECTION CONFIG ───────────────────────────────────────────────
GRIPPER_IP   = "169.254.186.72"
GRIPPER_PORT = 502
SLAVE_ID     = 12     # check manual — may be 9 for some firmware versions

# ─── REGISTER MAP (verify all addresses from your manual) ───────────
# Output registers (you WRITE to these to command the gripper)
REG_CONTROL      = 0    # Byte 0: control bits (activate, reset, etc.)
REG_GRIP_MODE    = 1    # Grip mode: 0=basic, 1=pinch, 2=wide, 3=scissor
REG_TARGET_POS   = 2    # Target position: 0=open, 255=closed
REG_TARGET_SPEED = 3    # Speed: 0=min, 255=max
REG_TARGET_FORCE = 4    # Force: 0=min, 255=max

# Input registers (you READ from these for feedback)
REG_STATUS       = 0    # Gripper status bits
REG_FAULT        = 1    # Fault flags
REG_POS_FINGER_A = 2    # Current position finger A
REG_POS_FINGER_B = 3    # Current position finger B
REG_POS_FINGER_C = 4    # Current position finger C
REG_CURRENT_A    = 5    # Motor current finger A
REG_CURRENT_B    = 6    # Motor current finger B
REG_CURRENT_C    = 7    # Motor current finger C


class TesolloGripper:
    def __init__(self, ip=GRIPPER_IP, port=GRIPPER_PORT):
        self.client = ModbusTcpClient(host=ip, port=port)
        self.connected = False

    def connect(self):
        self.connected = self.client.connect()
        if self.connected:
            print(f"[OK] Connected to gripper at {GRIPPER_IP}:{GRIPPER_PORT}")
        else:
            print("[ERROR] Failed to connect. Check IP, cable, and power.")
        return self.connected

    def disconnect(self):
        self.client.close()
        print("[OK] Disconnected")

    # ─── WRITE HELPERS ───────────────────────────────────────────────

    def write_register(self, address, value):
        """Write a single holding register (FC06)."""
        result = self.client.write_register(
            address=address,
            value=value,
            # device_id=SLAVE_ID
        )
        if result.isError():
            print(f"[ERROR] Write failed at register {address}: {result}")
            return False
        return True

    def write_registers(self, address, values):
        """Write multiple holding registers (FC16)."""
        result = self.client.write_registers(
            address=address,
            values=values,
            device_id=SLAVE_ID
        )
        if result.isError():
            print(f"[ERROR] Multi-write failed at register {address}: {result}")
            return False
        return True

    # ─── READ HELPERS ────────────────────────────────────────────────

    def read_input_registers(self, address, count=1):
        """Read input registers (FC04) — feedback data."""
        result = self.client.read_input_registers(
            address=address,
            count=count,
            device_id=SLAVE_ID
        )
        if result.isError():
            print(f"[ERROR] Read failed at register {address}: {result}")
            return None
        return result.registers

    def read_holding_registers(self, address, count=1):
        """Read holding registers (FC03) — last written commands."""
        result = self.client.read_holding_registers(
            address=address,
            count=count,
            device_id=SLAVE_ID
        )
        if result.isError():
            print(f"[ERROR] Read failed at register {address}: {result}")
            return None
        return result.registers

    # ─── GRIPPER ACTIONS ─────────────────────────────────────────────

    def activate(self):
        """
        Activate the gripper. Must be called once after power-on.
        Sets rACT bit in control register.
        Control byte: bit0=rACT, bit2=rGTO, bit4=rATR
        """
        print("[→] Activating gripper...")
        # rACT = 0x01 to activate
        self.write_register(REG_CONTROL, 0x00)  # reset first
        time.sleep(0.5)
        self.write_register(REG_CONTROL, 0x01)  # set rACT
        time.sleep(2.0)  # wait for activation to complete
        print("[OK] Activation command sent")

    def set_mode(self, mode: str):
        """
        Set grip mode.
        mode: 'basic' | 'pinch' | 'wide' | 'scissor'
        """
        modes = {"basic": 0, "pinch": 1, "wide": 2, "scissor": 3}
        if mode not in modes:
            print(f"[ERROR] Unknown mode '{mode}'. Use: {list(modes.keys())}")
            return
        self.write_register(REG_GRIP_MODE, modes[mode])
        print(f"[→] Grip mode set to: {mode}")

    def move(self, position: int, speed: int = 128, force: int = 100):
        """
        Command gripper to a position.
        position: 0 (fully open) to 255 (fully closed)
        speed   : 0 (slow) to 255 (fast)
        force   : 0 (min) to 255 (max)
        """
        position = max(0, min(255, position))
        speed    = max(0, min(255, speed))
        force    = max(0, min(255, force))

        # Write position, speed, force in one multi-register write
        self.write_registers(
            address=REG_TARGET_POS,
            values=[position, speed, force]
        )
        print(f"[→] Move: pos={position}, speed={speed}, force={force}")

    def open(self, speed=150):
        """Fully open the gripper."""
        print("[→] Opening gripper...")
        self.move(position=0, speed=speed, force=50)

    def close(self, speed=150, force=150):
        """Fully close the gripper."""
        print("[→] Closing gripper...")
        self.move(position=255, speed=speed, force=force)

    def stop(self):
        """Stop gripper motion immediately."""
        # Clear rGTO bit to stop
        self.write_register(REG_CONTROL, 0x01)  # rACT set, rGTO clear
        print("[→] Stopped")

    # ─── FEEDBACK ────────────────────────────────────────────────────

    def get_status(self):
        """Read and print full gripper status."""
        regs = self.read_input_registers(REG_STATUS, count=8)
        if regs is None:
            return

        status_byte = regs[0]
        fault_byte  = regs[1]
        pos_a       = regs[2]
        pos_b       = regs[3]
        pos_c       = regs[4]
        cur_a       = regs[5]
        cur_b       = regs[6]
        cur_c       = regs[7]

        # Parse status bits
        activated  = bool(status_byte & 0x01)
        moving     = bool(status_byte & 0x08)
        obj_detect = bool(status_byte & 0x30)  # gOBJ bits

        print(f"\n──── Gripper Status ────")
        print(f"  Activated : {activated}")
        print(f"  Moving    : {moving}")
        print(f"  Obj detect: {obj_detect}")
        print(f"  Fault     : 0x{fault_byte:02X}")
        print(f"  Position  : A={pos_a}  B={pos_b}  C={pos_c}  (0=open, 255=closed)")
        print(f"  Current   : A={cur_a}  B={cur_b}  C={cur_c}")
        print(f"────────────────────────\n")

        return {
            "activated": activated,
            "moving": moving,
            "obj_detected": obj_detect,
            "fault": fault_byte,
            "position": [pos_a, pos_b, pos_c],
            "current": [cur_a, cur_b, cur_c],
        }

    def wait_for_stop(self, timeout=10.0):
        """Block until gripper stops moving or timeout."""
        start = time.time()
        while time.time() - start < timeout:
            regs = self.read_input_registers(REG_STATUS, count=1)
            if regs is not None:
                moving = bool(regs[0] & 0x08)
                if not moving:
                    print("[OK] Gripper stopped")
                    return True
            time.sleep(0.1)
        print("[WARN] Timeout waiting for gripper to stop")
        return False


# ─── SHAPE-SPECIFIC GRASP PRESETS ────────────────────────────────────

def grasp_circle(gripper: TesolloGripper):
    """Circle: power grasp, symmetric, medium force."""
    gripper.set_mode("basic")
    time.sleep(0.2)
    gripper.move(position=180, speed=120, force=130)
    gripper.wait_for_stop()

def grasp_triangle(gripper: TesolloGripper):
    """Triangle: pinch mode, align with flat face."""
    gripper.set_mode("pinch")
    time.sleep(0.2)
    gripper.move(position=200, speed=100, force=120)
    gripper.wait_for_stop()

def grasp_heart(gripper: TesolloGripper):
    """Heart: basic mode, grasp at lobe region, lower force to avoid notch."""
    gripper.set_mode("basic")
    time.sleep(0.2)
    gripper.move(position=170, speed=80, force=110)
    gripper.wait_for_stop()


# ─── MAIN TEST SEQUENCE ──────────────────────────────────────────────

if __name__ == "__main__":
    gripper = TesolloGripper()

    if not gripper.connect():
        exit(1)

    
    gripper.activate()  # initial status check
    exit(1)
    try:
        # 1. Activate
        gripper.activate()
        gripper.get_status()

        # 2. Open fully
        gripper.open()
        gripper.wait_for_stop()
        gripper.get_status()

        # 3. Test circle grasp
        print("\n[TEST] Circle grasp")
        grasp_circle(gripper)
        gripper.get_status()
        time.sleep(1)

        # 4. Open again
        gripper.open()
        gripper.wait_for_stop()

        # 5. Test heart grasp
        print("\n[TEST] Heart grasp")
        grasp_heart(gripper)
        gripper.get_status()
        time.sleep(1)

        # 6. Return to open
        gripper.open()
        gripper.wait_for_stop()

    finally:
        gripper.disconnect()
