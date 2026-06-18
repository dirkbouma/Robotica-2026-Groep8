from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory("aardbeien_detectie"),
        "config",
        "detectie_params.yaml",
    )

    return LaunchDescription([
        Node(
            package="aardbeien_detectie",
            executable="detectie_node",
            name="aardbeien_detectie",
            output="screen",
            parameters=[config],
        )
    ])