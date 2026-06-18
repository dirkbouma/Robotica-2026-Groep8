#!/usr/bin/env python3

from threading import Thread

import rclpy

from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup

from pymoveit2 import MoveIt2


def main():
    rclpy.init()

    node = Node("hogpie_pose_test")

    callback_group = ReentrantCallbackGroup()

    moveit2 = MoveIt2(
        node=node,
        joint_names=[
            "lift_joint",
            "joint1",
            "joint2",
            "joint3",
        ],
        base_link_name="base_link",
        end_effector_name="tool_link",
        group_name="arm",
        callback_group=callback_group,
    )

    executor = rclpy.executors.MultiThreadedExecutor(2)
    executor.add_node(node)

    executor_thread = Thread(
        target=executor.spin,
        daemon=True,
    )

    executor_thread.start()

    node.create_rate(1.0).sleep()

    moveit2.max_velocity = 0.5
    moveit2.max_acceleration = 0.5
    
    position = [
        0.231,
        -0.041,
        0.226,
    ]

    quat_xyzw = [
        0.0,
        0.0,
        0.0,
        1.0,
    ]

    node.get_logger().info(
        f"Moving to pose:"
        f" position={position}"
        f" quat={quat_xyzw}"
    )

    moveit2.move_to_pose(
        position=position,
        quat_xyzw=quat_xyzw,
        cartesian=False,
    )

    moveit2.wait_until_executed()

    node.get_logger().info("Motion complete")

    rclpy.shutdown()

    executor_thread.join()


if __name__ == "__main__":
    main()