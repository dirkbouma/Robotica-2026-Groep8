#!/usr/bin/env python3

import rclpy

from rclpy.node import Node

from moveit_msgs.srv import GetPositionIK
from geometry_msgs.msg import PoseStamped


def main():
    rclpy.init()

    node = Node("ik_test")

    client = node.create_client(
        GetPositionIK,
        "/compute_ik"
    )

    client.wait_for_service()

    req = GetPositionIK.Request()

    req.ik_request.group_name = "arm"
    req.ik_request.ik_link_name = "tool_link"

    req.ik_request.pose_stamped = PoseStamped()

    req.ik_request.pose_stamped.header.frame_id = "base_link"

    req.ik_request.pose_stamped.pose.position.x = 0.231
    req.ik_request.pose_stamped.pose.position.y = -0.041
    req.ik_request.pose_stamped.pose.position.z = 0.226

    req.ik_request.pose_stamped.pose.orientation.x = 0.0
    req.ik_request.pose_stamped.pose.orientation.y = 0.0
    req.ik_request.pose_stamped.pose.orientation.z = 0.0
    req.ik_request.pose_stamped.pose.orientation.w = 1.0

    future = client.call_async(req)

    rclpy.spin_until_future_complete(
        node,
        future
    )

    result = future.result()

    print()
    print("ERROR CODE:")
    print(result.error_code.val)

    print()
    print("MESSAGE:")
    print(result.error_code.message)

    print()
    print("JOINTS:")
    print(result.solution.joint_state.name)
    print(result.solution.joint_state.position)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()