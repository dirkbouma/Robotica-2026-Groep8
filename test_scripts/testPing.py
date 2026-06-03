from dynamixel_sdk import PortHandler, PacketHandler
import serial.rs485
# =========================
# CONFIG
# =========================
DEVICENAME = "/dev/ttyAMA0"   # UART on GPIO14/15
BAUDRATE = 1000000            # AX-12A default baudrate
PROTOCOL_VERSION = 1.0
DXL_ID = 5

# =========================
# INITIALIZE SDK
# =========================
port_handler = PortHandler(DEVICENAME)
packet_handler = PacketHandler(PROTOCOL_VERSION)

# Open UART port
if not port_handler.openPort():
    print("Failed to open serial port")
    quit()

print("Serial port opened")

# Set baudrate
if not port_handler.setBaudRate(BAUDRATE):
    print("Failed to set baudrate")
    quit()

print("Baudrate configured")


# =========================
# PING SERVO
# =========================
model_number, comm_result, error = packet_handler.ping(
    port_handler,
    DXL_ID
)

# =========================
# RESULTS
# =========================
if comm_result != 0:
    print("Communication error:")
    print(packet_handler.getTxRxResult(comm_result))

elif error != 0:
    print("Servo returned error:")
    print(packet_handler.getRxPacketError(error))

else:
    print("Ping successful!")
    print(f"Servo ID: {DXL_ID}")
    print(f"Model Number: {model_number}")

# =========================
# CLEANUP
# =========================
port_handler.closePort()