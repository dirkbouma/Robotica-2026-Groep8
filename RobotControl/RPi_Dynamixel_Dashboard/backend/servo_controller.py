import time
import platform
import logging
import struct
try:
    import fcntl
except ImportError:
    fcntl = None
from .ax12a_registers import CONTROL_TABLE

logger = logging.getLogger(__name__)

# Fallback for Windows/Mac development
IS_LINUX = platform.system() == "Linux"

# Constants for Dynamixel Protocol 1.0 (used by AX-12A)
PROTOCOL_VERSION = 1.0
BAUDRATE = 1000000

# RS485 Constants for Linux ioctl
TIOCSRS485 = 0x542F
SER_RS485_ENABLED = 0x00000001
SER_RS485_RTS_ON_SEND = 0x00000002

if IS_LINUX:
    DEVICENAME = '/dev/ttyAMA0'
else:
    DEVICENAME = 'COM1'

try:
    if IS_LINUX:
        from dynamixel_sdk import PortHandler, PacketHandler
    else:
        raise ImportError("Not on Linux")
except ImportError:
    IS_LINUX = False
    logger.warning("Running in MOCK mode (dynamixel_sdk not found or not on Linux)")

class MockPortHandler:
    def openPort(self): return True
    def setBaudRate(self, baudrate): return True
    def closePort(self): pass

class MockPacketHandler:
    def __init__(self):
        # Mock RAM
        self.mock_memory = {}
        for i in range(1, 4):
            self.mock_memory[i] = {k: 0 for k in CONTROL_TABLE.keys()}
            self.mock_memory[i]["Present Position"] = 512
            self.mock_memory[i]["Present Voltage"] = 120
            self.mock_memory[i]["Present Temperature"] = 35
            self.mock_memory[i]["Present Load"] = 10
            self.mock_memory[i]["Model Number"] = 12
    
    def read1ByteTxRx(self, port, dxl_id, address):
        reg = self._find_reg_by_addr(address)
        if reg and dxl_id in self.mock_memory:
            return self.mock_memory[dxl_id].get(reg, 0), 0, 0
        return 0, 0, 0

    def read2ByteTxRx(self, port, dxl_id, address):
        reg = self._find_reg_by_addr(address)
        if reg and dxl_id in self.mock_memory:
            return self.mock_memory[dxl_id].get(reg, 0), 0, 0
        return 0, 0, 0

    def write1ByteTxRx(self, port, dxl_id, address, data):
        reg = self._find_reg_by_addr(address)
        if reg and dxl_id in self.mock_memory:
            self.mock_memory[dxl_id][reg] = data
        return 0, 0

    def write2ByteTxRx(self, port, dxl_id, address, data):
        reg = self._find_reg_by_addr(address)
        if reg and dxl_id in self.mock_memory:
            self.mock_memory[dxl_id][reg] = data
            if reg == "Goal Position":
                self.mock_memory[dxl_id]["Present Position"] = data
        return 0, 0

    def ping(self, port, dxl_id):
        if dxl_id in [1, 2, 3]: # Mock IDs present
            return 12, 0, 0
        return 0, 0, -1

    def _find_reg_by_addr(self, address):
        for k, v in CONTROL_TABLE.items():
            if v["address"] == address:
                return k
        return None

class ServoController:
    def __init__(self):
        if IS_LINUX:
            self.portHandler = PortHandler(DEVICENAME)
            self.packetHandler = PacketHandler(PROTOCOL_VERSION)
            if self.portHandler.openPort():
                logger.info(f"Succeeded to open the port {DEVICENAME}")
            else:
                logger.error(f"Failed to open the port {DEVICENAME}")
            
            if self.portHandler.setBaudRate(BAUDRATE):
                logger.info("Succeeded to change the baudrate")
            else:
                logger.error("Failed to change the baudrate")

            # ENABLE RS485 hardware toggling via ioctl
            try:
                if fcntl:
                    rs485_flags = (SER_RS485_ENABLED | SER_RS485_RTS_ON_SEND)
                    buf = struct.pack('IIIIIIII', rs485_flags, 0, 0, 0, 0, 0, 0, 0)
                    fcntl.ioctl(self.portHandler.ser.fileno(), TIOCSRS485, buf)
                    logger.info("RS485 enabled successfully via ioctl")
                else:
                    logger.warning("fcntl not available, skipping RS485 setup")
            except Exception as e:
                logger.error(f"RS485 setup failed: {e}")
        else:
            self.portHandler = MockPortHandler()
            self.packetHandler = MockPacketHandler()

    def scan(self):
        found_ids = []
        for i in range(254):
            model_number, dxl_comm_result, dxl_error = self.packetHandler.ping(self.portHandler, i)
            if dxl_comm_result == 0 and dxl_error == 0:
                found_ids.append(i)
        return found_ids

    def read_register(self, dxl_id, reg_name):
        reg = CONTROL_TABLE.get(reg_name)
        if not reg: return None
        
        if reg["size"] == 1:
            data, dxl_comm_result, dxl_error = self.packetHandler.read1ByteTxRx(self.portHandler, dxl_id, reg["address"])
        else:
            data, dxl_comm_result, dxl_error = self.packetHandler.read2ByteTxRx(self.portHandler, dxl_id, reg["address"])
        
        # Only return data if comm success
        if dxl_comm_result == 0 and dxl_error == 0:
            return data
        return None

    def write_register(self, dxl_id, reg_name, value):
        reg = CONTROL_TABLE.get(reg_name)
        if not reg: return False
        
        if reg["size"] == 1:
            dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler, dxl_id, reg["address"], value)
        else:
            dxl_comm_result, dxl_error = self.packetHandler.write2ByteTxRx(self.portHandler, dxl_id, reg["address"], value)
        
        return dxl_comm_result == 0 and dxl_error == 0

    def get_all_registers(self, dxl_id):
        data = {}
        for reg_name in CONTROL_TABLE.keys():
            val = self.read_register(dxl_id, reg_name)
            if val is not None:
                data[reg_name] = val
        return data

controller = ServoController()
