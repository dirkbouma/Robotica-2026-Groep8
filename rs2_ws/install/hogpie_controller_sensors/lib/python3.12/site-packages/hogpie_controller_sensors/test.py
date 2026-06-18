#!/usr/bin/env python3

from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder

moveit_config = (
    MoveItConfigsBuilder(
        "hogpie_arm",
        package_name="hogpie_arm_moveit_config"
    ).to_moveit_configs()
)

print("Creating MoveItPy...")

moveit = MoveItPy(
    node_name="moveit_pose_commander",
    config_dict=moveit_config.to_dict()
)

print("SUCCESS")