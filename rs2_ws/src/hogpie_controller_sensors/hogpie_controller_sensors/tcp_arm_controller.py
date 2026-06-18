#!/usr/bin/env python3

import rclpy

from rclpy.node import Node

from std_msgs.msg import String
from std_msgs.msg import Int16MultiArray


BUTTON_1 = 1 << 0
BUTTON_2 = 1 << 1
BUTTON_3 = 1 << 2
BUTTON_4 = 1 << 3
BUTTON_5 = 1 << 4

MAX_SPEED = 800
DEADBAND = 0.05


class TcpArmController(Node):

    def __init__(self):
        super().__init__("tcp_arm_controller")

        self.selected_joint = 0

        self.subscription = self.create_subscription(
            String,
            "tcp_data",
            self.tcp_callback,
            10
        )

        self.publisher = self.create_publisher(
            Int16MultiArray,
            "/ax12_wheel_cmd",
            10
        )

        self.get_logger().info(
            "TCP arm controller started"
        )

        self.log_selected_joint()

    # =================================================

    def log_selected_joint(self):

        names = [
            "Lift",
            "Joint1",
            "Joint2",
            "Joint3",
            "Gripper"
        ]

        self.get_logger().info(
            f"Selected: {names[self.selected_joint]}"
        )

    # =================================================

    def select_joint(self, buttons):

        previous = self.selected_joint

        if buttons & BUTTON_1:
            self.selected_joint = 0

        elif buttons & BUTTON_2:
            self.selected_joint = 1

        elif buttons & BUTTON_3:
            self.selected_joint = 2

        elif buttons & BUTTON_4:
            self.selected_joint = 3

        elif buttons & BUTTON_5:
            self.selected_joint = 4

        if previous != self.selected_joint:
            self.log_selected_joint()

    # =================================================

    def tcp_callback(self, msg):

        try:

            parts = msg.data.strip().split(",")


            if len(parts) != 6:
                return

            if parts[0] != "J":
                return

            lx = float(parts[1])
            ly = float(parts[2])

            rx = float(parts[3])
            ry = float(parts[4])

            buttons = int(parts[5])

            self.select_joint(buttons)

            self.get_logger().info(
                f"lx={lx:.3f} ly={ly:.3f} rx={rx:.3f} ry={ry:.3f} buttons={buttons}"
            )
            if abs(ly) < DEADBAND:
                speed = 0
            else:
                speed = int(
                    ly * MAX_SPEED
                )
            self.get_logger().info(
                f"speed={speed}"
            )
            cmd = [0, 0, 0, 0, 0]

            cmd[self.selected_joint] = speed

            out = Int16MultiArray()
            out.data = cmd

            self.publisher.publish(out)

        except Exception as e:

            self.get_logger().warning(
                f"Failed to parse: {msg.data}"
            )

            self.get_logger().warning(
                str(e)
            )


def main(args=None):

    rclpy.init(args=args)

    node = TcpArmController()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()