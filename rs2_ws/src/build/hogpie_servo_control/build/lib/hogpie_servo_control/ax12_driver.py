#!/usr/bin/env python3

import struct
import fcntl

import rclpy
from rclpy.node import Node

from std_msgs.msg import Int16MultiArray

from dynamixel_sdk import PortHandler, PacketHandler


# =====================================================
# CONFIG
# =====================================================

DEVICENAME = "/dev/ttyAMA0"
BAUDRATE = 1000000
PROTOCOL_VERSION = 1.0

SERVO_IDS = [1, 2, 3, 4, 5]

ADDR_MOVING_SPEED = 32

# =====================================================
# RS485
# =====================================================

TIOCSRS485 = 0x542F

SER_RS485_ENABLED = 0x00000001
SER_RS485_RTS_ON_SEND = 0x00000002


class AX12Driver(Node):

    def __init__(self):
        super().__init__("ax12_driver")

        self.port_handler = PortHandler(DEVICENAME)
        self.packet_handler = PacketHandler(PROTOCOL_VERSION)

        self.open_bus()

        self.subscription = self.create_subscription(
            Int16MultiArray,
            "/ax12_wheel_cmd",
            self.command_callback,
            10
        )

        self.get_logger().info("AX12 driver ready")

    # =================================================

    def open_bus(self):

        if not self.port_handler.openPort():
            raise RuntimeError(
                f"Failed to open {DEVICENAME}"
            )

        if not self.port_handler.setBaudRate(BAUDRATE):
            raise RuntimeError(
                f"Failed to set baudrate {BAUDRATE}"
            )

        flags = (
            SER_RS485_ENABLED |
            SER_RS485_RTS_ON_SEND
        )

        buf = struct.pack(
            "IIIIIIII",
            flags,
            0, 0, 0, 0, 0, 0, 0
        )

        try:

            fcntl.ioctl(
                self.port_handler.ser.fileno(),
                TIOCSRS485,
                buf
            )

            self.get_logger().info(
                "RS485 enabled"
            )

        except Exception as e:

            self.get_logger().warn(
                f"RS485 setup failed: {e}"
            )

    # =================================================

    @staticmethod
    def speed_to_ax12(speed):

        speed = max(-1023, min(1023, speed))

        if speed >= 0:
            return speed

        return 1024 + abs(speed)

    # =================================================

    def set_speed(self, dxl_id, speed):

        value = self.speed_to_ax12(speed)

        comm_result, error = \
            self.packet_handler.write2ByteTxRx(
                self.port_handler,
                dxl_id,
                ADDR_MOVING_SPEED,
                value
            )

        if comm_result != 0:

            self.get_logger().error(
                f"ID {dxl_id}: "
                + self.packet_handler.getTxRxResult(
                    comm_result
                )
            )

            return

        if error != 0:

            self.get_logger().error(
                f"ID {dxl_id}: "
                + self.packet_handler.getRxPacketError(
                    error
                )
            )

    # =================================================

    def command_callback(self, msg):

        if len(msg.data) != 5:

            self.get_logger().warning(
                "Expected 5 values"
            )

            return

        for dxl_id, speed in zip(
            SERVO_IDS,
            msg.data
        ):
            self.set_speed(
                dxl_id,
                int(speed)
            )

    # =================================================

    def stop_all(self):

        for dxl_id in SERVO_IDS:
            self.set_speed(dxl_id, 0)

    # =================================================

    def destroy_node(self):

        self.stop_all()

        self.port_handler.closePort()

        super().destroy_node()


def main(args=None):

    rclpy.init(args=args)

    node = AX12Driver()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()