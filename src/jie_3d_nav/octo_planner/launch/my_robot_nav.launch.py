import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    jie_octomap_share = get_package_share_directory("jie_octomap")
    default_rviz_config = os.path.join(
        jie_octomap_share, "rviz", "mid360_localization.rviz"
    )
    web_root = os.path.join(jie_octomap_share, "web")
    web_server_script = os.path.abspath(
        os.path.join(
            jie_octomap_share,
            "..",
            "..",
            "lib",
            "jie_octomap",
            "no_cache_http_server.py",
        )
    )

    map_frame = LaunchConfiguration("map_frame")
    odom_frame = LaunchConfiguration("odom_frame")
    base_frame = LaunchConfiguration("base_frame")
    map_package_dir = LaunchConfiguration("map_package_dir")

    launch_rviz_arg = DeclareLaunchArgument(
        "launch_rviz",
        default_value="false",
        description="Launch RViz with a generic OctoMap display config.",
    )
    launch_map_gui_arg = DeclareLaunchArgument(
        "launch_map_gui",
        default_value="false",
        description="Launch the Qt map viewer and save/load GUI windows.",
    )
    launch_planner_arg = DeclareLaunchArgument(
        "launch_planner",
        default_value="true",
        description="Launch jie_path_node for 3D path planning.",
    )
    launch_controller_arg = DeclareLaunchArgument(
        "launch_controller",
        default_value="false",
        description=(
            "Launch d1_controller as a generic path tracker. Keep this off until "
            "your localization TF and cmd_vel pipeline are ready."
        ),
    )
    launch_livox_driver_arg = DeclareLaunchArgument(
        "launch_livox_driver",
        default_value="false",
        description="Launch the MID360 Livox ROS2 driver wrapper.",
    )
    launch_fastlivo_arg = DeclareLaunchArgument(
        "launch_fastlivo",
        default_value="false",
        description="Launch FAST-LIVO2 ROS2 as the odometry source for MID360.",
    )
    launch_lidar_localization_arg = DeclareLaunchArgument(
        "launch_lidar_localization",
        default_value="false",
        description="Launch lidar_localization_ros2 to publish map -> odom relocalization.",
    )
    launch_cmd_bridge_arg = DeclareLaunchArgument(
        "launch_cmd_bridge",
        default_value="false",
        description="Launch the /cmd_vel -> /ctrl_cmd bridge for MK-mini chassis control.",
    )
    launch_chassis_arg = DeclareLaunchArgument(
        "launch_chassis",
        default_value="false",
        description="Launch MK-mini yhs_can_control node.",
    )
    launch_web_arg = DeclareLaunchArgument(
        "launch_web",
        default_value="true",
        description="Launch the web-based OctoMap viewer.",
    )
    launch_rosbridge_arg = DeclareLaunchArgument(
        "launch_rosbridge",
        default_value="true",
        description="Launch rosbridge_websocket for the web client.",
    )
    use_fake_localization_arg = DeclareLaunchArgument(
        "use_fake_localization",
        default_value="false",
        description=(
            "Publish a fake animated map->odom TF for early UI/planner validation "
            "before integrating FAST-LIO2 or a relocalization stack."
        ),
    )
    publish_static_odom_to_base_arg = DeclareLaunchArgument(
        "publish_static_odom_to_base",
        default_value="false",
        description=(
            "Publish a fixed odom->base TF for early wiring tests. Disable this "
            "once your odometry/localization stack publishes a real transform."
        ),
    )
    web_http_port_arg = DeclareLaunchArgument(
        "web_http_port",
        default_value="8080",
        description="HTTP port for the web viewer.",
    )
    rviz_config_path_arg = DeclareLaunchArgument(
        "rviz_config_path",
        default_value=default_rviz_config,
        description=(
            "RViz config path. The default profile includes /initialpose, "
            "/cloud_registered, /initial_map, /pcl_pose and planning overlays."
        ),
    )
    map_package_dir_arg = DeclareLaunchArgument(
        "map_package_dir",
        default_value="",
        description=(
            "Optional navigation map package directory to autoload with "
            "map_package_manager. Leave empty if you plan to import maps manually."
        ),
    )
    map_frame_arg = DeclareLaunchArgument(
        "map_frame",
        default_value="map",
        description="Global planning frame.",
    )
    odom_frame_arg = DeclareLaunchArgument(
        "odom_frame",
        default_value="odom",
        description="Odometry frame used by the localization stack.",
    )
    base_frame_arg = DeclareLaunchArgument(
        "base_frame",
        default_value="livox_frame",
        description=(
            "Tracking frame used by the controller. For the first integration "
            "stage, this can be the lidar frame."
        ),
    )
    livox_config_path_arg = DeclareLaunchArgument(
        "livox_config_path",
        default_value=os.path.join(
            get_package_share_directory("octo_planner"),
            "config",
            "mid360_livox_config.json",
        ),
        description="Path to the MID360 Livox JSON configuration file.",
    )
    livox_publish_freq_arg = DeclareLaunchArgument(
        "livox_publish_freq",
        default_value="10.0",
        description="Point cloud publish frequency for livox_ros_driver2.",
    )
    fastlivo_config_path_arg = DeclareLaunchArgument(
        "fastlivo_config_path",
        default_value=os.path.join(
            get_package_share_directory("fast_livo"),
            "config",
            "mid360_lio_only.yaml",
        ),
        description="Path to the FAST-LIVO2 MID360 LiDAR+IMU odometry config.",
    )
    fastlivo_use_rviz_arg = DeclareLaunchArgument(
        "fastlivo_use_rviz",
        default_value="false",
        description="Launch FAST-LIVO2's RViz profile together with odometry.",
    )
    lidar_localization_param_path_arg = DeclareLaunchArgument(
        "lidar_localization_param_path",
        default_value=os.path.join(
            get_package_share_directory("octo_planner"),
            "config",
            "lidar_localization_mid360_fastlivo.yaml",
        ),
        description="Parameter file for lidar_localization_ros2 relocalization.",
    )
    lidar_localization_map_path_arg = DeclareLaunchArgument(
        "lidar_localization_map_path",
        default_value="",
        description="Absolute path to the pointcloud map used for relocalization.",
    )
    lidar_localization_cloud_topic_arg = DeclareLaunchArgument(
        "lidar_localization_cloud_topic",
        default_value="/cloud_registered",
        description="PointCloud2 topic consumed by lidar_localization_ros2.",
    )
    lidar_localization_set_initial_pose_arg = DeclareLaunchArgument(
        "lidar_localization_set_initial_pose",
        default_value="false",
        description="Set a startup initial pose for lidar_localization_ros2.",
    )
    lidar_localization_initial_pose_x_arg = DeclareLaunchArgument(
        "lidar_localization_initial_pose_x",
        default_value="0.0",
        description="Initial pose x for lidar_localization_ros2.",
    )
    lidar_localization_initial_pose_y_arg = DeclareLaunchArgument(
        "lidar_localization_initial_pose_y",
        default_value="0.0",
        description="Initial pose y for lidar_localization_ros2.",
    )
    lidar_localization_initial_pose_z_arg = DeclareLaunchArgument(
        "lidar_localization_initial_pose_z",
        default_value="0.0",
        description="Initial pose z for lidar_localization_ros2.",
    )
    lidar_localization_initial_pose_qx_arg = DeclareLaunchArgument(
        "lidar_localization_initial_pose_qx",
        default_value="0.0",
        description="Initial pose quaternion x for lidar_localization_ros2.",
    )
    lidar_localization_initial_pose_qy_arg = DeclareLaunchArgument(
        "lidar_localization_initial_pose_qy",
        default_value="0.0",
        description="Initial pose quaternion y for lidar_localization_ros2.",
    )
    lidar_localization_initial_pose_qz_arg = DeclareLaunchArgument(
        "lidar_localization_initial_pose_qz",
        default_value="0.0",
        description="Initial pose quaternion z for lidar_localization_ros2.",
    )
    lidar_localization_initial_pose_qw_arg = DeclareLaunchArgument(
        "lidar_localization_initial_pose_qw",
        default_value="1.0",
        description="Initial pose quaternion w for lidar_localization_ros2.",
    )
    cmd_vel_topic_arg = DeclareLaunchArgument(
        "cmd_vel_topic",
        default_value="/cmd_vel",
        description="Velocity command topic published by the controller.",
    )
    ctrl_cmd_topic_arg = DeclareLaunchArgument(
        "ctrl_cmd_topic",
        default_value="/ctrl_cmd",
        description="Chassis control topic consumed by MK-mini yhs_can_control.",
    )
    robot_radius_arg = DeclareLaunchArgument(
        "robot_radius",
        default_value="0.25",
        description="Robot collision radius in meters used by jie_path_node.",
    )
    wheel_base_arg = DeclareLaunchArgument(
        "wheel_base",
        default_value="0.6",
        description="Wheel base used by cmd_vel_to_ctrl_cmd_bridge and MK-mini chassis.",
    )
    chassis_params_file_arg = DeclareLaunchArgument(
        "chassis_params_file",
        default_value=os.path.join(
            get_package_share_directory("yhs_can_control"), "params", "cfg.yaml"
        ),
        description="Parameter file for MK-mini yhs_can_control.",
    )

    fake_map_to_odom_node = Node(
        package="octo_planner",
        executable="test_map_to_odom_tf_node",
        name="test_map_to_odom_tf_node",
        output="screen",
        condition=IfCondition(LaunchConfiguration("use_fake_localization")),
        parameters=[
            {
                "parent_frame": map_frame,
                "child_frame": odom_frame,
                "radius": 2.0,
                "orbit_period": 20.0,
                "spin_rate": 0.8,
            }
        ],
    )

    static_odom_to_base_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_odom_to_base",
        output="screen",
        condition=IfCondition(LaunchConfiguration("publish_static_odom_to_base")),
        arguments=["0", "0", "0", "0", "0", "0", odom_frame, base_frame],
    )

    livox_driver_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("octo_planner"),
                "launch",
                "mid360_driver.launch.py",
            )
        ),
        condition=IfCondition(LaunchConfiguration("launch_livox_driver")),
        launch_arguments={
            "config_path": LaunchConfiguration("livox_config_path"),
            "frame_id": base_frame,
            "publish_freq": LaunchConfiguration("livox_publish_freq"),
            "xfer_format": "0",
            "multi_topic": "0",
        }.items(),
    )
    fastlivo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("fast_livo"),
                "launch",
                "mapping_mid360_lio.launch.py",
            )
        ),
        condition=IfCondition(LaunchConfiguration("launch_fastlivo")),
        launch_arguments={
            "params_file": LaunchConfiguration("fastlivo_config_path"),
            "use_rviz": LaunchConfiguration("fastlivo_use_rviz"),
            "use_sim_time": "false",
        }.items(),
    )
    lidar_localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("octo_planner"),
                "launch",
                "mid360_relocalization.launch.py",
            )
        ),
        condition=IfCondition(LaunchConfiguration("launch_lidar_localization")),
        launch_arguments={
            "localization_param_path": LaunchConfiguration(
                "lidar_localization_param_path"
            ),
            "map_path": LaunchConfiguration("lidar_localization_map_path"),
            "cloud_topic": LaunchConfiguration("lidar_localization_cloud_topic"),
            "imu_topic": "/livox/imu",
            "registration_method": "NDT_OMP",
            "ndt_num_threads": "4",
            "global_frame_id": map_frame,
            "odom_frame_id": odom_frame,
            "base_frame_id": base_frame,
            "enable_map_odom_tf": "true",
            "set_initial_pose": LaunchConfiguration(
                "lidar_localization_set_initial_pose"
            ),
            "initial_pose_x": LaunchConfiguration(
                "lidar_localization_initial_pose_x"
            ),
            "initial_pose_y": LaunchConfiguration(
                "lidar_localization_initial_pose_y"
            ),
            "initial_pose_z": LaunchConfiguration(
                "lidar_localization_initial_pose_z"
            ),
            "initial_pose_qx": LaunchConfiguration(
                "lidar_localization_initial_pose_qx"
            ),
            "initial_pose_qy": LaunchConfiguration(
                "lidar_localization_initial_pose_qy"
            ),
            "initial_pose_qz": LaunchConfiguration(
                "lidar_localization_initial_pose_qz"
            ),
            "initial_pose_qw": LaunchConfiguration(
                "lidar_localization_initial_pose_qw"
            ),
        }.items(),
    )

    planner_node = Node(
        package="octo_planner",
        executable="jie_path_node",
        name="jie_path_node",
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_planner")),
        parameters=[
            {
                "octomap_topic": "/octomap",
                "start_topic": "/start_point",
                "goal_topic": "/goal_point",
                "goal_pose_topic": "/goal_pose",
                "path_topic": "/planned_path",
                "path_marker_topic": "/planned_path_marker",
                "preblocked_marker_topic": "/preblocked_cells_markers",
                "edited_occupied_marker_topic": "/edited_occupied_markers",
                "traversable_marker_topic": "/traversable_cells_markers",
                "risk_cost_topic": "/risk_cost_cells",
                "frame_id": map_frame,
                "map_id": "my_robot_map",
                "source_world_file": "",
                "robot_radius": ParameterValue(
                    LaunchConfiguration("robot_radius"), value_type=float
                ),
                "max_iterations": 500000,
                "snap_search_radius_cells": 12,
                "require_ground_support": True,
                "strict_direct_ground_support": False,
                "ground_support_xy_radius_cells": 1,
                "ground_support_depth_cells": 1,
                "enable_preblocked_costmap": True,
                "preblocked_costmap_radius_cells": 3,
                "preblocked_costmap_weight": 2.5,
            }
        ],
    )

    controller_node = Node(
        package="octo_planner",
        executable="d1_controller",
        name="path_tracker",
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_controller")),
        parameters=[
            {
                "path_topic": "/planned_path",
                "start_navigation_topic": "/start_navigation",
                "stop_navigation_topic": "/stop_navigation",
                "require_start_command": True,
                "cmd_vel_topic": LaunchConfiguration("cmd_vel_topic"),
                "manual_cmd_vel_topic": "/web_cmd_vel",
                "tracking_point_marker_topic": "/tracking_point_marker",
                "map_frame": map_frame,
                "base_frame": base_frame,
                "base_frame_candidates": base_frame,
                "robot_center_offset_frame": base_frame,
                "robot_center_offset_x": 0.0,
                "robot_center_offset_y": 0.0,
                "robot_center_offset_z": 0.0,
                "enable_tracking_debug_view": False,
                "enable_lateral_motion": False,
                "max_linear_speed": 0.6,
                "max_lateral_speed": 0.0,
                "max_angular_speed": 0.8,
                "goal_position_tolerance": 0.15,
                "goal_yaw_tolerance": 0.25,
            }
        ],
    )

    cmd_bridge_node = Node(
        package="octo_planner",
        executable="cmd_vel_to_ctrl_cmd_bridge",
        name="cmd_vel_to_ctrl_cmd_bridge",
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_cmd_bridge")),
        parameters=[
            {
                "cmd_vel_topic": LaunchConfiguration("cmd_vel_topic"),
                "ctrl_cmd_topic": LaunchConfiguration("ctrl_cmd_topic"),
                "wheel_base": ParameterValue(LaunchConfiguration("wheel_base"), value_type=float),
                "publish_rate": 20.0,
                "cmd_timeout_sec": 0.5,
                "max_speed_mps": 0.8,
                "max_steering_deg": 25.0,
                "min_speed_for_steering": 0.08,
                "forward_gear": 4,
                "reverse_gear": 2,
                "neutral_gear": 3,
            }
        ],
    )

    chassis_node = Node(
        package="yhs_can_control",
        executable="yhs_can_control_node",
        name="yhs_can_control_node",
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_chassis")),
        parameters=[LaunchConfiguration("chassis_params_file")],
    )

    map_package_manager_node = Node(
        package="jie_octomap",
        executable="map_package_manager",
        name="map_package_manager",
        output="screen",
        parameters=[{"autoload_package_path": map_package_dir}],
    )

    occupied_marker_node = Node(
        package="jie_octomap",
        executable="octomap_to_occupied_markers_node",
        name="octomap_to_occupied_markers",
        output="screen",
        parameters=[
            {
                "octomap_topic": "/octomap",
                "marker_topic": "/octomap_occupied_markers",
                "frame_id": map_frame,
            }
        ],
    )

    map_viewer_gui_node = Node(
        package="jie_octomap",
        executable="map_viewer_gui",
        name="map_viewer_gui",
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_map_gui")),
        parameters=[
            {
                "tf_parent_frame": map_frame,
                "tf_child_frame": base_frame,
            }
        ],
    )

    map_save_gui_node = Node(
        package="jie_octomap",
        executable="map_save_gui",
        name="map_save_gui",
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_map_gui")),
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", LaunchConfiguration("rviz_config_path")],
        condition=IfCondition(LaunchConfiguration("launch_rviz")),
    )

    web_http_server = ExecuteProcess(
        cmd=[
            web_server_script,
            "--port",
            LaunchConfiguration("web_http_port"),
            "--directory",
            web_root,
        ],
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_web")),
    )

    rosbridge_node = Node(
        package="rosbridge_server",
        executable="rosbridge_websocket",
        name="rosbridge_websocket",
        output="screen",
        condition=IfCondition(LaunchConfiguration("launch_rosbridge")),
    )

    return LaunchDescription(
        [
            launch_rviz_arg,
            launch_map_gui_arg,
            launch_planner_arg,
            launch_controller_arg,
            launch_livox_driver_arg,
            launch_fastlivo_arg,
            launch_lidar_localization_arg,
            launch_cmd_bridge_arg,
            launch_chassis_arg,
            launch_web_arg,
            launch_rosbridge_arg,
            use_fake_localization_arg,
            publish_static_odom_to_base_arg,
            web_http_port_arg,
            rviz_config_path_arg,
            map_package_dir_arg,
            map_frame_arg,
            odom_frame_arg,
            base_frame_arg,
            livox_config_path_arg,
            livox_publish_freq_arg,
            fastlivo_config_path_arg,
            fastlivo_use_rviz_arg,
            lidar_localization_param_path_arg,
            lidar_localization_map_path_arg,
            lidar_localization_cloud_topic_arg,
            lidar_localization_set_initial_pose_arg,
            lidar_localization_initial_pose_x_arg,
            lidar_localization_initial_pose_y_arg,
            lidar_localization_initial_pose_z_arg,
            lidar_localization_initial_pose_qx_arg,
            lidar_localization_initial_pose_qy_arg,
            lidar_localization_initial_pose_qz_arg,
            lidar_localization_initial_pose_qw_arg,
            cmd_vel_topic_arg,
            ctrl_cmd_topic_arg,
            robot_radius_arg,
            wheel_base_arg,
            chassis_params_file_arg,
            fake_map_to_odom_node,
            static_odom_to_base_node,
            livox_driver_launch,
            fastlivo_launch,
            lidar_localization_launch,
            planner_node,
            controller_node,
            cmd_bridge_node,
            chassis_node,
            map_package_manager_node,
            occupied_marker_node,
            map_viewer_gui_node,
            map_save_gui_node,
            rviz_node,
            web_http_server,
            rosbridge_node,
        ]
    )
