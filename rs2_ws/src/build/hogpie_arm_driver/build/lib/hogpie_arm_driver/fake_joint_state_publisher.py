#!/usr/bin/env python3


import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState


class FakeJointStatePublisher(Node):

    def __init__(self):
        super().__init__('fake_joint_state_publisher')

        self.publisher = self.create_publisher(
            JointState,
            '/joint_states',
            10
        )

        self.timer = self.create_timer(
            0.05,   # 20 Hz
            self.publish_joint_state
        )


        self.get_logger().info(
            'Fake JointState Publisher started'
        )

        self.positions = [
            0.088,
            0.0,
            0.0,
            0.0
        ]

        self.subscription = self.create_subscription(
            JointState,
            "/hogpie_arm/target_joint_state",
            self.target_callback,
            10
        )

    def target_callback(self, msg):
 
        joint_map = dict(zip(msg.name, msg.position))

        self.positions = [
            joint_map.get("lift_joint", 0.0),
            joint_map.get("joint1", 0.0),
            joint_map.get("joint2", 0.0),
            joint_map.get("joint3", 0.0),
        ]

        self.get_logger().info(
            f"Received target: {self.positions}"
        )

    def publish_joint_state(self):

        msg = JointState()

        msg.header.stamp = self.get_clock().now().to_msg()

        msg.name = [
            'lift_joint',
            'joint1',
            'joint2',
            'joint3'
        ]
        msg.position = self.positions

        self.publisher.publish(msg)

        


def main(args=None):
    rclpy.init(args=args)

    node = FakeJointStatePublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()