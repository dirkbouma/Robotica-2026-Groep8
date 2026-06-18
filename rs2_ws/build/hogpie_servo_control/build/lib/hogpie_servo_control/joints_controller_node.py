#!/usr/bin/env python3

import rclpy

from rclpy.node import Node

from std_msgs.msg import Int16MultiArray
from std_msgs.msg import Bool

from sensor_msgs.msg import JointState


# =====================================================
# CONFIG
# =====================================================

KP = 250.0

MAX_SPEED = 1000

MIN_SPEED = 100

POSITION_TOLERANCE = 0.01

CONTROL_PERIOD = 0.02


JOINT_CONFIG = {

    "lift_joint": {
        "servo_index": 0,
        "direction": 1
    },

    "joint1": {
        "servo_index": 1,
        "direction": -1
    },

    "joint2": {
        "servo_index": 2,
        "direction": -1
    },

    "joint3": {
        "servo_index": 3,
        "direction": -1
    }

}


# =====================================================
# CONTROLLER
# =====================================================

class JointController(Node):

    def __init__(self):

        super().__init__("joint_controller")

        self.current_positions = {}

        self.target_positions = {}

        self.motion_complete = True

        self.create_subscription(
            JointState,
            "/joint_states",
            self.joint_state_callback,
            10
        )

        self.create_subscription(
            JointState,
            "/target_joint_state",
            self.target_callback,
            10
        )

        self.cmd_pub = self.create_publisher(
            Int16MultiArray,
            "/ax12_wheel_cmd",
            10
        )

        self.motion_complete_pub = self.create_publisher(
            Bool,
            "/hogpie_arm/motion_complete",
            10
        )

        self.control_timer = self.create_timer(
            CONTROL_PERIOD,
            self.control_loop
        )

        self.get_logger().info(
            "Joint controller started"
        )

    # =================================================

    def joint_state_callback(self, msg):

        for name, position in zip(
            msg.name,
            msg.position
        ):
            self.current_positions[name] = position

    # =================================================

    def target_callback(self, msg):

        for name, position in zip(
            msg.name,
            msg.position
        ):
            self.target_positions[name] = position

        self.motion_complete = False

        motion_msg = Bool()
        motion_msg.data = False

        self.motion_complete_pub.publish(
            motion_msg
        )

        self.get_logger().info(
            "Received target joint state"
        )

    # =================================================

    def control_loop(self):

        if not self.target_positions:
            return

        speeds = [0, 0, 0, 0, 0]


        all_reached = True

        for joint_name, target in \
                self.target_positions.items():

            if joint_name not in JOINT_CONFIG:
                continue

            if joint_name not in self.current_positions:
                continue

            current = (
                self.current_positions[
                    joint_name
                ]
            )

            error = target - current

            self.get_logger().info(
                f"{joint_name}: "
                f"target={target:.3f} "
                f"current={current:.3f} "
                f"error={error:.3f}"
            )

            if abs(error) < POSITION_TOLERANCE:

                speed = 0

            else:

                all_reached = False

                speed = KP * error

                speed = max(
                    -MAX_SPEED,
                    min(MAX_SPEED, speed)
                )

                if abs(speed) < MIN_SPEED:

                    speed = (
                        MIN_SPEED
                        if speed > 0
                        else -MIN_SPEED
                    )

                speed *= (
                    JOINT_CONFIG[
                        joint_name
                    ]["direction"]
                )

            servo_index = (
                JOINT_CONFIG[
                    joint_name
                ]["servo_index"]
            )

            speeds[servo_index] = int(speed)

        cmd = Int16MultiArray()

        cmd.data = speeds

        self.cmd_pub.publish(cmd)

        # ---------------------------------------------
        # Motion Complete
        # ---------------------------------------------

        if (
            all_reached
            and not self.motion_complete
        ):

            self.motion_complete = True

            motion_msg = Bool()
            motion_msg.data = True

            self.motion_complete_pub.publish(
                motion_msg
            )

            self.get_logger().info(
                "Target reached"
            )

            self.target_positions.clear()

    # =================================================

    def stop_all(self):

        msg = Int16MultiArray()

        msg.data = [0, 0, 0, 0, 0]

        self.cmd_pub.publish(msg)

    # =================================================

    def destroy_node(self):

        self.stop_all()

        super().destroy_node()


# =====================================================
# MAIN
# =====================================================

def main(args=None):

    rclpy.init(args=args)

    node = JointController()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()