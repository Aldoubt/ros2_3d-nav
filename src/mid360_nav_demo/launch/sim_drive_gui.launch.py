from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package="mid360_nav_demo",
                executable="sim_drive_gui.py",
                name="sim_drive_gui",
                output="screen",
            ),
        ]
    )
