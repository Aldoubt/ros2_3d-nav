import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share_dir = get_package_share_directory("agt_nav_console")
    obstacle_config = os.path.join(package_share_dir, "config", "obstacle_stop.yaml")

    use_cloud_to_scan_arg = DeclareLaunchArgument(
        "use_cloud_to_scan",
        default_value="true",
        description="Convert /cloud_registered to /scan for obstacle stop when no LaserScan is available.",
    )
    cloud_topic_arg = DeclareLaunchArgument(
        "cloud_topic",
        default_value="/cloud_registered",
        description="PointCloud2 topic used by pointcloud_to_laserscan.",
    )
    scan_topic_arg = DeclareLaunchArgument(
        "scan_topic",
        default_value="/scan",
        description="LaserScan topic consumed by obstacle_stop_node.",
    )
    target_frame_arg = DeclareLaunchArgument(
        "target_frame",
        default_value="livox_frame",
        description="Target frame for pointcloud_to_laserscan.",
    )

    cloud_to_scan_node = Node(
        condition=IfCondition(LaunchConfiguration("use_cloud_to_scan")),
        package="pointcloud_to_laserscan",
        executable="pointcloud_to_laserscan_node",
        name="pointcloud_to_laserscan",
        output="screen",
        remappings=[
            ("cloud_in", LaunchConfiguration("cloud_topic")),
            ("scan", LaunchConfiguration("scan_topic")),
        ],
        parameters=[{
            "target_frame": LaunchConfiguration("target_frame"),
            "transform_tolerance": 0.05,
            "min_height": -0.3,
            "max_height": 1.2,
            "angle_min": -1.5708,
            "angle_max": 1.5708,
            "angle_increment": 0.0087,
            "scan_time": 0.1,
            "range_min": 0.15,
            "range_max": 15.0,
            "use_inf": True,
            "inf_epsilon": 1.0,
        }],
    )

    obstacle_stop_node = Node(
        package="agt_nav_console",
        executable="obstacle_stop_node",
        name="obstacle_stop_node",
        output="screen",
        parameters=[obstacle_config],
        remappings=[
            ("/scan", LaunchConfiguration("scan_topic")),
        ],
    )

    return LaunchDescription([
        use_cloud_to_scan_arg,
        cloud_topic_arg,
        scan_topic_arg,
        target_frame_arg,
        cloud_to_scan_node,
        obstacle_stop_node,
    ])
