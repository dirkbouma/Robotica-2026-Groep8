import serial
import serial.rs485

# 1. Open the port normally
ser = serial.Serial('/dev/ttyAMA0', 1000000, timeout=1.0)

# 2. Tell the Linux kernel to engage hardware RS485 auto-toggling
ser.rs485_mode = serial.rs485.RS485Settings(
    rts_level_for_tx=True,   # Set DIR pin HIGH when transmitting
    rts_level_for_rx=False,  # Set DIR pin LOW when receiving
    loopback=False,
    delay_before_tx=None,
    delay_before_rx=None
)

# 3. Test it!
packet = bytearray([0xFF, 0xFF, 0x01, 0x02, 0x01, 0xF7])

# You no longer need to touch the GPIO pin yourself.
# Just write the data, and the hardware handles the direction pin instantly!
ser.write(packet)

# Wait for the status packet reply
response = ser.read(6)
print([hex(b) for b in response])