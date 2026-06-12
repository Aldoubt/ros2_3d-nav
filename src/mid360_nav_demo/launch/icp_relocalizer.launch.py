import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _guess_workspace_root(share_dir: str) -> Path | None:
    env_root = os.environ.get("ROS2_WS_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    share_path = Path(share_dir).resolve()
    if "install" in share_path.parts:
        install_index = share_path.parts.index("install")
        return Path(*share_path.parts[:install_index])
    return None


def generate_launch_description():
    mid360_demo_share = get_package_share_directory("mid360_nav_demo")
    workspace_root = _guess_workspace_root(mid360_demo_share)
    default_global_map_pcd = ""
    if workspace_root is not None:
        default_global_map_pcd = str(
            workspace_root / "src" / "FAST-LIVO2-ROS2" / "Log" / "PCD" / "all_raw_points.pcd"
        )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "icp_params_file",
                default_value=os.path.join(mid360_demo_share, "config", "icp_relocalizer.yaml"),
            ),
            DeclareLaunchArgument(
                "global_map_pcd",
                default_value=default_global_map_pcd,
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
