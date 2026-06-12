import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap
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


def _load_topic_mapping(package_share_dir: str) -> dict[str, str]:
    config_path = Path(package_share_dir) / "config" / "topic_mapping.yaml"
    with open(config_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"topic_mapping.yaml must contain a YAML mapping: {config_path}")
    return {str(key): value for key, value in data.items()}


def generate_launch_description():
    agt_nav_console_share = get_package_share_directory("agt_nav_console")
    mid360_demo_share = get_package_share_directory("mid360_nav_demo")
    octo_planner_share = get_package_share_directory("octo_planner")
    topic_mapping = _load_topic_mapping(agt_nav_console_share)
    workspace_root = _guess_workspace_root(
        agt_nav_console_share, mid360_demo_share, octo_planner_share
    )

    online_nav_demo_launch = os.path.join(
        mid360_demo_share, "launch", "online_nav_demo.launch.py"
    )
    obstacle_stop_demo_launch = os.path.join(
        agt_nav_console_share, "launch", "obstacle_stop_demo.launch.py"
    )
    safety_config = os.path.join(agt_nav_console_share, "config", "safety.yaml")
    default_map = os.path.join(octo_planner_share, "maps", "syswaiwei.yaml")
    default_nav2_params = os.path.join(
        octo_planner_share, "config", "nav2_mid360_params.yaml"
    )
    default_fast_livo_params = os.path.join(
        get_package_share_directory("fast_livo"), "config", "mid360_lio_relocalization.yaml"
    )
    default_icp_params = os.path.join(
        mid360_demo_share, "config", "icp_relocalizer.yaml"
    )
    default_global_map_pcd = ""
    if workspace_root is not None:
        default_global_map_pcd = str(
            workspace_root / "src" / "FAST-LIVO2-ROS2" / "Log" / "PCD" / "all_raw_points.pcd"
        )

    declare_args = [
        DeclareLaunchArgument("launch_driver", default_value="true"),
        DeclareLaunchArgument("launch_fast_livo", default_value="true"),
        DeclareLaunchArgument("launch_icp_relocalizer", default_value="true"),
        DeclareLaunchArgument("launch_rviz", default_value="true"),
        DeclareLaunchArgument("launch_chassis", default_value="true"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument("bridge_publish_rate", default_value="30.0"),
        DeclareLaunchArgument("disable_dynamic_obstacles", default_value="false"),
        DeclareLaunchArgument("local_inflation_radius", default_value=""),
        DeclareLaunchArgument("global_inflation_radius", default_value=""),
        DeclareLaunchArgument("wheel_base", default_value="0.6"),
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
        DeclareLaunchArgument("chassis_params_file", default_value=os.path.join(
            get_package_share_directory("yhs_can_control"), "params", "cfg.yaml"
        )),
        DeclareLaunchArgument("launch_obstacle_stop", default_value="true"),
        DeclareLaunchArgument("use_cloud_to_scan", default_value="true"),
        DeclareLaunchArgument("scan_topic", default_value=topic_mapping["scan_topic"]),
        DeclareLaunchArgument("nav_cmd_topic", default_value=topic_mapping["nav_cmd_topic"]),
        DeclareLaunchArgument("manual_cmd_topic", default_value=topic_mapping["manual_cmd_topic"]),
        DeclareLaunchArgument("safe_cmd_topic", default_value=topic_mapping["safe_cmd_topic"]),
        DeclareLaunchArgument("ctrl_cmd_topic", default_value=topic_mapping["ctrl_cmd_topic"]),
        DeclareLaunchArgument("io_cmd_topic", default_value=topic_mapping["io_cmd_topic"]),
        DeclareLaunchArgument(
            "obstacle_stop_topic", default_value=topic_mapping["obstacle_stop_topic"]
        ),
        DeclareLaunchArgument(
            "obstacle_distance_topic", default_value=topic_mapping["obstacle_distance_topic"]
        ),
        DeclareLaunchArgument(
            "manual_enable_topic", default_value=topic_mapping["manual_enable_topic"]
        ),
        DeclareLaunchArgument(
            "auto_enable_topic", default_value=topic_mapping["auto_enable_topic"]
        ),
        DeclareLaunchArgument("set_estop_service", default_value=topic_mapping["set_estop_service"]),
        DeclareLaunchArgument(
            "clear_estop_service", default_value=topic_mapping["clear_estop_service"]
        ),
    ]

    online_nav_demo = GroupAction([
        SetRemap(src="/cmd_vel", dst=LaunchConfiguration("nav_cmd_topic")),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(online_nav_demo_launch),
            launch_arguments={
                "launch_driver": LaunchConfiguration("launch_driver"),
                "launch_fast_livo": LaunchConfiguration("launch_fast_livo"),
                "launch_icp_relocalizer": LaunchConfiguration("launch_icp_relocalizer"),
                "launch_rviz": LaunchConfiguration("launch_rviz"),
                "launch_cmd_bridge": "false",
                "launch_chassis": "false",
                "bridge_publish_rate": LaunchConfiguration("bridge_publish_rate"),
                "disable_dynamic_obstacles": LaunchConfiguration("disable_dynamic_obstacles"),
                "local_inflation_radius": LaunchConfiguration("local_inflation_radius"),
                "global_inflation_radius": LaunchConfiguration("global_inflation_radius"),
                "use_sim_time": LaunchConfiguration("use_sim_time"),
                "map": LaunchConfiguration("map"),
                "nav2_params_file": LaunchConfiguration("nav2_params_file"),
                "fast_livo_params": LaunchConfiguration("fast_livo_params"),
                "icp_params_file": LaunchConfiguration("icp_params_file"),
                "global_map_pcd": LaunchConfiguration("global_map_pcd"),
                "cloud_topic": LaunchConfiguration("cloud_topic"),
                "global_frame": LaunchConfiguration("global_frame"),
                "odom_frame": LaunchConfiguration("odom_frame"),
                "tracking_frame": LaunchConfiguration("tracking_frame"),
            }.items(),
        ),
    ])

    safety_guard_node = Node(
        package="agt_nav_console",
        executable="safety_guard_node",
        name="safety_guard_node",
        output="screen",
        parameters=[
            safety_config,
            {
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            },
        ],
        remappings=[
            ("/agt/cmd_vel_manual", LaunchConfiguration("manual_cmd_topic")),
            ("/agt/cmd_vel_nav", LaunchConfiguration("nav_cmd_topic")),
            ("/agt/obstacle_stop", LaunchConfiguration("obstacle_stop_topic")),
            ("/agt/manual_enable", LaunchConfiguration("manual_enable_topic")),
            ("/agt/auto_enable", LaunchConfiguration("auto_enable_topic")),
            ("/cmd_vel_safe", LaunchConfiguration("safe_cmd_topic")),
            ("/agt/set_estop", LaunchConfiguration("set_estop_service")),
            ("/agt/clear_estop", LaunchConfiguration("clear_estop_service")),
        ],
    )

    obstacle_stop = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(obstacle_stop_demo_launch),
        condition=IfCondition(LaunchConfiguration("launch_obstacle_stop")),
        launch_arguments={
            "use_cloud_to_scan": LaunchConfiguration("use_cloud_to_scan"),
            "cloud_topic": LaunchConfiguration("cloud_topic"),
            "scan_topic": LaunchConfiguration("scan_topic"),
            "target_frame": LaunchConfiguration("tracking_frame"),
            "obstacle_stop_topic": LaunchConfiguration("obstacle_stop_topic"),
            "obstacle_distance_topic": LaunchConfiguration("obstacle_distance_topic"),
        }.items(),
    )

    safe_cmd_bridge_node = Node(
        package="octo_planner",
        executable="cmd_vel_to_ctrl_cmd_bridge",
        name="cmd_vel_to_ctrl_cmd_bridge_safe",
        output="screen",
        parameters=[
            {
                "cmd_vel_topic": LaunchConfiguration("safe_cmd_topic"),
                "ctrl_cmd_topic": LaunchConfiguration("ctrl_cmd_topic"),
                "io_cmd_topic": LaunchConfiguration("io_cmd_topic"),
                "wheel_base": LaunchConfiguration("wheel_base"),
                "publish_rate": LaunchConfiguration("bridge_publish_rate"),
                "forward_gear": 4,
                "reverse_gear": 2,
                "neutral_gear": 3,
                "publish_io_cmd": True,
                "io_cmd_enable": True,
                "io_cmd_dis_charge": False,
            }
        ],
    )

    chassis_node = Node(
        condition=IfCondition(LaunchConfiguration("launch_chassis")),
        package="yhs_can_control",
        executable="yhs_can_control_node",
        name="yhs_can_control_node",
        output="screen",
        parameters=[LaunchConfiguration("chassis_params_file")],
    )

    return LaunchDescription(
        declare_args + [
            online_nav_demo,
            safety_guard_node,
            obstacle_stop,
            safe_cmd_bridge_node,
            chassis_node,
        ]
    )
