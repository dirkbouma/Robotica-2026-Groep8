#!/usr/bin/env python3
"""
AX-12A Extended Debugger - Python CLI
Does NOT use the Dynamixel library. Fully manual protocol implementation.
Designed for Raspberry Pi 5 with /dev/ttyAMA0.
"""

import sys
import time
import serial
import cmd

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/ttyAMA0'
BAUDRATE = 1000000

# Set DIR_PIN to the BCM GPIO pin number if you are using a 74LS241 or similar
# half-duplex hardware buffer that requires a direction toggle.
# Set to None if your hardware handles half-duplex automatically (e.g. USB to RS485).
DIR_PIN = None 

# If you need to invert the direction logic (like DIR_TX = HIGH, DIR_RX = LOW)
DIR_TX = True  # True usually means HIGH
DIR_RX = False # False usually means LOW

# Optional GPIO Setup
dir_output = None
if DIR_PIN is not None:
    try:
        from gpiozero import DigitalOutputDevice
        dir_output = DigitalOutputDevice(DIR_PIN)
        dir_output.value = DIR_RX # Start in RX mode
    except ImportError:
        print("Warning: gpiozero not found. Running without DIR_PIN toggling.")
        dir_output = None

# --- AX-12A INSTRUCTIONS ---
INST_PING       = 0x01
INST_READ_DATA  = 0x02
INST_WRITE_DATA = 0x03
INST_REG_WRITE  = 0x04
INST_ACTION     = 0x05
INST_RESET      = 0x06

