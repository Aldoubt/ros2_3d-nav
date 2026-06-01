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
    robot_xacro = os.path.join(
        pb_rm_share, "urdf", "simulation_waking_robot.xacro"
    )
    fast_livo_launch = os.path.join(
        fast_livo_share, "launch", "mapping_mid360_lio.launch.py"
    )
    octomap_launch = os.path.join(
        mid360_demo_share, "launch", "octomap_mapping.launch.py"
    )
    default_fast_livo_params = os.path.join(
        mid360_demo_share, "config", "mid360_lio_sim_custom.yaml"
    )
    default_rviz = os.path.join(
        mid360_demo_share, "rviz", "mid360_sim_mapping.rviz"
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("launch_sim", default_value="true"),
            DeclareLaunchArgument("launch_fast_livo", default_value="true"),
            DeclareLaunchArgument("launch_octomap", default_value="true"),
            DeclareLaunchArgument("launch_rviz", default_value="false"),
            DeclareLaunchArgument("launch_drive_gui", default_value="false"),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            DeclareLaunchArgument("world", default_value="RMUC"),
            DeclareLaunchArgument("fast_livo_params", default_value=default_fast_livo_params),
            DeclareLaunchArgument("cloud_topic", default_value="/cloud_registered"),
            DeclareLaunchArgument("projected_map_topic", default_value="/projected_map"),
            DeclareLaunchArgument("octomap_frame", default_value="odom"),
            DeclareLaunchArgument("base_frame_id", default_value="livox_frame"),
            DeclareLaunchArgument("lidar_xyz", default_value="0.12 0.0 0.175"),
            DeclareLaunchArgument("lidar_rpy", default_value="0 0 0"),
            DeclareLaunchArgument("pointcloud_min_z", default_value="0.20"),
            DeclareLaunchArgument("pointcloud_max_z", default_value="1.20"),
            DeclareLaunchArgument("occupancy_min_z", default_value="0.20"),
            DeclareLaunchArgument("occupancy_max_z", default_value="1.20"),
            DeclareLaunchArgument("filter_speckles", default_value="true"),
            DeclareLaunchArgument("filter_ground", default_value="false"),
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
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(octomap_launch),
                condition=IfCondition(LaunchConfiguration("launch_octomap")),
                launch_arguments={
                    "cloud_topic": LaunchConfiguration("cloud_topic"),
                    "projected_map_topic": LaunchConfiguration("projected_map_topic"),
                    "frame_id": LaunchConfiguration("octomap_frame"),
                    "base_frame_id": LaunchConfiguration("base_frame_id"),
                    "use_sim_time": LaunchConfiguration("use_sim_time"),
                    "pointcloud_min_z": LaunchConfiguration("pointcloud_min_z"),
                    "pointcloud_max_z": LaunchConfiguration("pointcloud_max_z"),
                    "occupancy_min_z": LaunchConfiguration("occupancy_min_z"),
                    "occupancy_max_z": LaunchConfiguration("occupancy_max_z"),
                    "filter_speckles": LaunchConfiguration("filter_speckles"),
                    "filter_ground": LaunchConfiguration("filter_ground"),
                }.items(),
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
