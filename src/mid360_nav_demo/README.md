# mid360_nav_demo

`mid360_nav_demo` 是当前工作空间里围绕 `Livox MID360` 组织的建图、地图导出、重定位和原始导航演示包。它负责承接底层传感器与定位导航主链，是总控 GUI 和 `agt_nav_console` 之下最核心的业务入口之一。

如果把整个工作空间理解成一套完整系统，那么这个包更偏“底层业务主链”，而 `agt_nav_console` 更偏“上层组织与联调入口”。

## 包定位

当前 `mid360_nav_demo` 主要负责：

- 在线建图
- 二维投影地图保存
- 全局点云地图驱动的重定位
- 原始导航链启动
- MID360 场景下的导航联调 demo

## 核心能力

### 1. 在线建图

当前建图主入口：

- `launch/online_mapping_demo.launch.py`

推荐启动：

```bash
export WS_ROOT=/path/to/your/ros2_ws
export ROS_DISTRO=${ROS_DISTRO:-humble}

source "/opt/ros/${ROS_DISTRO}/setup.bash"
source "${WS_ROOT}/install/setup.bash"

ros2 launch mid360_nav_demo online_mapping_demo.launch.py
```

这条链路通常会启动：

- `livox_ros_driver2`
- `fast_livo`
- `octomap_server`
- `RViz`

建图完成后，`FAST-LIVO2` 会按其参数配置输出点云地图，常见输出目录在：

- `src/FAST-LIVO2-ROS2/Log/PCD/`

### 2. 二维地图保存

当前地图保存主入口：

- `launch/save_projected_map.launch.py`

推荐启动：

```bash
source "/opt/ros/${ROS_DISTRO}/setup.bash"
source "${WS_ROOT}/install/setup.bash"

ros2 launch mid360_nav_demo save_projected_map.launch.py \
  map_prefix:="${HOME}/maps/example_site"
```

这条链路会调用 `nav2_map_server map_saver_cli`，把 `/projected_map` 保存为：

- `example_site.pgm`
- `example_site.yaml`

### 3. 在线重定位与原始导航链

当前原始导航主入口：

- `launch/online_nav_demo.launch.py`

推荐启动：

```bash
source "/opt/ros/${ROS_DISTRO}/setup.bash"
source "${WS_ROOT}/install/setup.bash"

ros2 launch mid360_nav_demo online_nav_demo.launch.py \
  map:="${WS_ROOT}/src/mid360_nav_demo/maps/example_site.yaml" \
  global_map_pcd:="${WS_ROOT}/src/FAST-LIVO2-ROS2/Log/PCD/all_downsampled_points.pcd"
```

这条链路通常会启动：

- `livox_ros_driver2`
- `FAST-LIVO2`
- `icp_relocalizer_node`
- `Nav2`
- 可选 RViz
- 可选底盘桥接

其中：

- `FAST-LIVO2` 负责在线里程计与配准点云
- ICP 重定位负责建立 `map -> odom`
- `Nav2` 负责规划和控制输出

### 4. 可选底盘输出

如果只是验证导航链，可以先不开底盘输出。

如果要把导航速度继续送到底盘桥接层，可以启用：

```bash
ros2 launch mid360_nav_demo online_nav_demo.launch.py \
  launch_cmd_bridge:=true \
  launch_chassis:=true
```

### 5. 仿真链路

当前包也保留了一套 MID360 仿真建图链，便于没有实机时做基础冒烟验证。

主入口：

- `launch/sim_mapping_demo.launch.py`

如果本机已经准备好相关仿真工作区，可按需 source 后再启动这一条链路。

## 当前链路中的关键 TF

当前这套 demo 默认假设：

- `FAST-LIVO2` 发布 `odom -> livox_frame`
- ICP 重定位发布 `map -> odom`

因此当前导航主链重点依赖：

```text
map -> odom -> livox_frame
```

如果后续底盘侧提供稳定的 `base_link`，则可以再把跟踪坐标系切换到 `base_link`。

## 与总控 GUI 的关系

这个包本身提供“建图、保存、重定位、导航”的业务能力，而总控 GUI 主要通过以下入口调用它：

- `online_mapping_demo.launch.py`
- `save_projected_map.launch.py`
- `online_nav_demo.launch.py`

也就是说：

- `mid360_nav_demo` 负责底层业务
- `agt_nav_console` 负责流程组织、上层控制和安全链补充

## 关键文件

- `launch/online_mapping_demo.launch.py`
  在线建图入口
- `launch/save_projected_map.launch.py`
  二维地图保存入口
- `launch/online_nav_demo.launch.py`
  原始导航链入口
- `launch/icp_relocalizer.launch.py`
  ICP 重定位单独入口
- `config/icp_relocalizer.yaml`
  ICP 重定位参数
- `maps/`
  当前保存的二维导航地图目录

## 推荐使用方式

### 1. 只做建图与地图导出

适合首次采图、重建地图、生成导航用地图：

1. 启动 `online_mapping_demo.launch.py`
2. 完成现场建图
3. 调用 `save_projected_map.launch.py`
4. 导出或整理 `.pcd` 地图

### 2. 只做原始导航链验证

适合不经过总控 GUI，先验证定位、TF 和 Nav2 是否正常：

1. 准备 `map yaml`
2. 准备 `global_map_pcd`
3. 启动 `online_nav_demo.launch.py`
4. 在 RViz 或 Qt GUI 中设置初始位姿并下发目标点

### 3. 与总控 GUI 配合使用

如果你现在的主工作流是总控 GUI，那么这个包通常不需要单独直接操作，而是作为下层被调用：

- 建图阶段由总控 GUI 拉起 `online_mapping_demo`
- 保存阶段由总控 GUI 拉起 `save_projected_map`
- 导航阶段由总控 GUI 或安全链拉起 `online_nav_demo`

## 迁移与二开提示

后续迁移和二次开发时，建议优先注意：

- 地图和点云路径尽量通过 launch 参数传入
- 不要继续把本机绝对路径写回源码
- 地图目录和运行时数据目录尽量与源码分离
- TF、topic、tracking frame 的调整优先走参数化方式

## 参考文档

- [README.md](/home/yangxuan/ros2_ws/README.md:1)
- [导航测试流程.md](/home/yangxuan/ros2_ws/导航测试流程.md:1)
- [迁移与二开整改清单.md](/home/yangxuan/ros2_ws/迁移与二开整改清单.md:1)
