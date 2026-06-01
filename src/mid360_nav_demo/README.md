# MID360 Nav Demo

ROS2 demo package for online MID360 mapping, projected map saving, ICP relocalization, and Nav2 navigation.

## Mapping

```bash
source /home/yangxuan/ros2_ws/src/install/setup.bash
ros2 launch mid360_nav_demo online_mapping_demo.launch.py
```

The mapping demo starts:

- `livox_ros_driver2`
- `fast_livo`
- `octomap_server`, remapped from `/cloud_registered` to `/projected_map`
- RViz

FAST-LIVO2 saves PCD files under `FAST-LIVO2-ROS2/Log/PCD` when enabled by its parameter file.

## Save 2D Map

```bash
source /home/yangxuan/ros2_ws/src/install/setup.bash
ros2 launch mid360_nav_demo save_projected_map.launch.py \
  map_prefix:=/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/site1
```

This calls `nav2_map_server map_saver_cli` on `/projected_map` and writes `site1.pgm` plus `site1.yaml`.
The launch subscribes with volatile QoS and waits up to 20 seconds, which matches
live `/projected_map` output from `octomap_server`.

## Gazebo Simulation Smoke Test

There is a usable MID360 CustomMsg simulation path on GitHub:

- `LCAS/livox_laser_simulation_ros2`: Gazebo Classic Livox plugin publishing both `livox_ros_driver2/msg/CustomMsg` and `sensor_msgs/msg/PointCloud2`.
- `LihanChen2004/PB_RMSimulation`: example robot/world using the MID360 plugin on `/livox/lidar` and IMU on `/livox/imu`.

This machine already has those packages under `/home/yangxuan/ws_livox` and `/home/yangxuan/ros2_ws_test/PB_RMSimulation`. Source them before this workspace, then launch the simulation chain:

```bash
source /home/yangxuan/ros2_ws_test/PB_RMSimulation/install/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash
ros2 launch mid360_nav_demo sim_mapping_demo.launch.py
```

The simulation launch uses `config/mid360_lio_sim_custom.yaml`. This is intentional:
the Gazebo MID360 plugin publishes `/livox/lidar` as `livox_ros_driver2/msg/CustomMsg`,
and this FAST-LIVO2 codebase selects the CustomMsg callback with `preprocess.lidar_type: 1`.
By default the simulated MID360 is mounted at `lidar_xyz:="0.12 0.0 0.175"`,
matching the original PB_RMSimulation xacro.
If ground points dominate the view, raise the sensor or narrow the octomap height
slice, for example:

```bash
ros2 launch mid360_nav_demo sim_mapping_demo.launch.py \
  lidar_xyz:="0.12 0.0 0.65" \
  pointcloud_min_z:=0.20 \
  occupancy_min_z:=0.20 \
  pointcloud_max_z:=1.30 \
  occupancy_max_z:=1.30 \
  launch_rviz:=true
```

Expected simulation topics:

- `/livox/lidar`: `livox_ros_driver2/msg/CustomMsg`, consumed by FAST-LIVO2.
- `/livox/imu`: simulated IMU, consumed by FAST-LIVO2.
- `/cloud_registered`: FAST-LIVO2 registered cloud.
- `/projected_map`: octomap 2D projection.

Useful checks:

```bash
ros2 topic info /livox/lidar
ros2 topic hz /livox/lidar
ros2 topic hz /cloud_registered
ros2 topic info /projected_map -v
ros2 topic echo /projected_map --once --field info
```

## Navigation

```bash
source /home/yangxuan/ros2_ws/src/install/setup.bash
ros2 launch mid360_nav_demo online_nav_demo.launch.py \
  map:=/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/site1.yaml \
  global_map_pcd:=/home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/Log/PCD/all_downsampled_points.pcd
```

In RViz, publish `2D Pose Estimate` to trigger ICP relocalization. The node publishes:

- `map -> odom`
- `/relocalization/aligned_cloud`
- `/relocalization/status`

Optional chassis output can be enabled with:

```bash
ros2 launch mid360_nav_demo online_nav_demo.launch.py \
  launch_cmd_bridge:=true launch_chassis:=true
```

## Important Frames

The first demo version assumes FAST-LIVO2 publishes odometry as `odom -> livox_frame`, and ICP publishes `map -> odom`. Nav2 therefore sees:

```text
map -> odom -> livox_frame
```

If the chassis later provides a stable `base_link`, set `tracking_frame:=base_link` and update Nav2 params accordingly.
