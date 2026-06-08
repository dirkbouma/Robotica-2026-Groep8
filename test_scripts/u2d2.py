from dynamixel_sdk import *

port = PortHandler('/dev/ttyUSB0')
packet = PacketHandler(1.0)

port.openPort()
port.setBaudRate(1000000)

model_number, result, error = packet.ping(port, 1)
print(model_number, result, error)