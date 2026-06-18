#!/usr/bin/env python3

import rclpy

from rclpy.node import Node

from std_msgs.msg import Bool

from sensor_msgs.msg import JointState

from trajectory_msgs.msg import JointTrajectory

POINT_SKIP_FACTOR = 20

class TrajectoryExecutor(Node):

    def __init__(self):

        super().__init__(
            "trajectory_executor"
        )

        self.current_trajectory = None

        self.current_point_index = 0

        self.waiting_for_completion = False

        self.create_subscription(
            JointTrajectory,
            "/joint_trajectory",
            self.trajectory_callback,
            10
        )

        self.create_subscription(
            Bool,
            "/hogpie_arm/motion_complete",
            self.motion_complete_callback,
            10
        )

        self.target_pub = (
            self.create_publisher(
                JointState,
                "/target_joint_state",
                10
            )
        )

        self.get_logger().info(
            "Trajectory executor started"
        )

    # =====================================

    def trajectory_callback(self, msg):

        if len(msg.points) == 0:

            self.get_logger().warning(
                "Empty trajectory"
            )

            return
        
        if self.current_trajectory is not None:

            self.get_logger().warning(
                "Trajectory already running"
            )
            return

        original_count = len(msg.points)

        filtered_points = msg.points[::POINT_SKIP_FACTOR]

        # Always keep final point
        if filtered_points[-1] != msg.points[-1]:
            filtered_points.append(
                msg.points[-1]
            )

        msg.points = filtered_points

        self.get_logger().info(
            f"Trajectory decimated: "
            f"{original_count} -> "
            f"{len(msg.points)} points"
        )

        self.current_trajectory = msg

        self.current_point_index = 0

        self.waiting_for_completion = False

        self.publish_next_point()

    # =====================================

    def publish_next_point(self):

        if self.current_trajectory is None:
            return

        if (
            self.current_point_index
            >= len(
                self.current_trajectory.points
            )
        ):

            self.get_logger().info(
                "Trajectory complete"
            )

            self.current_trajectory = None

            return

        point = (
            self.current_trajectory.points[
                self.current_point_index
            ]
        )

        msg = JointState()

        msg.name = (
            self.current_trajectory.joint_names
        )

        msg.position = (
            list(point.positions)
        )

        self.target_pub.publish(msg)

        self.waiting_for_completion = True

        self.get_logger().info(
            f"Executing point "
            f"{self.current_point_index + 1}/"
            f"{len(self.current_trajectory.points)}"
        )

    # =====================================

    def motion_complete_callback(
        self,
        msg
    ):

        if not msg.data:
            return

        if not self.waiting_for_completion:
            return

        self.waiting_for_completion = False

        self.current_point_index += 1

        self.publish_next_point()


def main(args=None):

    rclpy.init(args=args)

    node = TrajectoryExecutor()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()