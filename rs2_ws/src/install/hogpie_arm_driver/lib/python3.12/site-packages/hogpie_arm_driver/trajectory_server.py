from rclpy.node import Node
import rclpy
import time

from rclpy.action import ActionServer

from control_msgs.action import FollowJointTrajectory

from sensor_msgs.msg import JointState

class TrajectoryServer(Node):

    def __init__(self):
        super().__init__("trajectory_server")

        self._action_server = ActionServer(
            self,
            FollowJointTrajectory,
            "/arm_controller/follow_joint_trajectory",
            self.execute_callback,
        )
        self.target_pub = self.create_publisher(
            JointState,
            "/hogpie_arm/target_joint_state",
            10
        )
        self.get_logger().info(
            "Trajectory server started"
        )

    def execute_callback(self, goal_handle):

        self.get_logger().info("Goal received")

        trajectory = goal_handle.request.trajectory

        self.get_logger().info(
            f"Joints: {trajectory.joint_names}"
        )

        self.get_logger().info(
            f"Points: {len(trajectory.points)}"
        )

        if trajectory.points:

            for i, point in enumerate(trajectory.points):

                current_time = (
                    point.time_from_start.sec +
                    point.time_from_start.nanosec * 1e-9
                )

                self.get_logger().info(
                    f"Point {i}: "
                    f"t={current_time:.3f}s "
                    f"positions={list(point.positions)}"
                )

            previous_time = 0.0

            for i, point in enumerate(trajectory.points):

                current_time = (
                    point.time_from_start.sec +
                    point.time_from_start.nanosec * 1e-9
                )

                delay = current_time - previous_time

                if delay > 0:
                    time.sleep(delay)

                if not point.positions:
                    continue
                
                msg = JointState()

                msg.header.stamp = (
                    self.get_clock().now().to_msg()
                )

                msg.name = trajectory.joint_names

                msg.position = list(point.positions)

                self.target_pub.publish(msg)

                self.get_logger().info(
                    f"Published point {i}"
                )
                
                if i == len(trajectory.points) - 1:

                    self.get_logger().info("FINAL POINT")

                    for name, pos in zip(
                        trajectory.joint_names,
                        point.positions
                    ):
                        self.get_logger().info(
                            f"{name}: {pos}"
                        )
                    
                previous_time = current_time
        
        self.get_logger().info(
            "Trajectory execution complete"
        )
        goal_handle.succeed()

        result = FollowJointTrajectory.Result()

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

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main() 
