#!/usr/bin/env python3

import rclpy

from geometry_msgs.msg import PoseStamped
from pymoveit2 import MoveIt2

from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.qos import QoSProfile


class MoveItPoseCommander(Node):

    def __init__(self):
        super().__init__("moveit_pose_commander")

        self.callback_group = ReentrantCallbackGroup()

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
            use_move_group_action=True,
            callback_group=self.callback_group,
        )

        self.moveit2.max_velocity = 0.5
        self.moveit2.max_acceleration = 0.5

        self.last_pose = None

        self.create_subscription(
            PoseStamped,
            "/controller_target_pose",
            self.pose_callback,
            QoSProfile(depth=1),
            callback_group=self.callback_group,
        )

        self.get_logger().info(
            "MoveIt Pose Commander ready"
        )

    def poses_equal(
        self,
        pose_a,
        pose_b,
        tolerance=0.001,
    ):

        return (
            abs(pose_a.position.x - pose_b.position.x) < tolerance
            and abs(pose_a.position.y - pose_b.position.y) < tolerance
            and abs(pose_a.position.z - pose_b.position.z) < tolerance
            and abs(pose_a.orientation.x - pose_b.orientation.x) < tolerance
            and abs(pose_a.orientation.y - pose_b.orientation.y) < tolerance
            and abs(pose_a.orientation.z - pose_b.orientation.z) < tolerance
            and abs(pose_a.orientation.w - pose_b.orientation.w) < tolerance
        )

    def pose_callback(self, msg: PoseStamped):

        self.get_logger().info(
            f"Received pose: "
            f"x={msg.pose.position.x:.3f} "
            f"y={msg.pose.position.y:.3f} "
            f"z={msg.pose.position.z:.3f}"
        )

        if (
            self.last_pose is not None
            and self.poses_equal(
                msg.pose,
                self.last_pose,
            )
        ):
            self.get_logger().info(
                "Pose unchanged, ignoring"
            )
            return

        try:

            self.get_logger().info(
                "Planning and executing..."
            )

            self.moveit2.move_to_pose(
                position=msg.pose.position,
                quat_xyzw=msg.pose.orientation,
            )

            self.last_pose = msg.pose

            self.get_logger().info(
                "Move request sent"
            )

        except Exception as e:

            self.get_logger().error(
                f"MoveIt exception: {e}"
            )

    def destroy_node(self):

        self.get_logger().info(
            "Shutting down MoveIt Pose Commander"
        )

        super().destroy_node()


def main(args=None):

    rclpy.init(args=args)

    node = MoveItPoseCommander()

    executor = rclpy.executors.MultiThreadedExecutor(
        num_threads=2
    )

    executor.add_node(node)

    try:

        executor.spin()

    except KeyboardInterrupt:

        pass

    finally:

        executor.shutdown()

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()