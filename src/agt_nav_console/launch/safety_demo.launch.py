from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

import os


def generate_launch_description():
    package_share_dir = get_package_share_directory("agt_nav_console")
    safety_config = os.path.join(package_share_dir, "config", "safety.yaml")

    safety_guard_node = Node(
        package="agt_nav_console",
        executable="safety_guard_node",
        name="safety_guard_node",
        output="screen",
        parameters=[safety_config],
    )

    return LaunchDescription([
        safety_guard_node,
    ])
