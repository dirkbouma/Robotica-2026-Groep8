from launch import LaunchDescription

from launch_ros.actions import Node


def generate_launch_description():

    return LaunchDescription([
        Node(
            package="hogpie_controller_sensors",
            executable="moveit_commander",
            output="screen",
        )
    ])