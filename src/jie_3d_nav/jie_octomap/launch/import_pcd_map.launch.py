from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_prefix
import os


def generate_launch_description():
    resolution = LaunchConfiguration("resolution")
    voxel_downsample_m = LaunchConfiguration("voxel_downsample_m")
    min_points_per_voxel = LaunchConfiguration("min_points_per_voxel")
    min_cluster_voxels = LaunchConfiguration("min_cluster_voxels")
    pcd_file = LaunchConfiguration("pcd_file")
    launch_import_gui = LaunchConfiguration("launch_import_gui")
    default_import_gui_python = os.path.join(
        os.path.expanduser("~"), "ros2_ws", ".venv-jie3d", "bin", "python"
    )
    import_gui_python = LaunchConfiguration("import_gui_python")
    import_gui_script = os.path.join(
        get_package_prefix("jie_octomap"), "lib", "jie_octomap", "pcd_map_import_gui"
    )

    pcd_to_octomap_node = Node(
        package="jie_octomap",
        executable="pcd_to_octomap_node",
        name="pcd_to_octomap",
        output="screen",
        parameters=[
            {
                "pcd_file_cmd_topic": "/pcd_file_cmd",
                "pcd_file": pcd_file,
                "octomap_topic": "/octomap",
                "frame_id": "map",
                "resolution": ParameterValue(resolution, value_type=float),
                "voxel_downsample_m": ParameterValue(voxel_downsample_m, value_type=float),
                "min_points_per_voxel": ParameterValue(
                    min_points_per_voxel, value_type=int
                ),
                "min_cluster_voxels": ParameterValue(min_cluster_voxels, value_type=int),
            }
        ],
    )

    planner_node = Node(
        package="octo_planner",
        executable="jie_path_node",
        name="jie_path_node",
        output="screen",
        parameters=[
            {
                "octomap_topic": "/octomap",
                "start_topic": "/start_point",
                "goal_topic": "/goal_point",
                "path_topic": "/planned_path",
                "path_marker_topic": "/planned_path_marker",
                "preblocked_marker_topic": "/preblocked_cells_markers",
                "traversable_marker_topic": "/traversable_cells_markers",
                "risk_cost_topic": "/risk_cost_cells",
                "frame_id": "map",
                "map_id": "imported_pcd_map",
                "source_world_file": "",
                "robot_radius": 0.25,
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

    occupied_marker_node = Node(
        package="jie_octomap",
        executable="octomap_to_occupied_markers_node",
        name="octomap_to_occupied_markers",
        output="screen",
        parameters=[
            {
                "octomap_topic": "/octomap",
                "marker_topic": "/octomap_occupied_markers",
                "frame_id": "map",
            }
        ],
    )

    map_package_manager_node = Node(
        package="jie_octomap",
        executable="map_package_manager",
        name="map_package_manager",
        output="screen",
    )

    importer_gui_node = ExecuteProcess(
        cmd=[import_gui_python, import_gui_script],
        output="screen",
        condition=IfCondition(launch_import_gui),
        additional_env={"PYTHONNOUSERSITE": "1"},
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "resolution",
                default_value="0.5",
                description="OctoMap resolution in meters for imported PCD maps.",
            ),
            DeclareLaunchArgument(
                "pcd_file",
                default_value="",
                description=(
                    "Optional absolute path to a PCD/PLY file. When set, pcd_to_octomap_node "
                    "loads it directly without waiting for /pcd_file_cmd."
                ),
            ),
            DeclareLaunchArgument(
                "launch_import_gui",
                default_value="true",
                description="Whether to start the Python Open3D import GUI.",
            ),
            DeclareLaunchArgument(
                "import_gui_python",
                default_value=default_import_gui_python,
                description=(
                    "Python interpreter used to launch pcd_map_import_gui. "
                    "Recommend pointing this to .venv-jie3d/bin/python."
                ),
            ),
            DeclareLaunchArgument(
                "voxel_downsample_m",
                default_value="0.0",
                description=(
                    "Additional downsample size inside pcd_to_octomap_node. "
                    "The GUI already writes a preprocessed temporary PCD, so 0.0 avoids double downsampling."
                ),
            ),
            DeclareLaunchArgument(
                "min_points_per_voxel",
                default_value="1",
                description="Minimum source points required to keep an occupied voxel.",
            ),
            DeclareLaunchArgument(
                "min_cluster_voxels",
                default_value="1",
                description="Minimum connected occupied voxels required to keep a cluster.",
            ),
            pcd_to_octomap_node,
            planner_node,
            occupied_marker_node,
            map_package_manager_node,
            importer_gui_node,
        ]
    )
