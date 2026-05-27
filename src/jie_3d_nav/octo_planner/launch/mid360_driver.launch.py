import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    octo_planner_share = get_package_share_directory("octo_planner")
    default_config_path = os.path.join(
        octo_planner_share, "config", "mid360_livox_config.json"
    )

    config_path_arg = DeclareLaunchArgument(
        "config_path",
        default_value=default_config_path,
        description="Path to the Livox MID360 JSON configuration file.",
    )
    frame_id_arg = DeclareLaunchArgument(
        "frame_id",
        default_value="livox_frame",
        description="Frame id published by livox_ros_driver2.",
    )
    publish_freq_arg = DeclareLaunchArgument(
        "publish_freq",
        default_value="10.0",
        description="Point cloud publish frequency used by livox_ros_driver2.",
    )
    xfer_format_arg = DeclareLaunchArgument(
        "xfer_format",
        default_value="1",
        description=(
            "Point cloud output format. Use 1 for Livox customized point cloud, "
            "which matches the current FAST-LIVO2 mid360 configuration."
        ),
    )
    multi_topic_arg = DeclareLaunchArgument(
        "multi_topic",
        default_value="0",
        description="Whether each Livox device publishes to an independent topic.",
    )

    livox_driver_node = Node(
        package="livox_ros_driver2",
        executable="livox_ros_driver2_node",
        name="livox_lidar_publisher",
        output="screen",
        parameters=[
            {
                "xfer_format": ParameterValue(
                    LaunchConfiguration("xfer_format"), value_type=int
                ),
                "multi_topic": ParameterValue(
                    LaunchConfiguration("multi_topic"), value_type=int
                ),
                "data_src": 0,
                "publish_freq": ParameterValue(
                    LaunchConfiguration("publish_freq"), value_type=float
                ),
                "output_data_type": 0,
                "frame_id": LaunchConfiguration("frame_id"),
                "lvx_file_path": "/home/livox/livox_test.lvx",
                "user_config_path": LaunchConfiguration("config_path"),
                "cmdline_input_bd_code": "",
            }
        ],
    )

    return LaunchDescription(
        [
            config_path_arg,
            frame_id_arg,
            publish_freq_arg,
            xfer_format_arg,
            multi_topic_arg,
            livox_driver_node,
        ]
    )
