from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "icp_params_file",
                default_value="/home/yangxuan/ros2_ws/src/install/mid360_nav_demo/share/mid360_nav_demo/config/icp_relocalizer.yaml",
            ),
            DeclareLaunchArgument(
                "global_map_pcd",
                default_value="/home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/Log/PCD/all_raw_points.pcd",
            ),
            DeclareLaunchArgument("cloud_topic", default_value="/cloud_registered"),
            DeclareLaunchArgument("global_frame", default_value="map"),
            DeclareLaunchArgument("odom_frame", default_value="odom"),
            DeclareLaunchArgument("tracking_frame", default_value="livox_frame"),
            Node(
                package="mid360_nav_demo",
                executable="icp_relocalizer_node",
                name="icp_relocalizer_node",
                output="screen",
                additional_env={
                    "LD_PRELOAD": "/lib/x86_64-linux-gnu/libusb-1.0.so.0",
                },
                parameters=[
                    LaunchConfiguration("icp_params_file"),
                    {
                        "global_map_pcd": LaunchConfiguration("global_map_pcd"),
                        "cloud_topic": LaunchConfiguration("cloud_topic"),
                        "global_frame": LaunchConfiguration("global_frame"),
                        "odom_frame": LaunchConfiguration("odom_frame"),
                        "tracking_frame": LaunchConfiguration("tracking_frame"),
                    },
                ],
            ),
        ]
    )
