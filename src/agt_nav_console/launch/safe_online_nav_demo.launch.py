import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetRemap


def generate_launch_description():
    agt_nav_console_share = get_package_share_directory("agt_nav_console")
    mid360_demo_share = get_package_share_directory("mid360_nav_demo")
    octo_planner_share = get_package_share_directory("octo_planner")

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

    declare_args = [
        DeclareLaunchArgument("launch_driver", default_value="true"),
        DeclareLaunchArgument("launch_fast_livo", default_value="true"),
        DeclareLaunchArgument("launch_icp_relocalizer", default_value="true"),
        DeclareLaunchArgument("launch_rviz", default_value="true"),
        DeclareLaunchArgument("launch_chassis", default_value="true"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument("bridge_publish_rate", default_value="30.0"),
        DeclareLaunchArgument("wheel_base", default_value="0.6"),
        DeclareLaunchArgument("map", default_value=default_map),
        DeclareLaunchArgument("nav2_params_file", default_value=default_nav2_params),
        DeclareLaunchArgument("fast_livo_params", default_value=default_fast_livo_params),
        DeclareLaunchArgument("icp_params_file", default_value=default_icp_params),
        DeclareLaunchArgument(
            "global_map_pcd",
            default_value="/home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/Log/PCD/all_downsampled_points.pcd",
        ),
        DeclareLaunchArgument("cloud_topic", default_value="/cloud_registered"),
        DeclareLaunchArgument("global_frame", default_value="map"),
        DeclareLaunchArgument("odom_frame", default_value="odom"),
        DeclareLaunchArgument("tracking_frame", default_value="livox_frame"),
        DeclareLaunchArgument("chassis_params_file", default_value=os.path.join(
            get_package_share_directory("yhs_can_control"), "params", "cfg.yaml"
        )),
        DeclareLaunchArgument("launch_obstacle_stop", default_value="true"),
        DeclareLaunchArgument("use_cloud_to_scan", default_value="true"),
        DeclareLaunchArgument("scan_topic", default_value="/scan"),
    ]

    online_nav_demo = GroupAction([
        SetRemap(src="/cmd_vel", dst="/agt/cmd_vel_nav"),
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
    )

    obstacle_stop = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(obstacle_stop_demo_launch),
        condition=IfCondition(LaunchConfiguration("launch_obstacle_stop")),
        launch_arguments={
            "use_cloud_to_scan": LaunchConfiguration("use_cloud_to_scan"),
            "cloud_topic": LaunchConfiguration("cloud_topic"),
            "scan_topic": LaunchConfiguration("scan_topic"),
            "target_frame": LaunchConfiguration("tracking_frame"),
        }.items(),
    )

    safe_cmd_bridge_node = Node(
        package="octo_planner",
        executable="cmd_vel_to_ctrl_cmd_bridge",
        name="cmd_vel_to_ctrl_cmd_bridge_safe",
        output="screen",
        parameters=[
            {
                "cmd_vel_topic": "/cmd_vel_safe",
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
        declare_args + [
            online_nav_demo,
            safety_guard_node,
            obstacle_stop,
            safe_cmd_bridge_node,
            chassis_node,
        ]
    )
