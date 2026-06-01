from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="mid360_nav_demo",
                executable="octomap_tuning_gui.py",
                name="octomap_tuning_gui",
                output="screen",
            ),
        ]
    )
