import socket
import struct
import time
import threading

class DeltoGripper:
    def __init__(self, ip_address="169.254.186.72", port=502):
        self.ip_address = ip_address
        self.port = port
        self.socket = None

        # Concurrency primitives
        self.current_target = None
        self.target_lock = threading.Lock()
        self.target_updated = threading.Event()
        self.stop_event = threading.Event()
        self.control_thread = None
        self.control_running = False
        self.comm_lock = threading.Lock()

        # Overrides: None => no override, integer => forced duty for that motor
        # Indexing: 0..11 for motors 1..12
        self.overrides = [None] * 12
        self.overrides_lock = threading.Lock()

    def connect(self):
        """Establish connection to the gripper"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.ip_address, self.port))
            print("Connected to gripper successfully")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def calculate_crc16(self, data):
        """Calculate CRC-16/ARC for the data"""
        crc = 0
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def set_motor_duties(self, motor_duties):
        """Set duty cycles for all 12 motors (-1000 to 1000)"""
        if not self.socket:
            print("Not connected to gripper")
            return None
        try:
            # Build command packet (format preserved from your snippet)
            packet = bytes([0x03, 0x28])
            for motor_id, duty in enumerate(motor_duties, 1):
                packet += bytes([motor_id])
                duty = max(-1000, min(1000, duty))
                packet += struct.pack('>h', duty)
            crc = self.calculate_crc16(packet)
            packet += struct.pack('<H', crc)

            # send under comm lock
            with self.comm_lock:
                self.socket.send(packet)
        except Exception as e:
            print(f"Error setting duties: {e}")
            return None

    def read_motor_positions(self):
        """Read current motor positions"""
        if not self.socket:
            return None
        try:
            packet = bytes([0x01, 0x05, 0xEE])
            crc = self.calculate_crc16(packet)
            packet += struct.pack('<H', crc)

            with self.comm_lock:
                self.socket.send(packet)
                response = self.socket.recv(4096)

            if not response or len(response) < 5:
                # invalid response
                return None

            positions = {}
            # Parse each motor (defensive checks)
            for i in range(12):
                base = 2 + i * 5
                if base + 2 >= len(response):
                    break
                motor_id = response[base]
                pos_high = response[base + 1]
                pos_low = response[base + 2]
                position = (pos_high << 8) | pos_low
                if position > 32767:
                    position -= 65536
                positions[motor_id] = position * 0.1  # as you had (degrees)
            return positions
        except Exception as e:
            print(f"Error reading positions: {e}")
            return None

    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
            print("Disconnected from gripper")

    # ---- Overrides API ----
    def set_overrides_for_indices(self, indices, value):
        """Set override value for motors whose indices are provided (indices are 1-based motor numbers)."""
        with self.overrides_lock:
            for idx in indices:
                if 1 <= idx <= 12:
                    self.overrides[idx - 1] = int(value)
        # wake control loop so it applies overrides immediately
        self.target_updated.set()

    def clear_overrides_for_indices(self, indices):
        """Clear overrides (set to None) for the provided 1-based motor indices."""
        with self.overrides_lock:
            for idx in indices:
                if 1 <= idx <= 12:
                    self.overrides[idx - 1] = None
        self.target_updated.set()

    def get_overrides_snapshot(self):
        """Return a copy of current overrides (for control loop use)."""
        with self.overrides_lock:
            return list(self.overrides)

    # ---- Threaded control loop API ----
    def start_hold_loop(self, initial_target, max_duty=600, tolerance=0.5,
                        stable_required=5, cycle_delay=0.05, max_hold_time=None):
        """
        Start background control loop. 
        """
        # validate
        if not isinstance(initial_target, (list, tuple)) or len(initial_target) != 12:
            print("start_hold_loop: initial_target must be list/tuple of 12 elements.")
            return False

        with self.target_lock:
            self.current_target = list(initial_target)
        self.target_updated.set()

        if self.control_running:
            return True  # already running

        self.stop_event.clear()
        self.target_updated.clear()

        def control_loop():
            self.control_running = True
            stable_count = 0
            start_time = time.time()
            current_angle = [0.0] * 12
            error = [0.0] * 12
            duties = [0] * 12

            try:
                while not self.stop_event.is_set():
                    # global timeout
                    if max_hold_time is not None and (time.time() - start_time) > max_hold_time:
                        print("Control loop overall timeout reached.")
                        break

                    # copy target safely
                    with self.target_lock:
                        target = None if self.current_target is None else list(self.current_target)

                    if target is None:
                        # no target - wait for update or stop
                        self.target_updated.wait(timeout=0.1)
                        self.target_updated.clear()
                        continue

                    # read positions
                    positions = self.read_motor_positions()
                    if not positions:
                        # if read failed, retry briefly
                        # keep loop alive so user can re-try or switch
                        # (don't flood prints)
                        time.sleep(0.1)
                        continue

                    # take a snapshot of overrides
                    overrides_snapshot = self.get_overrides_snapshot()

                    all_within = True
                    for i in range(12):
                        motor_index = i + 1
                        current_angle[i] = positions.get(motor_index, current_angle[i])
                        error[i] = target[i] - current_angle[i]

                        if abs(error[i]) <= tolerance:
                            duty = 0
                        else:
                            duty = int(error[i] * 20)
                            duty = max(-max_duty, min(max_duty, duty))

                        # apply override if present (overrides are per motor index 0..11)
                        if overrides_snapshot[i] is not None:
                            duties[i] = int(overrides_snapshot[i])
                        else:
                            duties[i] = duty

                        if overrides_snapshot[i] is None and abs(error[i]) > tolerance:
                            all_within = False
                        elif overrides_snapshot[i] is not None:
                            # if overridden, we still consider "not within" only based on underlying error
                            if abs(error[i]) > tolerance:
                                all_within = False

                    # apply duties
                    self.set_motor_duties(duties)

                    # debug (comment/uncomment)
                    # print("Positions:", [round(current_angle[i], 1) for i in range(12)], "Overrides:", overrides_snapshot)

                    if all_within:
                        stable_count += 1
                    else:
                        stable_count = 0

                    if stable_count >= stable_required:
                        # stabilized: stop actively driving but stay ready for new target
                        self.set_motor_duties([0] * 12)
                        # block for small period waiting for target change or override change
                        self.target_updated.wait(timeout=0.1)
                        self.target_updated.clear()
                        continue

                    time.sleep(cycle_delay)

            except Exception as e:
                print(f"Exception in control loop: {e}")
            finally:
                # ensure motors are stopped on exit
                try:
                    self.set_motor_duties([0] * 12)
                except Exception:
                    pass
                self.control_running = False
                print("Control loop stopped.")

        self.control_thread = threading.Thread(target=control_loop, daemon=True)
        self.control_thread.start()
        return True

##    def update_target(self, new_target):
##        """Updates the target while control loop is running."""
##        if not isinstance(new_target, (list, tuple)) or len(new_target) != 12:
##            print("update_target: target must be list of 12 elements")
##            return False
##        with self.target_lock:
##            self.current_target = list(new_target)
##        # wake control loop immediately
##        self.target_updated.set()
##        return True

    def update_target(self, new_target):
        """Updates the target while control loop is running.
        Clears overrides for motors 4,8,12 so they follow the new target.
        """
        if not isinstance(new_target, (list, tuple)) or len(new_target) != 12:
            print("update_target: target must be list of 12 elements")
            return False
        # set new target
        with self.target_lock:
            self.current_target = list(new_target)

        # Clear overrides for motors 4,8,12 so they follow the new target's values
        # (if you prefer to clear all overrides, call: self.clear_all_overrides())
        self.clear_overrides_for_indices([4, 8, 12])

        # wake control loop immediately
        self.target_updated.set()
        return True


    def stop_hold_loop(self, wait=True, timeout=2.0):
        """Stop the background control loop cleanly."""
        self.stop_event.set()
        self.target_updated.set()
        if wait and self.control_thread is not None:
            self.control_thread.join(timeout=timeout)
        return True

    # (optional) keep original synchronous Holding for compatibility
    def Holding(self, target_angle, max_duty=600):
        """Synchronous version kept for compatibility (not used in threaded mode)."""
        tolerance = 0.5
        stable_required = 5
        stable_count = 0
        cycle_delay = 0.05

        if not isinstance(target_angle, (list, tuple)) or len(target_angle) != 12:
            print("Target angle must be a list/tuple of 12 elements.")
            return False

        current_angle = [0.0]*12
        error = [0.0]*12
        duties = [0]*12

        try:
            while True:
                positions = self.read_motor_positions()
                if not positions:
                    print("Failed to read positions")
                    return False

                all_within = True
                for i in range(12):
                    motor_index = i + 1
                    current_angle[i] = positions.get(motor_index, current_angle[i])
                    error[i] = target_angle[i] - current_angle[i]

                    if abs(error[i]) <= tolerance:
                        duty = 0
                    else:
                        duty = int(error[i] * 20)
                        duty = max(-max_duty, min(max_duty, duty))

                    duties[i] = duty
                    if abs(error[i]) > tolerance:
                        all_within = False

                self.set_motor_duties(duties)
                print("Positions:", [round(current_angle[i], 1) for i in range(12)])

                if all_within:
                    self.set_motor_duties([0]*12)
                    print("Target reached and stabilized (sync Holding).")
                    return True

                time.sleep(cycle_delay)

        except KeyboardInterrupt:
            print("\nStopping all motors due to KeyboardInterrupt")
            self.set_motor_duties([0]*12)
            return True
        except Exception as e:
            print(f"Exception in Holding: {e}")
            self.set_motor_duties([0]*12)
            return False

# ---- Main program ----
if __name__ == "__main__":
    gripper = DeltoGripper()

    if gripper.connect():
        try:
            a = gripper.read_motor_positions()
            print("Initial Positions :")
            if a:
                for key, value in a.items():
                    print(f"Motor {key} : {value:.2f}")
            else:
                print("No initial position data available.")

            # Predefined positions
            HOME = [0.0] * 12
            BALL = [-5,-2.3,62,69,-60,-1.6,57.5,69.2,60,-2.3,54.8,68.4]#[ -7.6, -2.0, 0.0, 95.0, -97.1, 7.7, 76.7, 115.9, 85.3, -2.6, 75.3, 116.5 ]
            BLOCK = [5,.4,84,40.6,-90,6.5,75,49,90,-8.7,81.2,46.3]#[ -10.3,3.5,78.9,113.9,-91.4,-7.9,84.4,44.3,91.4,6.5,68.2,51.5]
            CLIP = [0,0,140,110,-83.5,8.8,81,52,88.3,-11,83.5,47.9]
            VISITING_CARD = [-4.8,1.2,103.1,114.7,-100,0,62.2,55,82.6,.7,82.1,45.1]

            print("Finger is Moving to HOME Position (initial automatic move)")
            # Start control loop in background with HOME as initial setpoint
            gripper.start_hold_loop(HOME)

            # Interactive menu (main thread)
            while True:
                try:
                    choice = int(input("Enter 1=HOME 2=BALL 3=BLOCK 4=CLIP 5=VISITING_CARD 0=EXIT : "))
                except ValueError:
                    print("Please enter an integer (0-5).")
                    continue

                match choice:
                    case 1:
                        print("Switching to HOME...")
                        gripper.update_target(HOME)
                    case 2:
                        print("Switching to BALL...")
                        gripper.update_target(BALL)
                    case 3:
                        print("Switching to BLOCK...")
                        gripper.update_target(BLOCK)
                    case 4:
                        print("Switching to CLIP...")
                        gripper.update_target(CLIP)
                    case 5:
                        print("Switching to VISITING_CARD...")
                        gripper.update_target(VISITING_CARD)                        
                    case 0:
                        print("Stopping program...")
                        break
                    case _:
                        print("Invalid input")
                        continue

                # After choosing target, go to the inner HOLD/RELEASE/EXIT menu
                # This menu should be available for every target (HOME, BALL, BLOCK).
                while True:
                    # show inner menu
                    try:
                        inner = int(input("Enter 1=HOLD 2=RELEASE 3=EXIT : "))
                    except ValueError:
                        print("Please enter an integer (1-3).")
                        continue

                    match inner:
                        case 1:  # HOLD: set motors 4,8,12 duty to 500
                            print("HOLD selected: forcing motors 4,8,12 to duty=500 (others remain controlled).")
                            gripper.set_overrides_for_indices([3,7,11], 500) ##3,7,11,    4,8,12
                            continue

                        case 2:  # RELEASE: clear overrides so motors 4,8,12 follow the current target again
                            print("RELEASE selected: clearing overrides so motors 4,8,12 return to the target position.")
                            gripper.clear_overrides_for_indices([3,7,11])
                            continue

                        case 3:  # exit inner menu -> go back to target selection
                            print("Exiting HOLD/RELEASE menu; returning to target selection.")
                            break

                        case _:
                            print("Invalid input in HOLD/RELEASE menu")
                            continue


                # end of inner menu - loop back to outer menu

            # Final positions print
            final_pos = gripper.read_motor_positions()
            print("Final Positions :")
            if final_pos:
                for key, value in final_pos.items():
                    print(f"Motor {key} : {value:.2f}")
            else:
                print("No final position data available.")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            # Stop background loop and disconnect
            gripper.stop_hold_loop()
            gripper.disconnect()  
