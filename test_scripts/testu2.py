#!/usr/bin/env python3

from dynamixel_sdk import *

PORT = "/dev/ttyUSB0"
BAUD = 1000000
PROTOCOL = 1.0

TORQUE_ENABLE = 24
GOAL_POSITION = 30
MOVING_SPEED = 32

port = PortHandler(PORT)
packet = PacketHandler(PROTOCOL)

if not port.openPort():
    print(f"Failed to open {PORT}")
    exit(1)

if not port.setBaudRate(BAUD):
    print(f"Failed to set baud rate {BAUD}")
    exit(1)

print(f"Connected to {PORT} @ {BAUD}")
print("Commands:")
print("  scan")
print("  move <id> <speed> <position>")
print("  quit")

while True:
    try:
        cmd = input("dxl> ").strip()

        if cmd == "quit":
            break

        elif cmd == "scan":
            found = []

            for dxl_id in range(254):
                model, result, error = packet.ping(port, dxl_id)

                if result == COMM_SUCCESS:
                    found.append(dxl_id)

            if found:
                print("Found IDs:", found)
            else:
                print("No servos found")

        elif cmd.startswith("move "):
            parts = cmd.split()

            if len(parts) != 4:
                print("Usage: move <id> <speed> <position>")
                continue

            dxl_id = int(parts[1])
            speed = int(parts[2])
            position = int(parts[3])

            packet.write1ByteTxRx(
                port,
                dxl_id,
                TORQUE_ENABLE,
                1
            )

            packet.write2ByteTxRx(
                port,
                dxl_id,
                MOVING_SPEED,
                speed
            )

            packet.write2ByteTxRx(
                port,
                dxl_id,
                GOAL_POSITION,
                position
            )

            print(
                f"Moved ID {dxl_id} "
                f"to {position} "
                f"at speed {speed}"
            )

        else:
            print("Unknown command")

    except KeyboardInterrupt:
        break

port.closePort()
print("Disconnected")