class AX12A_Debug(cmd.Cmd):
    intro = "\n===================================\n   AX-12A Extended Debugger v1.0   \n===================================\nType 'help' or '?' for a list of commands."
    prompt = "> "

    def __init__(self):
        super().__init__()
        self.debug_mode = False
        self.dir_tx_state = DIR_TX
        self.dir_rx_state = DIR_RX
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0)
            print(f"Opened {SERIAL_PORT} at {BAUDRATE} baud.")
        except serial.SerialException as e:
            print(f"Failed to open serial port {SERIAL_PORT}: {e}")
            print("Running in dummy mode for testing.")
            self.ser = None

    def set_tx_mode(self):
        if dir_output is not None:
            dir_output.value = self.dir_tx_state

    def set_rx_mode(self):
        if self.ser:
            self.ser.flush() # Wait for all bytes to be transmitted
        if dir_output is not None:
            dir_output.value = self.dir_rx_state

    def send_packet(self, dxl_id, instruction, params=None):
        if params is None:
            params = []
        
        length = len(params) + 2
        checksum = dxl_id + length + instruction + sum(params)
        checksum = (~checksum) & 0xFF

        packet = bytearray([0xFF, 0xFF, dxl_id, length, instruction])
        packet.extend(params)
        packet.append(checksum)

        self.set_tx_mode()
        if self.ser:
            self.ser.write(packet)
        self.set_rx_mode()

    def read_packet(self, timeout_ms=100):
        if not self.ser:
            return -1, 0, []

        start = time.time()
        timeout = timeout_ms / 1000.0
        
        state = 0
        dxl_id = 0
        length = 0
        error = 0
        params = []
        calc_checksum = 0

        while (time.time() - start) < timeout:
            if self.ser.in_waiting > 0:
                b = self.ser.read()[0]
                if self.debug_mode:
                    print(f"DEBUG RX: 0x{b:02X}")
                
                if state == 0:
                    if b == 0xFF: state = 1
                elif state == 1:
                    if b == 0xFF: state = 2
                    else: state = 0
                elif state == 2:
                    dxl_id = b
                    calc_checksum += b
                    state = 3
                elif state == 3:
                    length = b
                    calc_checksum += b
                    state = 4
                elif state == 4:
                    error = b
                    calc_checksum += b
                    if length == 2:
                        state = 6 # No params
                    else:
                        state = 5
                elif state == 5:
                    params.append(b)
                    calc_checksum += b
                    if len(params) >= length - 2:
                        state = 6
                elif state == 6:
                    rx_checksum = b
                    calc_checksum = (~calc_checksum) & 0xFF
                    if rx_checksum == calc_checksum:
                        return len(params), error, params
                    else:
                        return -2, error, params
        return -1, 0, []

    def print_error_status(self, error):
        if error == 0:
            return
        err_msg = "  [ERRORS]: "
        if error & 0x01: err_msg += "InputVoltage "
        if error & 0x02: err_msg += "AngleLimit "
        if error & 0x04: err_msg += "Overheating "
        if error & 0x08: err_msg += "Range "
        if error & 0x10: err_msg += "Checksum "
        if error & 0x20: err_msg += "Overload "
        if error & 0x40: err_msg += "Instruction "
        print(err_msg)

    # --- CLI COMMANDS ---

    def do_ping(self, arg):
        """ping <id> : Ping servo"""
        try:
            dxl_id = int(arg)
        except ValueError:
            print("Usage: ping <id>")
            return
            
        self.send_packet(dxl_id, INST_PING)
        res, err, params = self.read_packet()
        if res >= 0:
            print(f"Pong from ID: {dxl_id}")
            self.print_error_status(err)
        elif res == -2:
            print("Checksum Error!")
        else:
            print("Timeout.")

    def do_scan(self, arg):
        """scan : Scan all IDs 0-253"""
        print("Scanning IDs 0-253...")
        found = False
        for dxl_id in range(254):
            self.send_packet(dxl_id, INST_PING)
            res, err, params = self.read_packet(timeout_ms=15)
            if res >= 0:
                print(f"Found servo at ID: {dxl_id}")
                found = True
        if not found:
            print("No servos found.")
        print("Scan complete.")

    def do_read(self, arg):
        """read <id> <addr> <len> : Read registers"""
        args = arg.split()
        if len(args) != 3:
            print("Usage: read <id> <addr> <len>")
            return
        try:
            dxl_id, addr, length = map(int, args)
        except ValueError:
            print("Arguments must be integers.")
            return

        self.send_packet(dxl_id, INST_READ_DATA, [addr, length])
        res, err, params = self.read_packet()
        if res >= 0:
            print(f"Read {res} bytes from addr {addr}:")
            for i, val in enumerate(params):
                print(f"  [{addr + i:02d}] 0x{val:02X} ({val})")
            self.print_error_status(err)
        else:
            print("Failed to read (timeout or err).")

    def do_write(self, arg):
        """write <id> <addr> <val> : Write 8-bit register"""
        args = arg.split()
        if len(args) != 3:
            print("Usage: write <id> <addr> <val>")
            return
        try:
            dxl_id, addr, val = map(int, args)
        except ValueError:
            print("Arguments must be integers.")
            return

        self.send_packet(dxl_id, INST_WRITE_DATA, [addr, val])
        res, err, params = self.read_packet()
        if res >= 0:
            print("Write successful.")
            self.print_error_status(err)
        else:
            print("Write failed (timeout or err).")

    def do_write16(self, arg):
        """write16 <id> <addr> <val> : Write 16-bit register"""
        args = arg.split()
        if len(args) != 3:
            print("Usage: write16 <id> <addr> <val>")
            return
        try:
            dxl_id, addr, val = map(int, args)
        except ValueError:
            print("Arguments must be integers.")
            return

        val_l = val & 0xFF
        val_h = (val >> 8) & 0xFF
        self.send_packet(dxl_id, INST_WRITE_DATA, [addr, val_l, val_h])
        res, err, params = self.read_packet()
        if res >= 0:
            print("Write 16-bit successful.")
            self.print_error_status(err)
        else:
            print("Write failed (timeout or err).")

    def do_move(self, arg):
        """move <id> <pos> <speed> : Move servo"""
        args = arg.split()
        if len(args) != 3:
            print("Usage: move <id> <pos> <speed>")
            return
        try:
            dxl_id, pos, speed = map(int, args)
        except ValueError:
            print("Arguments must be integers.")
            return

        params = [
            30, # Goal position register
            pos & 0xFF,
            (pos >> 8) & 0xFF,
            speed & 0xFF,
            (speed >> 8) & 0xFF
        ]
        self.send_packet(dxl_id, INST_WRITE_DATA, params)
        self.read_packet() # Ignore response to return quickly
        print("Move command sent.")

    def do_led(self, arg):
        """led <id> <1/0> : Toggle LED"""
        args = arg.split()
        if len(args) != 2:
            print("Usage: led <id> <1/0>")
            return
        try:
            dxl_id, state = map(int, args)
        except ValueError:
            print("Arguments must be integers.")
            return
            
        self.do_write(f"{dxl_id} 25 {1 if state else 0}")

    def do_status(self, arg):
        """status <id> : Read volt, temp, load, pos"""
        try:
            dxl_id = int(arg)
        except ValueError:
            print("Usage: status <id>")
            return
            
        print(f"--- Status ID {dxl_id} ---")
        
        # Volt
        self.send_packet(dxl_id, INST_READ_DATA, [42, 1])
        res, err, params = self.read_packet()
        if res == 1:
            print(f"Voltage: {params[0] / 10.0:.1f} V")
            
        # Temp
        self.send_packet(dxl_id, INST_READ_DATA, [43, 1])
        res, err, params = self.read_packet()
        if res == 1:
            print(f"Temperature: {params[0]} C")
            
        # Load
        self.send_packet(dxl_id, INST_READ_DATA, [40, 2])
        res, err, params = self.read_packet()
        if res == 2:
            load = params[0] | (params[1] << 8)
            ccw = (load & 0x400) > 0
            load = load & 0x3FF
            direction = "CCW" if ccw else "CW"
            print(f"Load: {load} ({direction})")
            
        # Pos
        self.send_packet(dxl_id, INST_READ_DATA, [36, 2])
        res, err, params = self.read_packet()
        if res == 2:
            pos = params[0] | (params[1] << 8)
            print(f"Present Position: {pos}")

    def do_reset(self, arg):
        """reset <id> : Factory reset servo"""
        try:
            dxl_id = int(arg)
        except ValueError:
            print("Usage: reset <id>")
            return
            
        print(f"Factory resetting ID {dxl_id}... (This will reset ID to 1 and baud to 1000000)")
        self.send_packet(dxl_id, INST_RESET)
        self.read_packet()
        print("Reset command sent.")

    def do_debug(self, arg):
        """debug : Toggle debug mode to print raw received bytes"""
        self.debug_mode = not self.debug_mode
        print(f"Debug mode is now {'ON' if self.debug_mode else 'OFF'}.")

    def do_flipdir(self, arg):
        """flipdir : Swap the logic for DIR_TX and DIR_RX (High/Low)"""
        self.dir_tx_state = not self.dir_tx_state
        self.dir_rx_state = not self.dir_rx_state
        print(f"Direction logic flipped. TX is now {'HIGH' if self.dir_tx_state else 'LOW'}, RX is {'HIGH' if self.dir_rx_state else 'LOW'}.")
        self.set_rx_mode() # Apply new RX state

    def do_exit(self, arg):
        """exit : Exit the debugger"""
        print("Exiting...")
        return True

    def do_quit(self, arg):
        """quit : Exit the debugger"""
        print("Exiting...")
        return True
        
    def do_EOF(self, arg):
        print()
        return True

if __name__ == '__main__':
    try:
        AX12A_Debug().cmdloop()
    except KeyboardInterrupt:
        print("\nExiting...")
