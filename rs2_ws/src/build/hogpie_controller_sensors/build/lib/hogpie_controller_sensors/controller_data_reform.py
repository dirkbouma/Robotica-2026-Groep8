#!/usr/bin/env python3

import math

import rclpy

from rclpy.node import Node

from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped


class Controller_data_reform(Node):

    def __init__(self):
        super().__init__('controller_data_reform')

        self.subscription = self.create_subscription(
            String,
            'tcp_data',
            self.listener_callback,
            10
        )

        self.pose_pub = self.create_publisher(
            PoseStamped,
            '/controller_target_pose',
            10
        )

        #
        # Initial target position
        #
        self.x = 0.20
        self.y = 0.00
        self.z = 0.10

        #
        # Initial tool orientation
        # (yaw around Z axis)
        #
        self.yaw = 0.0

        #
        # Movement scaling
        #
        self.step = 0.005

        #
        # Rotation scaling
        #
        self.rotation_step = 0.03

        self.get_logger().info(
            'Controller Data Reform started'
        )

    def apply_deadzone(self, value):

        if abs(value) < 0.10:
            return 0.0

        return value

    def listener_callback(self, msg):

        parts = msg.data.strip().split(',')

        #
        # Expected format:
        # J,lx,ly,rx,ry,button
        #
        if len(parts) != 6:
            return

        if parts[0] != 'J':
            return

        try:
            lx = float(parts[1])
            ly = float(parts[2])
            rx = float(parts[3])
            ry = float(parts[4])
            button = int(parts[5])

        except ValueError:
            return

        #
        # Apply deadzone
        #
        lx = self.apply_deadzone(lx)
        ly = self.apply_deadzone(ly)
        rx = self.apply_deadzone(rx)
        ry = self.apply_deadzone(ry)

        #
        # Position control
        #
        # Left stick:
        # X/Y movement
        #
        self.x += lx * self.step
        self.y += ly * self.step

        #
        # Right stick vertical:
        # Z movement
        #
        self.z += ry * self.step

        #
        # Right stick horizontal:
        # Tool orientation (yaw)
        #
        self.yaw += rx * self.rotation_step

        #
        # Position limits
        #
        self.x = max(0.05, min(0.40, self.x))
        self.y = max(-0.40, min(0.40, self.y))
        self.z = max(0.02, min(0.30, self.z))

        pose = PoseStamped()

        pose.header.stamp = (
            self.get_clock().now().to_msg()
        )

        pose.header.frame_id = "base_link"

        #
        # Cartesian position
        #
        pose.pose.position.x = self.x
        pose.pose.position.y = self.y
        pose.pose.position.z = self.z

        #
        # Quaternion from yaw
        #
        pose.pose.orientation.x = 0.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = math.sin(
            self.yaw / 2.0
        )
        pose.pose.orientation.w = math.cos(
            self.yaw / 2.0
        )

        self.pose_pub.publish(pose)

        self.get_logger().info(
            f"Target Pose -> "
            f"x={self.x:.3f}, "
            f"y={self.y:.3f}, "
            f"z={self.z:.3f}, "
            f"yaw={self.yaw:.3f}, "
            f"button={button}"
        )


def main(args=None):

    rclpy.init(args=args)

    controller_data_reform = Controller_data_reform()

    try:
        rclpy.spin(controller_data_reform)

    except KeyboardInterrupt:
        pass

    controller_data_reform.destroy_node()

    rclpy.shutdown()


if __name__ == '__main__':
    main()