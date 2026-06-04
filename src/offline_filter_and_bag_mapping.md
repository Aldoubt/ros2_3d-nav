# 离线滤波参数测试与 Bag 建图流程

本文档用于整理两类离线测试：

1. 只复盘 `octomap 2D 投影`，快速对比 `projected_map` 滤波参数。
2. 从 `bag` 里的原始雷达和 IMU 重跑 `FAST-LIVO2 + octomap`，离线验证建图效果。

适用目录约定：

```text
工作空间: /home/yangxuan/ros2_ws
源码目录: /home/yangxuan/ros2_ws/src
bag 目录: /home/yangxuan/ros2_ws/src/bags
```

---

## 1. 测试目标

离线测试建议分开做，不要一次把所有参数一起改掉。

### 1.1 octomap 2D 投影参数

主要影响 `/projected_map` 的二维占据效果：

```text
pointcloud_min_z  // 低于这个高度的点不参与建图 
pointcloud_max_z  // 高于这个高度的点不参与建图
occupancy_min_z   // 低于这个高度的占据体素不投影为 2D 障碍，调高可以减少地面杂点；太高会让低矮障碍在 PGM 里消失
occupancy_max_z   // 高于这个高度的占据体素不投影为 2D 障碍
filter_speckles   // 去掉孤立小黑点
filter_ground     // 尝试分割/过滤地面，平整地面可以开；大棚有垄、坡、凹凸地面时可能误删低矮障碍
resolution        // 决定栅格/体素大小，
sensor_max_range  // 限制传感器最大作用距离
```

适合回答的问题：

```text
地面黑点为什么多
低矮障碍为什么丢失
高处结构是否被错误投影到 2D 地图
不同高度窗口对通行区域影响多大
```

### 1.2 FAST-LIVO2 前端/预处理参数

主要影响 `/cloud_registered` 质量和整体建图稳定性：

```text
preprocess.blind
preprocess.point_filter_num
preprocess.filter_size_surf
lio.voxel_size
pcd_save.filter_size_pcd
```

适合回答的问题：

```text
点云是否过密导致抖动或拖慢
近距离噪点是否过多
下采样后地图是否仍保留关键结构
FAST-LIVO2 重跑后 /cloud_registered 是否更干净
```

---

## 2. 基础准备

每个新终端先执行：

```bash
conda deactivate
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash
```

先确认 bag 基本信息：

```bash
ros2 bag info /home/yangxuan/ros2_ws/src/bags/你的bag目录
```

当前仓库里已有一个示例：

```text
/home/yangxuan/ros2_ws/src/bags/mid360_mapping_20260603_195044
```

已知这个 bag 包含：

```text
/livox/lidar         sensor_msgs/msg/PointCloud2
/livox/imu           sensor_msgs/msg/Imu
/cloud_registered    sensor_msgs/msg/PointCloud2
/aft_mapped_to_init  nav_msgs/msg/Odometry
/projected_map       nav_msgs/msg/OccupancyGrid
/tf                  tf2_msgs/msg/TFMessage
```

重要说明：

```text
当前 MID360 + FAST-LIVO2 实车链路使用的是 Livox PointCloud2(PointXYZRTLT)。
也就是 /livox/lidar 为 sensor_msgs/msg/PointCloud2 时，
应继续使用 mid360_lio_only.yaml 这类 lidar_type:=7 的 MID360 配置。
```

---

## 3. 推荐测试策略

建议先跑“快路径”，再跑“全链路”。

### 3.1 快路径：只测 octomap 2D 滤波

适用场景：

```text
只想比较 /projected_map 效果
不想每次都重跑 FAST-LIVO2
bag 里已经录了 /cloud_registered
```

优点：

```text
启动快
变量少
便于集中调 pointcloud_min_z / occupancy_min_z 一类参数
```

### 3.2 全链路：raw bag 重跑 FAST-LIVO2 + octomap

适用场景：

```text
怀疑 /cloud_registered 本身就不理想
需要一起评估 FAST-LIVO2 预处理和 octomap 投影
要重新导出 PCD 和新的 2D 地图
```

优点：

```text
能验证原始输入到最终地图的完整效果
能比较不同 FAST-LIVO2 参数对后续 octomap 的影响
```

---

## 4. 流程 A：只回放 /cloud_registered，快速调 2D 地图参数

### 4.1 启动 octomap + RViz + GUI

终端 1：

