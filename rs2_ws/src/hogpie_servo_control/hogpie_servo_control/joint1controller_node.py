#!/usr/bin/env python3

import rclpy

from rclpy.node import Node

from std_msgs.msg import Float64
from std_msgs.msg import Int16MultiArray

from sensor_msgs.msg import JointState


# =====================================================
# CONFIG
# =====================================================

KP = 250.0

MAX_SPEED = 300

POSITION_TOLERANCE = 0.01

JOINT_NAME = "joint1"

LIFT_SERVO_INDEX = 0
JOINT1_SERVO_INDEX = 1
JOINT2_SERVO_INDEX = 2
JOINT3_SERVO_INDEX = 3
GRIPPER_SERVO_INDEX = 4
# Change to -1 if motion is reversed
JOINT1_DIRECTION = -1


# =====================================================
# CONTROLLER
# =====================================================

class Joint1Controller(Node):

    def __init__(self):

        super().__init__("joint1_controller")

        self.current_position = None

        self.target_position = None

        self.last_reported_state = False

        self.joint_state_sub = self.create_subscription(
            JointState,
            "/joint_states",
            self.joint_state_callback,
            10
        )

        self.target_sub = self.create_subscription(
            Float64,
            "/target_joint1",
            self.target_callback,
            10
        )

        self.cmd_pub = self.create_publisher(
            Int16MultiArray,
            "/ax12_wheel_cmd",
            10
        )

        self.control_timer = self.create_timer(
            0.02,
            self.control_loop
        )

        self.get_logger().info(
            "Joint1 controller started"
        )

    # =================================================

    def joint_state_callback(self, msg):

        try:

            idx = msg.name.index(JOINT_NAME)

            self.current_position = msg.position[idx]

        except ValueError:

            self.get_logger().warning(
                f"{JOINT_NAME} not found in JointState"
            )

    # =================================================

    def target_callback(self, msg):

        self.target_position = msg.data

        self.last_reported_state = False

        self.get_logger().info(
            f"New target: {self.target_position:.3f} rad"
        )

    # =================================================

    def publish_speed(self, speed):

        cmd = Int16MultiArray()

        values = [0, 0, 0, 0, 0]

        values[JOINT1_SERVO_INDEX] = int(speed)

        cmd.data = values

        self.cmd_pub.publish(cmd)

    # =================================================

    def control_loop(self):

        if self.current_position is None:
            return

        if self.target_position is None:
            return

        error = (
            self.target_position
            - self.current_position
        )

        # -----------------------------------------
        # Target reached
        # -----------------------------------------

        if abs(error) < POSITION_TOLERANCE:

            self.publish_speed(0)

            if not self.last_reported_state:

                self.get_logger().info(
                    f"Target reached "
                    f"({self.current_position:.3f} rad)"
                )

                self.last_reported_state = True

            return

        # -----------------------------------------
        # P Controller
        # -----------------------------------------

        speed = KP * error

        speed = max(
            -MAX_SPEED,
            min(MAX_SPEED, speed)
        )

        speed *= JOINT1_DIRECTION

        self.publish_speed(int(speed))

    # =================================================

    def destroy_node(self):

        self.publish_speed(0)

        super().destroy_node()


# =====================================================
# MAIN
# =====================================================

def main(args=None):

    rclpy.init(args=args)

    node = Joint1Controller()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()