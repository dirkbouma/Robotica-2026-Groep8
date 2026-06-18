#!/usr/bin/env python3

from threading import Thread

import rclpy

from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup

from pymoveit2 import MoveIt2


def main():

    rclpy.init()

    node = Node("workspace_scan")

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

    reachable = []

    x_values = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    y_values = [-0.20, -0.10, 0.00, 0.10, 0.20]
    z_values = [0.05, 0.10, 0.15, 0.20, 0.25]

    total = (
        len(x_values)
        * len(y_values)
        * len(z_values)
    )

    count = 0

    node.get_logger().info(
        f"Testing {total} positions..."
    )

    for x in x_values:
        for y in y_values:
            for z in z_values:

                count += 1

                ik_result = moveit2.compute_ik(
                    position=(x, y, z),
                    quat_xyzw=(0.0, 0.0, 0.0, 1.0),
                    ik_link_name="tool_link",
                )

                if ik_result is not None:

                    reachable.append(
                        (x, y, z)
                    )

                    print(
                        f"REACHABLE: "
                        f"x={x:.2f} "
                        f"y={y:.2f} "
                        f"z={z:.2f}"
                    )

                if count % 500 == 0:
                    node.get_logger().info(
                        f"{count}/{total}"
                    )

    print()
    print("========== SUMMARY ==========")
    print(f"Reachable points: {len(reachable)}")

    if reachable:

        min_x = min(p[0] for p in reachable)
        max_x = max(p[0] for p in reachable)

        min_y = min(p[1] for p in reachable)
        max_y = max(p[1] for p in reachable)

        min_z = min(p[2] for p in reachable)
        max_z = max(p[2] for p in reachable)

        print()
        print("Reachable bounds:")
        print(f"X: {min_x:.2f} -> {max_x:.2f}")
        print(f"Y: {min_y:.2f} -> {max_y:.2f}")
        print(f"Z: {min_z:.2f} -> {max_z:.2f}")

    rclpy.shutdown()
    executor_thread.join()


if __name__ == "__main__":
    main()