```bash
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash

ros2 launch mid360_nav_demo online_mapping_demo.launch.py \
  launch_driver:=false \
  launch_fast_livo:=false \
  launch_octomap:=true \
  launch_rviz:=true \
  launch_tuning_gui:=true \
  use_sim_time:=true \
  cloud_topic:=/cloud_registered \
  projected_map_topic:=/projected_map \
  octomap_frame:=odom \
  base_frame_id:=livox_frame
```

这条命令只保留：

```text
octomap_server
RViz
octomap_tuning_gui
```

### 4.2 回放 bag

终端 2：

```bash
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash

ros2 bag play /home/yangxuan/ros2_ws/src/bags/mid360_mapping_20260603_195044 \
  --clock \
  --topics /cloud_registered /aft_mapped_to_init /tf
```

注意：

```text
这里不要回放 /projected_map，避免和当前 octomap_server 的输出冲突。
```

### 4.3 观察与调参

RViz 重点看：

```text
Fixed Frame: odom
PointCloud2: /cloud_registered
Map: /projected_map
TF
```

终端检查：

```bash
ros2 topic hz /cloud_registered
ros2 topic info /projected_map -v
ros2 topic echo /projected_map --once --field info
```

GUI 调参建议：

```text
地面黑点多：提高 pointcloud_min_z、occupancy_min_z
低矮障碍丢失：降低 pointcloud_min_z、occupancy_min_z
高处结构干扰：降低 pointcloud_max_z、occupancy_max_z
孤立噪点多：filter_speckles 保持 true
```

推荐起步值：

```text
pointcloud_min_z = 0.05
occupancy_min_z = 0.08
pointcloud_max_z = 1.20
occupancy_max_z = 1.20
filter_speckles = true
filter_ground = false
```

### 4.4 保存结果

GUI 里点 `Save PGM/YAML`，或者另开终端保存：

```bash
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash

ros2 launch mid360_nav_demo save_projected_map.launch.py \
  map_prefix:=/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/offline_case_a
```

建议命名带参数信息，例如：

```text
offline_case_a_z005_008_zmax120_fs1
offline_case_a_ground_on
offline_case_a_low_obstacle
```

---

## 5. 流程 B：从 raw bag 重跑 FAST-LIVO2 + octomap

### 5.1 准备 FAST-LIVO2 参数文件

基准文件：

```text
/home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/config/mid360_lio_only.yaml
```

建议每组测试都复制一份，避免把基线改乱：

```bash
cp /home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/config/mid360_lio_only.yaml \
   /home/yangxuan/ros2_ws/src/mid360_nav_demo/config/mid360_lio_only_test_a.yaml
```

优先关注这些字段：

```text
preprocess.blind
preprocess.point_filter_num
preprocess.filter_size_surf
lio.voxel_size
pcd_save.filter_size_pcd
```

一组较稳妥的起步值：

```text
preprocess.blind: 0.5
preprocess.point_filter_num: 1
preprocess.filter_size_surf: 0.1
lio.voxel_size: 0.5
pcd_save.filter_size_pcd: 0.15
```

### 5.2 启动全链路离线建图

终端 1：

```bash
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash

ros2 launch mid360_nav_demo online_mapping_demo.launch.py \
  launch_driver:=false \
  launch_fast_livo:=true \
  launch_octomap:=true \
  launch_rviz:=true \
  launch_tuning_gui:=true \
  use_sim_time:=true \
  fast_livo_params:=/home/yangxuan/ros2_ws/src/mid360_nav_demo/config/mid360_lio_only_test_a.yaml \
  cloud_topic:=/cloud_registered \
  projected_map_topic:=/projected_map \
  octomap_frame:=odom \
  base_frame_id:=livox_frame
```

### 5.3 回放原始 bag 输入

终端 2：

```bash
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash

ros2 bag play /home/yangxuan/ros2_ws/src/bags/mid360_mapping_20260603_195044 \
  --clock \
  --topics /livox/lidar /livox/imu /tf
```

注意：

```text
这里不要同时回放 /cloud_registered、/aft_mapped_to_init、/projected_map，
否则会和 FAST-LIVO2、octomap_server 的新输出混在一起，无法判断结果来自谁。
```

### 5.4 检查链路是否正常

```bash
ros2 topic hz /livox/lidar
ros2 topic hz /livox/imu
ros2 topic hz /cloud_registered
ros2 topic info /aft_mapped_to_init -v
ros2 topic info /projected_map -v
ros2 run tf2_ros tf2_echo odom livox_frame
```

如果 `/cloud_registered` 没出来，优先检查：

```text
bag 中 /livox/lidar 的消息类型
FAST-LIVO2 参数文件中的 preprocess.lidar_type
是否忘记 use_sim_time:=true
是否 bag play 时没有带 --clock
```

