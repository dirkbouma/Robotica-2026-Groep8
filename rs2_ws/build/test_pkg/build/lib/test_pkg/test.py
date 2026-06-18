#!/usr/bin/env python3


import struct
import fcntl
import time

import rclpy
from rclpy.node import Node

from std_msgs.msg import Int32MultiArray

from dynamixel_sdk import PortHandler, PacketHandler


# config

DEVICENAME = "/dev/ttyAMA0"
BAUDRATE = 1000000
PROTOCOL_VERSION = 1.0
SERVO_ID = 5

# IDLE POSITION

IDLE_POSITION = 500
IDLE_SPEED = 100

# RS485

TIOCSRS485 = 0x542F
SER_RS485_ENABLED = 0x00000001
SER_RS485_RTS_ON_SEND = 0x00000002
SER_RS485_RTS_AFTER_SEND = 0x00000004

# AX12 REGISTERS

ADDR_TORQUE_ENABLE = 24
ADDR_LED = 25
ADDR_GOAL_POSITION = 30
ADDR_MOVING_SPEED = 32
TORQUE_ENABLE = 1


class ServoController(Node):

    def __init__(self):

        super().__init__('servo_controller')

        self.port_handler = PortHandler(
            DEVICENAME
        )

        self.packet_handler = PacketHandler(
            PROTOCOL_VERSION
        )

        # Open port
        if not self.port_handler.openPort():

            raise RuntimeError(
                f"Failed to open {DEVICENAME}"
            )

        # Set baudrate
        if not self.port_handler.setBaudRate(
            BAUDRATE
        ):

            raise RuntimeError(
                "Failed to set baudrate"
            )

        # Enable RS485
        try:

            rs485_flags = (
                SER_RS485_ENABLED |
                SER_RS485_RTS_ON_SEND
            )

            buf = struct.pack(
                'IIIIIIII',
                rs485_flags,
                0, 0, 0, 0, 0, 0, 0
            )

            fcntl.ioctl(
                self.port_handler.ser.fileno(),
                TIOCSRS485,
                buf
            )

            print("RS485 ioctl applied")

            self.get_logger().info(
                "RS485 enabled"
            )

        except Exception as e:

            self.get_logger().error(
                f"RS485 setup failed: {e}"
            )

        # Enable torque for servo 17
        self.packet_handler.write1ByteTxOnly(
            self.port_handler,
            SERVO_ID,
            ADDR_TORQUE_ENABLE,
            TORQUE_ENABLE
        )

        time.sleep(0.1)

        # Last strawberry detection
        self.last_detection_time = time.time()

        # Subscribe
        self.subscription = self.create_subscription(
            Int32MultiArray,
            '/ax12/move',
            self.move_callback,
            10
        )

        # Timer callback every 5 seconds
        self.counter_timer = self.create_timer(
            5.0,
            self.counter_callback
        )

        self.get_logger().info(
            "Servo controller started"
        )





    def move_callback(self, msg):

        if len(msg.data) != 3:

            self.get_logger().error(
                "Expected [id, position, speed]"
            )

            return

        dxl_id, position, speed = msg.data

        # Update detection timestamp
        self.last_detection_time = time.time()

        # Clamp values
        position = max(0, min(1023, position))

        speed = max(1, min(1023, speed))

        # Set speed
        self.packet_handler.write2ByteTxOnly(
            self.port_handler,
            dxl_id,
            ADDR_MOVING_SPEED,
            speed
        )

        # Set position
        self.packet_handler.write2ByteTxOnly(
            self.port_handler,
            dxl_id,
            ADDR_GOAL_POSITION,
            position
        )

        self.get_logger().info(
            f"Move ID={dxl_id} "
            f"Pos={position} "
            f"Speed={speed}"
        )

    # COUNTER CALLBACK
    

    def counter_callback(self):

        current_time = time.time()

        # No strawberry detected for 1 second
        if current_time - self.last_detection_time > 1.0:

            self.get_logger().info(
                "No strawberry detected -> idle move"
            )

            # Create idle move command
            msg = Int32MultiArray()

            msg.data = [
                SERVO_ID,
                IDLE_POSITION,
                IDLE_SPEED
            ]


            self.move_callback(msg)



    def destroy_node(self):

        self.port_handler.closePort()

        super().destroy_node()



def main(args=None):

    rclpy.init(args=args)

    node = ServoController()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == '__main__':
    main()