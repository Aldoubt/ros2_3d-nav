import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    octo_planner_share = get_package_share_directory("octo_planner")
    nav2_bringup_share = get_package_share_directory("nav2_bringup")

    default_map = os.path.join(octo_planner_share, "maps", "syswaiwei.yaml")
    default_params = os.path.join(octo_planner_share, "config", "nav2_mid360_params.yaml")
    default_rviz = os.path.join(nav2_bringup_share, "rviz", "nav2_default_view.rviz")
    nav2_navigation_launch = os.path.join(nav2_bringup_share, "launch", "navigation_launch.py")

    map_yaml_arg = DeclareLaunchArgument(
        "map",
        default_value=default_map,
        description="2D occupancy grid yaml used by nav2_map_server.",
    )
    params_file_arg = DeclareLaunchArgument(
        "params_file",
        default_value=default_params,
        description="Nav2 parameter file tuned for MID360 + FAST-LIVO2 + lidar_localization.",
    )
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="false",
        description="Use simulated time.",
    )
    autostart_arg = DeclareLaunchArgument(
        "autostart",
        default_value="true",
        description="Autostart map_server and Nav2 lifecycle nodes.",
    )
    use_composition_arg = DeclareLaunchArgument(
        "use_composition",
        default_value="False",
        description="Use Nav2 composition container mode.",
    )
    use_respawn_arg = DeclareLaunchArgument(
        "use_respawn",
        default_value="False",
        description="Respawn Nav2 nodes when they crash.",
    )
    log_level_arg = DeclareLaunchArgument(
        "log_level",
        default_value="info",
        description="Log level for Nav2 nodes.",
    )
    launch_rviz_arg = DeclareLaunchArgument(
        "launch_rviz",
        default_value="true",
        description="Launch RViz with the default Nav2 profile.",
    )
    rviz_config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value=default_rviz,
        description="RViz config file.",
    )
    launch_cmd_bridge_arg = DeclareLaunchArgument(
        "launch_cmd_bridge",
        default_value="false",
        description="Launch /cmd_vel to /ctrl_cmd bridge for MK-mini chassis.",
    )
    launch_chassis_arg = DeclareLaunchArgument(
        "launch_chassis",
        default_value="false",
        description="Launch yhs_can_control for the physical chassis.",
    )
    chassis_params_file_arg = DeclareLaunchArgument(
        "chassis_params_file",
        default_value=os.path.join(
            get_package_share_directory("yhs_can_control"), "params", "cfg.yaml"
        ),
        description="Parameter file for yhs_can_control.",
    )
    wheel_base_arg = DeclareLaunchArgument(
        "wheel_base",
        default_value="0.6",
        description="Wheel base used by cmd_vel_to_ctrl_cmd_bridge.",
    )
    bridge_publish_rate_arg = DeclareLaunchArgument(
        "bridge_publish_rate",
        default_value="30.0",
        description="Publish rate from /cmd_vel to /ctrl_cmd for the physical chassis.",
    )

    map_server_node = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[
            LaunchConfiguration("params_file"),
            {
                "use_sim_time": LaunchConfiguration("use_sim_time"),
                "yaml_filename": LaunchConfiguration("map"),
            },
        ],
        arguments=["--ros-args", "--log-level", LaunchConfiguration("log_level")],
    )

    lifecycle_manager_localization = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_localization",
        output="screen",
        parameters=[
            {
                "use_sim_time": LaunchConfiguration("use_sim_time"),
                "autostart": LaunchConfiguration("autostart"),
                "node_names": ["map_server"],
            }
        ],
        arguments=["--ros-args", "--log-level", LaunchConfiguration("log_level")],
    )

    nav2_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav2_navigation_launch),
        launch_arguments={
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "autostart": LaunchConfiguration("autostart"),
            "params_file": LaunchConfiguration("params_file"),
            "use_composition": LaunchConfiguration("use_composition"),
            "use_respawn": LaunchConfiguration("use_respawn"),
            "container_name": "nav2_container",
            "log_level": LaunchConfiguration("log_level"),
        }.items(),
    )

    rviz_node = Node(
        condition=IfCondition(LaunchConfiguration("launch_rviz")),
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", LaunchConfiguration("rviz_config")],
        output="screen",
    )

    cmd_bridge_node = Node(
        condition=IfCondition(LaunchConfiguration("launch_cmd_bridge")),
        package="octo_planner",
        executable="cmd_vel_to_ctrl_cmd_bridge",
        name="cmd_vel_to_ctrl_cmd_bridge",
        output="screen",
        parameters=[
            {
                "cmd_vel_topic": "/cmd_vel",
                "ctrl_cmd_topic": "/ctrl_cmd",
                "io_cmd_topic": "/io_cmd",
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
        [
            map_yaml_arg,
            params_file_arg,
            use_sim_time_arg,
            autostart_arg,
            use_composition_arg,
            use_respawn_arg,
            log_level_arg,
            launch_rviz_arg,
            rviz_config_arg,
            launch_cmd_bridge_arg,
            launch_chassis_arg,
            chassis_params_file_arg,
            wheel_base_arg,
            bridge_publish_rate_arg,
            map_server_node,
            lifecycle_manager_localization,
            nav2_navigation,
            rviz_node,
            cmd_bridge_node,
            chassis_node,
        ]
    )
