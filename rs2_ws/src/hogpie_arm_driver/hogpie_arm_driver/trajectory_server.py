#!/usr/bin/env python3

import rclpy

from rclpy.node import Node
from rclpy.action import ActionServer

from control_msgs.action import FollowJointTrajectory

from trajectory_msgs.msg import JointTrajectory


class TrajectoryServer(Node):

    def __init__(self):

        super().__init__("trajectory_server")

        self.trajectory_pub = self.create_publisher(
            JointTrajectory,
            "/joint_trajectory",
            10
        )

        self._action_server = ActionServer(
            self,
            FollowJointTrajectory,
            "/arm_controller/follow_joint_trajectory",
            self.execute_callback,
        )

        self.get_logger().info(
            "Trajectory server started"
        )

    # =====================================

    def execute_callback(
        self,
        goal_handle
    ):

        self.get_logger().info(
            "Goal received"
        )

        trajectory = (
            goal_handle.request.trajectory
        )

        self.get_logger().info(
            f"Joints: "
            f"{trajectory.joint_names}"
        )

        self.get_logger().info(
            f"Points: "
            f"{len(trajectory.points)}"
        )

        if len(trajectory.points) == 0:

            self.get_logger().warning(
                "Received empty trajectory"
            )

            goal_handle.abort()

            result = (
                FollowJointTrajectory.Result()
            )

            result.error_code = (
                FollowJointTrajectory.Result.INVALID_GOAL
            )

            return result

        self.trajectory_pub.publish(
            trajectory
        )

        self.get_logger().info(
            "Forwarded trajectory to executor"
        )

        goal_handle.succeed()

        result = (
            FollowJointTrajectory.Result()
        )

        result.error_code = (
            FollowJointTrajectory.Result.SUCCESSFUL
        )

        return result


def main(args=None):

    rclpy.init(args=args)

    node = TrajectoryServer()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()