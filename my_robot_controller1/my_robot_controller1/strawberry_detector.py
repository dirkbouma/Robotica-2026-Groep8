#!/usr/bin/env python3

import cv2
import numpy as np
import threading
import time

import rclpy
from rclpy.node import Node

from std_msgs.msg import Int32MultiArray

# ============================================================
# CAMERA
# ============================================================

RECAMERA_IP = "192.168.42.1"

RTSP_URL = (
    f"rtsp://admin:admin@{RECAMERA_IP}:554/live"
)

# ============================================================
# DETECTION
# ============================================================

MIN_AREA = 6000
MAX_AREA = 120000

MIN_ASPECT_RATIO = 0.4
MAX_ASPECT_RATIO = 1.6

MIN_CIRCULARITY = 0.25

MIN_RED_RATIO = 0.5

# ============================================================
# FIXED SERVO COMMAND
# ============================================================

SERVO_ID = 17
SERVO_POSITION = 750
SERVO_SPEED = 100

# ============================================================
# HSV RED
# ============================================================

lower_red1 = np.array([0, 120, 80])
upper_red1 = np.array([10, 255, 220])

lower_red2 = np.array([170, 120, 80])
upper_red2 = np.array([180, 255, 220])

# ============================================================

KERNEL_SMALL = np.ones((3, 3), np.uint8)

KERNEL_MEDIUM = np.ones((7, 7), np.uint8)

# ============================================================


class RTSPStream:

    def __init__(self, url):

        self.url = url

        self.frame = None

        self.lock = threading.Lock()

        self.running = False

    def start(self):

        self.cap = cv2.VideoCapture(
            self.url,
            cv2.CAP_FFMPEG
        )

        self.running = True

        thread = threading.Thread(
            target=self.update,
            daemon=True
        )

        thread.start()

    def update(self):

        while self.running:

            ret, frame = self.cap.read()

            if ret:

                with self.lock:
                    self.frame = frame

            else:
                time.sleep(0.1)

    def read(self):

        with self.lock:

            if self.frame is None:
                return None

            return self.frame.copy()

    def stop(self):

        self.running = False

        self.cap.release()


# ============================================================

def detect_strawberries(frame, mask_red):

    contours, _ = cv2.findContours(
        mask_red,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    results = []

    for contour in contours:

        area = cv2.contourArea(contour)

        if area < MIN_AREA:
            continue

        if area > MAX_AREA:
            continue

        x, y, w, h = cv2.boundingRect(
            contour
        )

        aspect_ratio = w / h

        if aspect_ratio < MIN_ASPECT_RATIO:
            continue

        if aspect_ratio > MAX_ASPECT_RATIO:
            continue

        perimeter = cv2.arcLength(
            contour,
            True
        )

        circularity = (
            4 * np.pi * area / (perimeter ** 2)
        ) if perimeter > 0 else 0

        if circularity < MIN_CIRCULARITY:
            continue

        mask_roi = np.zeros(
            mask_red.shape,
            np.uint8
        )

        cv2.drawContours(
            mask_roi,
            [contour],
            -1,
            255,
            -1
        )

        red_pixels = cv2.countNonZero(
            cv2.bitwise_and(
                mask_red,
                mask_red,
                mask=mask_roi
            )
        )

        total_pixels = cv2.countNonZero(
            mask_roi
        )

        red_ratio = (
            red_pixels / total_pixels
            if total_pixels > 0 else 0
        )

        if red_ratio < MIN_RED_RATIO:
            continue

        (cx, cy), radius = cv2.minEnclosingCircle(
            contour
        )

        results.append(
            (int(cx), int(cy), int(radius))
        )

    return results


# ============================================================

class StrawberryDetector(Node):

    def __init__(self):

        super().__init__('strawberry_detector')

        #
        # Publisher
        #
        self.publisher = self.create_publisher(
            Int32MultiArray,
            '/ax12/move',
            10
        )

        #
        # Camera
        #
        self.stream = RTSPStream(
            RTSP_URL
        )

        self.stream.start()

        #
        # Cooldown timer
        #
        self.last_move_time = 0

        #
        # Timer
        #
        self.timer = self.create_timer(
            0.03,
            self.process_frame
        )

        self.get_logger().info(
            "Strawberry detector started"
        )

    # ========================================================

    def process_frame(self):

        frame = self.stream.read()

        if frame is None:
            return

        frame = cv2.resize(
            frame,
            (854, 480)
        )

        blurred = cv2.GaussianBlur(
            frame,
            (5, 5),
            0
        )

        hsv = cv2.cvtColor(
            blurred,
            cv2.COLOR_BGR2HSV
        )

        mask_red1 = cv2.inRange(
            hsv,
            lower_red1,
            upper_red1
        )

        mask_red2 = cv2.inRange(
            hsv,
            lower_red2,
            upper_red2
        )

        mask_red = cv2.bitwise_or(
            mask_red1,
            mask_red2
        )

        mask_red = cv2.morphologyEx(
            mask_red,
            cv2.MORPH_OPEN,
            KERNEL_SMALL
        )

        mask_red = cv2.morphologyEx(
            mask_red,
            cv2.MORPH_DILATE,
            KERNEL_MEDIUM
        )

        detections = detect_strawberries(
            frame,
            mask_red
        )

        #
        # Strawberry detected
        #
        if len(detections) > 0:

            current_time = time.time()

            #
            # Max 1 command per second
            #
            if current_time - self.last_move_time > 1.0:

                msg = Int32MultiArray()

                #
                # [servo_id, position, speed]
                #
                msg.data = [
                    SERVO_ID,
                    SERVO_POSITION,
                    SERVO_SPEED
                ]

                self.publisher.publish(msg)

                self.last_move_time = current_time

                self.get_logger().info(
                    "Aardbei gevonden -> servo beweegt " + str(SERVO_POSITION)
                )

        #
        # Draw detections
        #
        for cx, cy, radius in detections:

            cv2.circle(
                frame,
                (cx, cy),
                radius,
                (0, 255, 0),
                2
            )

        #
        # Debug windows
        #
        cv2.imshow(
            "Strawberry Detector",
            frame
        )

        # cv2.imshow(
        #     "Red Mask",
        #     mask_red
        # )

        cv2.waitKey(1)

    # ========================================================

    def destroy_node(self):

        self.stream.stop()

        cv2.destroyAllWindows()

        super().destroy_node()


# ============================================================

def main(args=None):

    rclpy.init(args=args)

    node = StrawberryDetector()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == '__main__':
    main()