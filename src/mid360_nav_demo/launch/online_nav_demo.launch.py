import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml


def _guess_workspace_root(*share_dirs: str) -> Path | None:
    env_root = os.environ.get("ROS2_WS_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    for share_dir in share_dirs:
        share_path = Path(share_dir).resolve()
        if "install" in share_path.parts:
            install_index = share_path.parts.index("install")
            return Path(*share_path.parts[:install_index])
    return None


def _load_topic_mapping() -> dict[str, str]:
    agt_nav_console_share = get_package_share_directory("agt_nav_console")
    config_path = Path(agt_nav_console_share) / "config" / "topic_mapping.yaml"
    with open(config_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"topic_mapping.yaml must contain a YAML mapping: {config_path}")
    return {str(key): value for key, value in data.items()}


def generate_launch_description():
    octo_planner_share = get_package_share_directory("octo_planner")
    fast_livo_share = get_package_share_directory("fast_livo")
    mid360_demo_share = get_package_share_directory("mid360_nav_demo")
    topic_mapping = _load_topic_mapping()
    workspace_root = _guess_workspace_root(
        octo_planner_share, fast_livo_share, mid360_demo_share
    )

    mid360_driver_launch = os.path.join(
        octo_planner_share, "launch", "mid360_driver.launch.py"
    )
    fast_livo_launch = os.path.join(
        fast_livo_share, "launch", "mapping_mid360_lio.launch.py"
    )
    nav2_mid360_launch = os.path.join(
        octo_planner_share, "launch", "nav2_mid360.launch.py"
    )
    default_fast_livo_params = os.path.join(
        fast_livo_share, "config", "mid360_lio_relocalization.yaml"
    )
    default_nav2_params = os.path.join(
        octo_planner_share, "config", "nav2_mid360_params.yaml"
    )
    default_map = os.path.join(octo_planner_share, "maps", "syswaiwei.yaml")
    default_icp_params = os.path.join(
        mid360_demo_share, "config", "icp_relocalizer.yaml"
    )
    default_global_map_pcd = ""
    if workspace_root is not None:
        default_global_map_pcd = str(
            workspace_root
            / "src"
            / "FAST-LIVO2-ROS2"
            / "Log"
            / "PCD"
            / "all_downsampled_points.pcd"
        )

    return LaunchDescription(
        [
            DeclareLaunchArgument("launch_driver", default_value="true"),
            DeclareLaunchArgument("launch_fast_livo", default_value="true"),
            DeclareLaunchArgument("launch_icp_relocalizer", default_value="true"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            DeclareLaunchArgument("launch_cmd_bridge", default_value="false"),
            DeclareLaunchArgument("launch_chassis", default_value="false"),
            DeclareLaunchArgument("bridge_publish_rate", default_value="30.0"),
            DeclareLaunchArgument("disable_dynamic_obstacles", default_value="false"),
            DeclareLaunchArgument("local_inflation_radius", default_value=""),
            DeclareLaunchArgument("global_inflation_radius", default_value=""),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument("map", default_value=default_map),
            DeclareLaunchArgument("nav2_params_file", default_value=default_nav2_params),
            DeclareLaunchArgument("fast_livo_params", default_value=default_fast_livo_params),
            DeclareLaunchArgument("icp_params_file", default_value=default_icp_params),
            DeclareLaunchArgument(
                "global_map_pcd",
                default_value=default_global_map_pcd,
            ),
            DeclareLaunchArgument("cloud_topic", default_value=topic_mapping["cloud_topic"]),
            DeclareLaunchArgument("global_frame", default_value=topic_mapping["global_frame_id"]),
            DeclareLaunchArgument("odom_frame", default_value=topic_mapping["odom_frame_id"]),
            DeclareLaunchArgument("tracking_frame", default_value=topic_mapping["tracking_frame_id"]),
            DeclareLaunchArgument("cmd_vel_topic", default_value="/cmd_vel"),
            DeclareLaunchArgument("ctrl_cmd_topic", default_value=topic_mapping["ctrl_cmd_topic"]),
            DeclareLaunchArgument("io_cmd_topic", default_value=topic_mapping["io_cmd_topic"]),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(mid360_driver_launch),
                condition=IfCondition(LaunchConfiguration("launch_driver")),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(fast_livo_launch),
                condition=IfCondition(LaunchConfiguration("launch_fast_livo")),
                launch_arguments={
                    "params_file": LaunchConfiguration("fast_livo_params"),
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                    "use_rviz": "false",
                }.items(),
            ),
            Node(
                condition=IfCondition(LaunchConfiguration("launch_icp_relocalizer")),
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
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(nav2_mid360_launch),
                launch_arguments={
                    "map": LaunchConfiguration("map"),
                    "params_file": LaunchConfiguration("nav2_params_file"),
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                    "launch_rviz": LaunchConfiguration("launch_rviz"),
                    "launch_cmd_bridge": LaunchConfiguration("launch_cmd_bridge"),
                    "launch_chassis": LaunchConfiguration("launch_chassis"),
                    "bridge_publish_rate": LaunchConfiguration("bridge_publish_rate"),
                    "cmd_vel_topic": LaunchConfiguration("cmd_vel_topic"),
                    "ctrl_cmd_topic": LaunchConfiguration("ctrl_cmd_topic"),
                    "io_cmd_topic": LaunchConfiguration("io_cmd_topic"),
                    "disable_dynamic_obstacles": LaunchConfiguration("disable_dynamic_obstacles"),
                    "local_inflation_radius": LaunchConfiguration("local_inflation_radius"),
                    "global_inflation_radius": LaunchConfiguration("global_inflation_radius"),
                }.items(),
            ),
        ]
    )
