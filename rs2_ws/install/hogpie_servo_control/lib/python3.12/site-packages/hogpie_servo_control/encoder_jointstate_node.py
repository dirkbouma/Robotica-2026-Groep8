#!/usr/bin/env python3

import math

import rclpy

from rclpy.node import Node

from std_msgs.msg import Float32MultiArray
from sensor_msgs.msg import JointState


LIFT_ZERO = 13.798828125
J1_ZERO = 208.828125
J2_ZERO = 309.814453125
J3_ZERO = -33.57


class EncoderJointStateNode(Node):

    def __init__(self):

        super().__init__("encoder_joint_state_node")

        self.subscription = self.create_subscription(
            Float32MultiArray,
            "/encoder_angles",
            self.encoder_callback,
            10
        )

        self.publisher = self.create_publisher(
            JointState,
            "/joint_states",
            10
        )

        self.get_logger().info(
            "Encoder JointState node started"
        )

    @staticmethod
    def normalize_deg(angle):

        while angle > 180.0:
            angle -= 360.0

        while angle < -180.0:
            angle += 360.0

        return angle

    def encoder_callback(self, msg):

        if len(msg.data) != 4:

            self.get_logger().warning(
                f"Expected 4 encoder values, got {len(msg.data)}"
            )

            return

        lift_deg = self.normalize_deg(
            msg.data[0] - LIFT_ZERO
        )

        joint1_deg = self.normalize_deg(
            msg.data[1] - J1_ZERO
        )

        joint2_deg = self.normalize_deg(
            msg.data[2] - J2_ZERO
        )

        joint3_deg = self.normalize_deg(
            msg.data[3] - J3_ZERO
        )

        joint_state = JointState()

        joint_state.header.stamp = (
            self.get_clock().now().to_msg()
        )

        joint_state.name = [
            "lift_joint",
            "joint1",
            "joint2",
            "joint3"
        ]

        joint_state.position = [
            0.0,
            math.radians(joint1_deg),
            math.radians(joint2_deg),
            math.radians(joint3_deg)
        ]

        self.publisher.publish(joint_state)


def main(args=None):

    rclpy.init(args=args)

    node = EncoderJointStateNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()