#!/usr/bin/python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory("fast_livo")
    runtime_ld_library_path = (
        "/usr/lib/x86_64-linux-gnu:" + os.environ.get("LD_LIBRARY_PATH", "")
    )
    default_config = os.path.join(package_share, "config", "mid360_lio_only.yaml")
    default_rviz = os.path.join(package_share, "rviz_cfg", "fast_livo2.rviz")

    params_file_arg = DeclareLaunchArgument(
        "params_file",
        default_value=default_config,
        description="FAST-LIVO2 parameter file for MID360 LiDAR+IMU odometry.",
    )
    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz",
        default_value="false",
        description="Whether to launch RViz together with FAST-LIVO2.",
    )
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="false",
        description="Whether FAST-LIVO2 should use simulated time.",
    )

    return LaunchDescription(
        [
            params_file_arg,
            use_rviz_arg,
            use_sim_time_arg,
            Node(
                package="fast_livo",
                executable="fastlivo_mapping",
                output="screen",
                additional_env={"LD_LIBRARY_PATH": runtime_ld_library_path},
                parameters=[
                    LaunchConfiguration("params_file"),
                    {"use_sim_time": LaunchConfiguration("use_sim_time")},
                ],
            ),
            Node(
                condition=IfCondition(LaunchConfiguration("use_rviz")),
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                arguments=["-d", default_rviz],
                output="screen",
            ),
        ]
    )