### 5.5 保存结果

保存 2D 地图：

```bash
ros2 launch mid360_nav_demo save_projected_map.launch.py \
  map_prefix:=/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/offline_full_test_a
```

检查 FAST-LIVO2 生成的 PCD：

```bash
ls -lh /home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/Log/PCD
```

建议把每轮输出单独归档，例如：

```text
maps/offline_full_test_a.yaml
maps/offline_full_test_a.pgm
PCD/all_downsampled_points_test_a.pcd
参数文件 mid360_lio_only_test_a.yaml
```

---

## 6. 参数调整建议

### 6.1 先调 octomap，再调 FAST-LIVO2

推荐顺序：

```text
先固定 FAST-LIVO2，只调 2D 投影参数
确定高度窗口后，再回头调 FAST-LIVO2 的 blind / 下采样
```

原因：

```text
octomap 参数对 2D 地图可见变化最快
FAST-LIVO2 变化会同时影响里程计、点云密度和最终地图
```

### 6.2 octomap 常见现象与对应动作

```text
地面噪点多:
  pointcloud_min_z += 0.02 ~ 0.05
  occupancy_min_z += 0.02 ~ 0.05

低矮障碍缺失:
  pointcloud_min_z -= 0.02
  occupancy_min_z -= 0.02

墙上/高处结构投影到平面:
  pointcloud_max_z -= 0.10 ~ 0.30
  occupancy_max_z -= 0.10 ~ 0.30

稀疏孤立黑点:
  filter_speckles=true
```

### 6.3 FAST-LIVO2 常见现象与对应动作

```text
近距离杂点多:
  preprocess.blind 适当增大

点太密、回放很吃力:
  preprocess.point_filter_num 增大
  preprocess.filter_size_surf 增大

结构细节丢失:
  preprocess.filter_size_surf 减小
  lio.voxel_size 减小

导出的 PCD 太大:
  pcd_save.filter_size_pcd 增大
```

---

## 7. 推荐测试记录模板

建议每测一组就记一行，后面最容易回溯。

```markdown
| 编号 | bag | 模式 | FAST-LIVO 参数文件 | octomap 参数 | 结果现象 | 输出地图 |
| --- | --- | --- | --- | --- | --- | --- |
| A01 | mid360_mapping_20260603_195044 | octomap-only | - | min_z=0.05/0.08 max_z=1.2/1.2 fs=true | 地面噪点少，低矮障碍保留 | offline_case_a |
| B01 | mid360_mapping_20260603_195044 | full-chain | mid360_lio_only_test_a.yaml | min_z=0.05/0.08 max_z=1.2/1.2 fs=true | 点云更稳，地图边缘更完整 | offline_full_test_a |
```

也建议记录下面这些定性结论：

```text
地图边界是否闭合
地面黑点是否明显
门口/桌腿/箱体这类低矮障碍是否保留
回放是否流畅
FAST-LIVO2 是否有明显漂移或抖动
```

---

## 8. 常见坑

### 8.1 忘记 use_sim_time

症状：

```text
节点启动了，但数据不同步
话题有数据，RViz 不更新
```

处理：

```text
launch 加 use_sim_time:=true
bag play 加 --clock
```

### 8.2 同时回放旧输出和新输出

症状：

```text
/cloud_registered、/projected_map 看起来有数据
但无法判断到底来自 bag 还是来自当前算法
```

处理：

```text
测 octomap-only 时，只回放 /cloud_registered 一类上游输入
测 full-chain 时，只回放 /livox/lidar /livox/imu /tf
```

### 8.3 直接覆盖参数文件

症状：

```text
后面分不清哪套参数对应哪张地图
```

处理：

```text
每轮复制一个新参数文件
地图文件名带测试编号
记录表同步更新
```

### 8.4 先关建图再保存地图

症状：

```text
save_projected_map 超时
GUI 点保存失败
```

处理：

```text
先保存 /projected_map
再 Ctrl+C 停止当前离线回放或建图
```

---

## 9. 一套推荐起步流程

如果只是想尽快开始，直接按下面做：

1. 先跑“流程 A”，只回放 `/cloud_registered`，把 `pointcloud_min_z / occupancy_min_z` 调到满意。
2. 保存一张 `offline_case_a` 的 2D 地图。
3. 再跑“流程 B”，复制 `mid360_lio_only.yaml` 为测试版，只改一两个 FAST-LIVO2 参数。
4. 保存 `offline_full_test_a` 的地图和 PCD。
5. 用记录表对比两次结果，再决定是否继续调 `blind`、`filter_size_surf`、`voxel_size`。

