import cmd
from dynamixel_sdk import *

# Control table addresses for AX-12A
ADDR_AX_LED           = 25
ADDR_AX_GOAL_POSITION = 30
ADDR_AX_MOVING_SPEED  = 32
ADDR_AX_PRESENT_POS   = 36
ADDR_AX_PRESENT_LOAD  = 40
ADDR_AX_PRESENT_VOLT  = 42
ADDR_AX_PRESENT_TEMP  = 43

PROTOCOL_VERSION = 1.0
BAUDRATE         = 1000000
DEVICENAME       = '/dev/ttyAMA0'

class DynamixelCLI(cmd.Cmd):
    intro = '\n===================================\n   AX-12A Python Debugger v1.0   \n===================================\nType help or ? to list commands.\n'
    prompt = '> '

    def __init__(self):
        super().__init__()
        self.portHandler = PortHandler(DEVICENAME)
        self.packetHandler = PacketHandler(PROTOCOL_VERSION)

        if self.portHandler.openPort():
            print("Succeeded to open the port")
        else:
            print("Failed to open the port")

        if self.portHandler.setBaudRate(BAUDRATE):
            print("Succeeded to change the baudrate")
        else:
            print("Failed to change the baudrate")

    def print_error_status(self, dxl_comm_result, dxl_error):
        if dxl_comm_result != COMM_SUCCESS:
            print(f"  [COMM ERR]: {self.packetHandler.getTxRxResult(dxl_comm_result)}")
        elif dxl_error != 0:
            print(f"  [ERRORS]: {self.packetHandler.getRxPacketError(dxl_error)}")

    def do_ping(self, arg):
        """ping <id>                  - Ping servo"""
        try:
            dxl_id = int(arg)
            model_num, dxl_comm_result, dxl_error = self.packetHandler.ping(self.portHandler, dxl_id)
            if dxl_comm_result == COMM_SUCCESS:
                print(f"Pong from ID: {dxl_id}")
            self.print_error_status(dxl_comm_result, dxl_error)
        except ValueError:
            print("Invalid arguments. Usage: ping <id>")

    def do_scan(self, arg):
        """scan                       - Scan all IDs 0-253"""
        print("Scanning IDs 0-253...")
        for dxl_id in range(254):
            model_num, dxl_comm_result, dxl_error = self.packetHandler.ping(self.portHandler, dxl_id)
            if dxl_comm_result == COMM_SUCCESS:
                print(f"Found servo at ID: {dxl_id}")
        print("Scan complete.")

    def do_read(self, arg):
        """read <id> <addr> <len>     - Read registers"""
        try:
            args = arg.split()
            dxl_id, addr, length = map(int, args)
            data, dxl_comm_result, dxl_error = self.packetHandler.readTxRx(self.portHandler, dxl_id, addr, length)
            if dxl_comm_result == COMM_SUCCESS:
                print(f"Read {length} bytes from addr {addr}:")
                for i in range(length):
                    print(f"  [{addr + i:02d}] 0x{data[i]:02X} ({data[i]})")
            self.print_error_status(dxl_comm_result, dxl_error)
        except (ValueError, IndexError):
            print("Invalid arguments. Usage: read <id> <addr> <len>")

    def do_write(self, arg):
        """write <id> <addr> <val>    - Write 8-bit register"""
        try:
            args = arg.split()
            dxl_id, addr, val = map(int, args)
            dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler, dxl_id, addr, val)
            if dxl_comm_result == COMM_SUCCESS:
                print("Write successful.")
            self.print_error_status(dxl_comm_result, dxl_error)
        except (ValueError, IndexError):
            print("Invalid arguments. Usage: write <id> <addr> <val>")

    def do_write16(self, arg):
        """write16 <id> <addr> <val>  - Write 16-bit register"""
        try:
            args = arg.split()
            dxl_id, addr, val = map(int, args)
            dxl_comm_result, dxl_error = self.packetHandler.write2ByteTxRx(self.portHandler, dxl_id, addr, val)
            if dxl_comm_result == COMM_SUCCESS:
                print("Write 16-bit successful.")
            self.print_error_status(dxl_comm_result, dxl_error)
        except (ValueError, IndexError):
            print("Invalid arguments. Usage: write16 <id> <addr> <val>")

    def do_move(self, arg):
        """move <id> <pos> <speed>    - Move servo"""
        try:
            args = arg.split()
            dxl_id, pos, speed = map(int, args)
            data = [pos & 0xFF, (pos >> 8) & 0xFF, speed & 0xFF, (speed >> 8) & 0xFF]
            dxl_comm_result, dxl_error = self.packetHandler.writeTxRx(self.portHandler, dxl_id, ADDR_AX_GOAL_POSITION, 4, data)
            if dxl_comm_result == COMM_SUCCESS:
                print("Move command sent.")
            self.print_error_status(dxl_comm_result, dxl_error)
        except (ValueError, IndexError):
            print("Invalid arguments. Usage: move <id> <pos> <speed>")

    def do_led(self, arg):
        """led <id> <1/0>             - Toggle LED"""
        try:
            args = arg.split()
            dxl_id, val = map(int, args)
            val = 1 if val else 0
            dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler, dxl_id, ADDR_AX_LED, val)
            if dxl_comm_result == COMM_SUCCESS:
                print("LED command sent.")
            self.print_error_status(dxl_comm_result, dxl_error)
        except (ValueError, IndexError):
            print("Invalid arguments. Usage: led <id> <1/0>")

    def do_status(self, arg):
        """status <id>                - Read volt, temp, load, pos"""
        try:
            dxl_id = int(arg)
            print(f"--- Status ID {dxl_id} ---")
            
            # Volt
            volt, dxl_comm_result, dxl_error = self.packetHandler.read1ByteTxRx(self.portHandler, dxl_id, ADDR_AX_PRESENT_VOLT)
            if dxl_comm_result == COMM_SUCCESS:
                print(f"Voltage: {volt / 10.0:.1f} V")
            
            # Temp
            temp, dxl_comm_result, dxl_error = self.packetHandler.read1ByteTxRx(self.portHandler, dxl_id, ADDR_AX_PRESENT_TEMP)
            if dxl_comm_result == COMM_SUCCESS:
                print(f"Temperature: {temp} C")
                
            # Load
            load, dxl_comm_result, dxl_error = self.packetHandler.read2ByteTxRx(self.portHandler, dxl_id, ADDR_AX_PRESENT_LOAD)
            if dxl_comm_result == COMM_SUCCESS:
                ccw = (load & 0x400) > 0
                actual_load = load & 0x3FF
                direction = "CCW" if ccw else "CW"
                print(f"Load: {actual_load} ({direction})")
                
            # Pos
            pos, dxl_comm_result, dxl_error = self.packetHandler.read2ByteTxRx(self.portHandler, dxl_id, ADDR_AX_PRESENT_POS)
            if dxl_comm_result == COMM_SUCCESS:
                print(f"Present Position: {pos}")
                
            self.print_error_status(dxl_comm_result, dxl_error)
        except ValueError:
            print("Invalid arguments. Usage: status <id>")

    def do_reset(self, arg):
        """reset <id>                 - Factory reset servo"""
        try:
            dxl_id = int(arg)
            print(f"Factory resetting ID {dxl_id}... (This will reset ID to 1 and baud to 1000000)")
            # 0x00 is Reset All
            dxl_comm_result, dxl_error = self.packetHandler.factoryReset(self.portHandler, dxl_id, 0x00)
            if dxl_comm_result == COMM_SUCCESS:
                print("Reset command sent.")
            self.print_error_status(dxl_comm_result, dxl_error)
        except ValueError:
            print("Invalid arguments. Usage: reset <id>")

    def do_quit(self, arg):
        """quit                       - Exit the debugger"""
        print("Closing port and exiting...")
        self.portHandler.closePort()
        return True

    def do_EOF(self, arg):
        """Exit on Ctrl-D"""
        print()
        return self.do_quit(arg)

if __name__ == '__main__':
    try:
        DynamixelCLI().cmdloop()
    except KeyboardInterrupt:
        print("\nExiting...")
