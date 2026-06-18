#!/usr/bin/env python3

import rclpy

from geometry_msgs.msg import PoseStamped

from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.qos import QoSProfile

from pymoveit2 import MoveIt2


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

    def pose_callback(self, msg: PoseStamped):
        print("POSE CALLBACK FIRED")
        if self.last_pose is not None:

            if (
                msg.pose.position.x == self.last_pose.position.x and
                msg.pose.position.y == self.last_pose.position.y and
                msg.pose.position.z == self.last_pose.position.z and
                msg.pose.orientation.x == self.last_pose.orientation.x and
                msg.pose.orientation.y == self.last_pose.orientation.y and
                msg.pose.orientation.z == self.last_pose.orientation.z and
                msg.pose.orientation.w == self.last_pose.orientation.w
            ):
                return

        self.get_logger().info(
            f"Target pose: "
            f"x={msg.pose.position.x:.3f} "
            f"y={msg.pose.position.y:.3f} "
            f"z={msg.pose.position.z:.3f}"
        )

        ik_result = self.moveit2.compute_ik(
            position=(
                msg.pose.position.x,
                msg.pose.position.y,
                msg.pose.position.z,
            ),
            quat_xyzw=(
                msg.pose.orientation.x,
                msg.pose.orientation.y,
                msg.pose.orientation.z,
                msg.pose.orientation.w,
            ),
            ik_link_name="tool_link",
        )

        if ik_result is None:
            self.get_logger().warning(
                "No IK solution found"
            )
            return

        joint_map = dict(
            zip(
                ik_result.name,
                ik_result.position,
            )
        )

        joint_positions = [
            joint_map["lift_joint"],
            joint_map["joint1"],
            joint_map["joint2"],
            joint_map["joint3"],
        ]

        self.get_logger().info(
            f"Joint target: {joint_positions}"
        )

        self.moveit2.move_to_configuration(
            joint_positions=joint_positions
        )

        self.moveit2.wait_until_executed()

        self.last_pose = msg.pose


def main(args=None):

    rclpy.init(args=args)

    node = MoveItPoseCommander()

    executor = rclpy.executors.MultiThreadedExecutor(2)

    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main()