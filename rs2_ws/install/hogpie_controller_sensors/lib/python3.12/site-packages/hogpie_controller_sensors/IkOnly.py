#!/usr/bin/env python3

import rclpy

from rclpy.node import Node

from pymoveit2 import MoveIt2


class IKOnly(Node):

    def __init__(self):
        super().__init__("ik_only")

        self.moveit2 = MoveIt2(
            node=self,
            joint_names=[
                "lift_joint",
                "joint1",
                "joint2",
                "joint3",
            ],
            base_link_name="base_link",
            end_effector_name="tool_link",
            group_name="arm",
        )

        result = self.moveit2.compute_ik(
            position=(0.23, -0.04, 0.22),
            quat_xyzw=(0.0, 0.0, 0.0, 1.0),
            ik_link_name="tool_link",
        )

        print(result)


def main():

    rclpy.init()

    node = IKOnly()

    rclpy.spin_once(node, timeout_sec=1.0)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main()