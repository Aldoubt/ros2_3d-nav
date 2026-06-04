from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "map_topic",
                default_value="/projected_map",
                description="OccupancyGrid topic to save.",
            ),
            DeclareLaunchArgument(
                "map_prefix",
                default_value="/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/mid360_map",
                description="Output map path without extension.",
            ),
            DeclareLaunchArgument(
                "image_format",
                default_value="pgm",
                description="Output image format used by nav2_map_server.",
            ),
            DeclareLaunchArgument(
                "map_subscribe_transient_local",
                default_value="true",
                description=(
                    "Use true when /projected_map is published with transient local "
                    "durability so late subscribers can still receive the latest map."
                ),
            ),
            DeclareLaunchArgument(
                "save_map_timeout",
                default_value="20.0",
                description="Seconds to wait for a map message before failing.",
            ),
            ExecuteProcess(
                cmd=[
                    "ros2",
                    "run",
                    "nav2_map_server",
                    "map_saver_cli",
                    "-t",
                    LaunchConfiguration("map_topic"),
                    "-f",
                    LaunchConfiguration("map_prefix"),
                    "--fmt",
                    LaunchConfiguration("image_format"),
                    "--ros-args",
                    "-p",
                    [
                        "map_subscribe_transient_local:=",
                        LaunchConfiguration("map_subscribe_transient_local"),
                    ],
                    "-p",
                    ["save_map_timeout:=", LaunchConfiguration("save_map_timeout")],
                ],
                output="screen",
            ),
        ]
    )
