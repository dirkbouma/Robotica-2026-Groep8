#!/usr/bin/env python3

import time
import smbus2

import rclpy

from rclpy.node import Node

from std_msgs.msg import Float32MultiArray


TCA_ADDR = 0x70
AS5600_ADDR = 0x36

CHANNELS = [2, 3, 4, 5]

PUBLISH_RATE = 0.05  # 20 Hz


class ContinuousEncoder:

    def __init__(self):

        self.last_angle = None
        self.turn_count = 0

    def update(self, angle_deg):

        if self.last_angle is not None:

            delta = angle_deg - self.last_angle

            if delta > 180.0:
                self.turn_count -= 1

            elif delta < -180.0:
                self.turn_count += 1

        self.last_angle = angle_deg

        return angle_deg + (self.turn_count * 360.0)


class EncoderNode(Node):

    def __init__(self):

        super().__init__("encoder_node")

        self.bus = smbus2.SMBus(1)

        self.publisher = self.create_publisher(
            Float32MultiArray,
            "/encoder_angles",
            10
        )

        self.trackers = [
            ContinuousEncoder(),
            ContinuousEncoder(),
            ContinuousEncoder(),
            ContinuousEncoder()
        ]

        self.timer = self.create_timer(
            PUBLISH_RATE,
            self.publish_angles
        )

        self.log_counter = 0

        self.get_logger().info(
            "AS5600 encoder node started"
        )

    def select_channel(self, channel):

        self.bus.write_byte(
            TCA_ADDR,
            1 << channel
        )

    def read_angle(self):

        high = self.bus.read_byte_data(
            AS5600_ADDR,
            0x0E
        )

        low = self.bus.read_byte_data(
            AS5600_ADDR,
            0x0F
        )

        raw = (
            ((high & 0x0F) << 8)
            | low
        )

        return raw * 360.0 / 4096.0

    def publish_angles(self):

        try:

            values = []

            for index, channel in enumerate(CHANNELS):

                self.select_channel(channel)

                time.sleep(0.001)

                angle = self.read_angle()

                continuous_angle = (
                    self.trackers[index].update(angle)
                )

                values.append(
                    float(continuous_angle)
                )

            msg = Float32MultiArray()
            msg.data = values

            self.publisher.publish(msg)

            self.log_counter += 1

            if self.log_counter >= 20:

                self.log_counter = 0

                self.get_logger().info(
                    f"lift={values[0]:.2f}°, "
                    f"joint1={values[1]:.2f}°, "
                    f"joint2={values[2]:.2f}°, "
                    f"joint3={values[3]:.2f}°"
                )

        except Exception as e:

            self.get_logger().error(
                f"I2C read failed: {e}"
            )


def main(args=None):

    rclpy.init(args=args)

    node = EncoderNode()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.bus.close()

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()