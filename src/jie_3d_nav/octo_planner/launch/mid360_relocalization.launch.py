import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    octo_planner_share = get_package_share_directory("octo_planner")
    default_param_path = os.path.join(
        octo_planner_share, "config", "lidar_localization_mid360_fastlivo.yaml"
    )

    localization_param_path_arg = DeclareLaunchArgument(
        "localization_param_path",
        default_value=default_param_path,
        description="Parameter file for lidar_localization_ros2 relocalization.",
    )
    map_path_arg = DeclareLaunchArgument(
        "map_path",
        default_value="",
        description="Absolute path to the relocalization pointcloud map (.pcd or .ply).",
    )
    cloud_topic_arg = DeclareLaunchArgument(
        "cloud_topic",
        default_value="/cloud_registered",
        description="PointCloud2 topic consumed by lidar_localization_ros2.",
    )
    imu_topic_arg = DeclareLaunchArgument(
        "imu_topic",
        default_value="/livox/imu",
        description="IMU topic exposed to lidar_localization_ros2.",
    )
    registration_method_arg = DeclareLaunchArgument(
        "registration_method",
        default_value="NDT_OMP",
        description="Registration backend used by lidar_localization_ros2.",
    )
    ndt_num_threads_arg = DeclareLaunchArgument(
        "ndt_num_threads",
        default_value="4",
        description="Number of NDT_OMP threads for relocalization.",
    )
    global_frame_id_arg = DeclareLaunchArgument(
        "global_frame_id",
        default_value="map",
        description="Global map frame published by the relocalization stack.",
    )
    odom_frame_id_arg = DeclareLaunchArgument(
        "odom_frame_id",
        default_value="odom",
        description="Odometry frame consumed by the relocalization stack.",
    )
    base_frame_id_arg = DeclareLaunchArgument(
        "base_frame_id",
        default_value="livox_frame",
        description="Base frame used by lidar_localization_ros2.",
    )
    enable_map_odom_tf_arg = DeclareLaunchArgument(
        "enable_map_odom_tf",
        default_value="true",
        description="Whether lidar_localization_ros2 publishes map -> odom.",
    )
    set_initial_pose_arg = DeclareLaunchArgument(
        "set_initial_pose",
        default_value="false",
        description="Set a startup initial pose through launch arguments.",
    )
    initial_pose_x_arg = DeclareLaunchArgument("initial_pose_x", default_value="0.0")
    initial_pose_y_arg = DeclareLaunchArgument("initial_pose_y", default_value="0.0")
    initial_pose_z_arg = DeclareLaunchArgument("initial_pose_z", default_value="0.0")
    initial_pose_qx_arg = DeclareLaunchArgument("initial_pose_qx", default_value="0.0")
    initial_pose_qy_arg = DeclareLaunchArgument("initial_pose_qy", default_value="0.0")
    initial_pose_qz_arg = DeclareLaunchArgument("initial_pose_qz", default_value="0.0")
    initial_pose_qw_arg = DeclareLaunchArgument("initial_pose_qw", default_value="1.0")

    relocalization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("lidar_localization_ros2"),
                "launch",
                "mid360_legged_localization.launch.py",
            )
        ),
        launch_arguments={
            "localization_param_dir": LaunchConfiguration("localization_param_path"),
            "map_path": LaunchConfiguration("map_path"),
            "cloud_topic": LaunchConfiguration("cloud_topic"),
            "imu_topic": LaunchConfiguration("imu_topic"),
            "registration_method": LaunchConfiguration("registration_method"),
            "ndt_num_threads": LaunchConfiguration("ndt_num_threads"),
            "global_frame_id": LaunchConfiguration("global_frame_id"),
            "odom_frame_id": LaunchConfiguration("odom_frame_id"),
            "base_frame_id": LaunchConfiguration("base_frame_id"),
            "enable_map_odom_tf": LaunchConfiguration("enable_map_odom_tf"),
            "set_initial_pose": LaunchConfiguration("set_initial_pose"),
            "initial_pose_x": LaunchConfiguration("initial_pose_x"),
            "initial_pose_y": LaunchConfiguration("initial_pose_y"),
            "initial_pose_z": LaunchConfiguration("initial_pose_z"),
            "initial_pose_qx": LaunchConfiguration("initial_pose_qx"),
            "initial_pose_qy": LaunchConfiguration("initial_pose_qy"),
            "initial_pose_qz": LaunchConfiguration("initial_pose_qz"),
            "initial_pose_qw": LaunchConfiguration("initial_pose_qw"),
            "publish_lidar_tf": "false",
            "publish_imu_tf": "false",
            "use_imu_preintegration": "false",
            "use_sim_time": "false",
        }.items(),
    )

    return LaunchDescription(
        [
            localization_param_path_arg,
            map_path_arg,
            cloud_topic_arg,
            imu_topic_arg,
            registration_method_arg,
            ndt_num_threads_arg,
            global_frame_id_arg,
            odom_frame_id_arg,
            base_frame_id_arg,
            enable_map_odom_tf_arg,
            set_initial_pose_arg,
            initial_pose_x_arg,
            initial_pose_y_arg,
            initial_pose_z_arg,
            initial_pose_qx_arg,
            initial_pose_qy_arg,
            initial_pose_qz_arg,
            initial_pose_qw_arg,
            relocalization_launch,
        ]
    )
