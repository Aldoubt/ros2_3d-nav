from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("cloud_topic", default_value="/cloud_registered"),
            DeclareLaunchArgument("projected_map_topic", default_value="/projected_map"),
            DeclareLaunchArgument("resolution", default_value="0.05"),
            DeclareLaunchArgument("frame_id", default_value="odom"),
            DeclareLaunchArgument("base_frame_id", default_value="livox_frame"),
            DeclareLaunchArgument("sensor_max_range", default_value="40.0"),
            DeclareLaunchArgument("pointcloud_min_z", default_value="0.1"),
            DeclareLaunchArgument("pointcloud_max_z", default_value="1.0"),
            DeclareLaunchArgument("occupancy_min_z", default_value="0.1"),
            DeclareLaunchArgument("occupancy_max_z", default_value="1.0"),
            DeclareLaunchArgument("filter_speckles", default_value="true"),
            DeclareLaunchArgument("filter_ground", default_value="false"),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            Node(
                package="octomap_server",
                executable="octomap_server_node",
                name="octomap_server",
                output="screen",
                parameters=[
                    {
                        "resolution": ParameterValue(
                            LaunchConfiguration("resolution"), value_type=float
                        ),
                        "frame_id": LaunchConfiguration("frame_id"),
                        "base_frame_id": LaunchConfiguration("base_frame_id"),
                        "sensor_model.max_range": ParameterValue(
                            LaunchConfiguration("sensor_max_range"), value_type=float
                        ),
                        "pointcloud_min_z": ParameterValue(
                            LaunchConfiguration("pointcloud_min_z"), value_type=float
                        ),
                        "pointcloud_max_z": ParameterValue(
                            LaunchConfiguration("pointcloud_max_z"), value_type=float
                        ),
                        "occupancy_min_z": ParameterValue(
                            LaunchConfiguration("occupancy_min_z"), value_type=float
                        ),
                        "occupancy_max_z": ParameterValue(
                            LaunchConfiguration("occupancy_max_z"), value_type=float
                        ),
                        "filter_speckles": ParameterValue(
                            LaunchConfiguration("filter_speckles"), value_type=bool
                        ),
                        "use_sim_time": LaunchConfiguration("use_sim_time"),
                        "filter_ground": ParameterValue(
                            LaunchConfiguration("filter_ground"), value_type=bool
                        ),
                        # Keep the latest projected map available for late subscribers
                        # such as RViz or map_saver_cli started after mapping begins.
                        "latch": True,
                    }
                ],
                remappings=[
                    ("cloud_in", LaunchConfiguration("cloud_topic")),
                    ("projected_map", LaunchConfiguration("projected_map_topic")),
                ],
            ),
        ]
    )
