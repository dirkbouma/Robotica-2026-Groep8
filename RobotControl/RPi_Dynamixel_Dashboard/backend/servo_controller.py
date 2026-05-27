import time
import platform
import logging
from .ax12a_registers import CONTROL_TABLE

logger = logging.getLogger(__name__)

# Fallback for Windows/Mac development
IS_RPI = platform.system() == "Linux" and ("arm" in platform.machine() or "aarch64" in platform.machine())

# Constants for Dynamixel Protocol 1.0 (used by AX-12A)
PROTOCOL_VERSION = 1.0
BAUDRATE = 1000000

# Defaults for Raspberry Pi
if IS_RPI:
    DEVICENAME = '/dev/ttyAMA0' # or '/dev/serial0'
    DIR_PIN = 18 # User can change this if needed
else:
    DEVICENAME = 'COM1'
    DIR_PIN = None

try:
    if IS_RPI:
        import gpiozero
        from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
        # Initialize DIR pin
        dir_pin = gpiozero.DigitalOutputDevice(DIR_PIN)
        dir_pin.off() # RX mode by default
    else:
        raise ImportError("Not on RPi")
except ImportError:
    IS_RPI = False
    logger.warning("Running in MOCK mode (dynamixel_sdk or gpiozero not found or not on RPi)")

class MockPortHandler:
    def openPort(self): return True
    def setBaudRate(self, baudrate): return True
    def closePort(self): pass

class MockPacketHandler:
    def __init__(self):
        # Mock RAM
        self.mock_memory = {}
        for i in range(1, 10):
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
        if IS_RPI:
            self.portHandler = PortHandler(DEVICENAME)
            self.packetHandler = PacketHandler(PROTOCOL_VERSION)
            if self.portHandler.openPort():
                logger.info("Succeeded to open the port")
            else:
                logger.error("Failed to open the port")
            
            if self.portHandler.setBaudRate(BAUDRATE):
                logger.info("Succeeded to change the baudrate")
            else:
                logger.error("Failed to change the baudrate")
        else:
            self.portHandler = MockPortHandler()
            self.packetHandler = MockPacketHandler()

    def set_tx_mode(self):
        if IS_RPI: dir_pin.on()
        
    def set_rx_mode(self):
        if IS_RPI: dir_pin.off()

    def scan(self):
        found_ids = []
        for i in range(1, 253):
            self.set_tx_mode()
            # The ping sends packet and then expects a response.
            # dynamixel_sdk handles tx/rx automatically, but with a half duplex level shifter we need to toggle DIR.
            # NOTE: For dynamixel_sdk with half-duplex UART on Pi, standard PortHandler might not toggle DIR fast enough.
            # However, dynamixel_sdk doesn't have hooks for DIR toggle per byte. 
            # Often, hardware auto-direction (like a 74LS241 or 74HC126 with TX acting as DIR) is used, or a custom PortHandler.
            # Assuming custom handling or slow enough response.
            model_number, dxl_comm_result, dxl_error = self.packetHandler.ping(self.portHandler, i)
            self.set_rx_mode()
            if dxl_comm_result == 0:
                found_ids.append(i)
        return found_ids

    def read_register(self, dxl_id, reg_name):
        reg = CONTROL_TABLE.get(reg_name)
        if not reg: return None
        
        self.set_tx_mode()
        # Hacky workaround: setting rx mode immediately after tx might be too fast/slow.
        # Ideally, we use an auto-dir level shifter or modifying the C-level dynamixel_sdk.
        if reg["size"] == 1:
            data, dxl_comm_result, dxl_error = self.packetHandler.read1ByteTxRx(self.portHandler, dxl_id, reg["address"])
        else:
            data, dxl_comm_result, dxl_error = self.packetHandler.read2ByteTxRx(self.portHandler, dxl_id, reg["address"])
        self.set_rx_mode()
        
        return data

    def write_register(self, dxl_id, reg_name, value):
        reg = CONTROL_TABLE.get(reg_name)
        if not reg: return False
        
        self.set_tx_mode()
        if reg["size"] == 1:
            dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler, dxl_id, reg["address"], value)
        else:
            dxl_comm_result, dxl_error = self.packetHandler.write2ByteTxRx(self.portHandler, dxl_id, reg["address"], value)
        self.set_rx_mode()
        
        return dxl_comm_result == 0

    def get_all_registers(self, dxl_id):
        data = {}
        for reg_name in CONTROL_TABLE.keys():
            val = self.read_register(dxl_id, reg_name)
            if val is not None:
                data[reg_name] = val
        return data

controller = ServoController()
