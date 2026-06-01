import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pb_rm_share = get_package_share_directory("pb_rm_simulation")
    mid360_demo_share = get_package_share_directory("mid360_nav_demo")
    fast_livo_share = get_package_share_directory("fast_livo")

    simulation_launch = os.path.join(pb_rm_share, "launch", "rm_simulation.launch.py")
    robot_xacro = os.path.join(pb_rm_share, "urdf", "simulation_waking_robot.xacro")
    fast_livo_launch = os.path.join(
        fast_livo_share, "launch", "mapping_mid360_lio.launch.py"
    )
    default_fast_livo_params = os.path.join(
        mid360_demo_share, "config", "mid360_lio_sim_relocalization.yaml"
    )
    default_icp_params = os.path.join(
        mid360_demo_share, "config", "icp_relocalizer.yaml"
    )
    default_rviz = os.path.join(
        mid360_demo_share, "rviz", "mid360_sim_relocalization.rviz"
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument("launch_sim", default_value="true"),
            DeclareLaunchArgument("launch_fast_livo", default_value="true"),
            DeclareLaunchArgument("launch_icp", default_value="true"),
            DeclareLaunchArgument("launch_map_server", default_value="true"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            DeclareLaunchArgument("launch_drive_gui", default_value="true"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("world", default_value="RMUC"),
            DeclareLaunchArgument("fast_livo_params", default_value=default_fast_livo_params),
            DeclareLaunchArgument("icp_params_file", default_value=default_icp_params),
            DeclareLaunchArgument(
                "map",
                default_value="/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/sim_test.yaml",
            ),
            DeclareLaunchArgument(
                "global_map_pcd",
                default_value="/home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/Log/PCD/all_raw_points.pcd",
            ),
            DeclareLaunchArgument("cloud_topic", default_value="/cloud_registered"),
            DeclareLaunchArgument("global_frame", default_value="map"),
            DeclareLaunchArgument("odom_frame", default_value="odom"),
            DeclareLaunchArgument("tracking_frame", default_value="livox_frame"),
            DeclareLaunchArgument("lidar_xyz", default_value="0.12 0.0 0.175"),
            DeclareLaunchArgument("lidar_rpy", default_value="0 0 0"),
            DeclareLaunchArgument("rviz_config", default_value=default_rviz),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(simulation_launch),
                condition=IfCondition(LaunchConfiguration("launch_sim")),
                launch_arguments={
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                    "world": LaunchConfiguration("world"),
                    "rviz": "false",
                    "robot_description": Command(
                        [
                            "xacro ",
                            robot_xacro,
                            " xyz:='",
                            LaunchConfiguration("lidar_xyz"),
                            "' rpy:='",
                            LaunchConfiguration("lidar_rpy"),
                            "'",
                        ]
                    ),
                }.items(),
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
                condition=IfCondition(LaunchConfiguration("launch_map_server")),
                package="nav2_map_server",
                executable="map_server",
                name="map_server",
                output="screen",
                parameters=[
                    {
                        "yaml_filename": LaunchConfiguration("map"),
                        "use_sim_time": LaunchConfiguration("use_sim_time"),
                    }
                ],
            ),
            Node(
                condition=IfCondition(LaunchConfiguration("launch_map_server")),
                package="nav2_lifecycle_manager",
                executable="lifecycle_manager",
                name="lifecycle_manager_map_server",
                output="screen",
                parameters=[
                    {
                        "use_sim_time": LaunchConfiguration("use_sim_time"),
                        "autostart": True,
                        "node_names": ["map_server"],
                    }
                ],
            ),
            Node(
                condition=IfCondition(LaunchConfiguration("launch_icp")),
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
            Node(
                condition=IfCondition(LaunchConfiguration("launch_rviz")),
                package="rviz2",
                executable="rviz2",
                name="rviz2",
                arguments=["-d", LaunchConfiguration("rviz_config")],
                output="screen",
            ),
            Node(
                condition=IfCondition(LaunchConfiguration("launch_drive_gui")),
                package="mid360_nav_demo",
                executable="sim_drive_gui.py",
                name="sim_drive_gui",
                output="screen",
            ),
        ]
    )
