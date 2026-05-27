# jie_3d_nav

[English](./README.en.md)

一套基于 ROS 2 Humble 的 3D 导航系统，通过 Web 界面交互。本系统已在智元科技 D1 机器狗以及留形科技 Odin 1 空间定位模组上测试通过。

> 迁移说明
>
> 当前仓库仍作为 `jie_3d_nav` 子模块代码与历史记录的承载仓库保留。
> 后续开发将逐步迁移到统一维护的 `ros2_ws` 总工作区仓库中，届时 `jie_3d_nav`、`FAST-LIVO2-ROS2`、`livox_ros_driver2`、`Livox-SDK2`、`rpg_vikit_ros2_fisheye` 等相关源码将以平级目录方式统一管理。
> 在新的总仓库完成公开与稳定切换前，本仓库中的说明和导航入口仍然有效。

本目录包含三个 ROS 2 包：

- `jie_map_msgs`：地图包保存、加载、导出等自定义服务接口。
- `jie_octomap`：OctoMap 管理包，负责多种地图格式导入、地图包保存/加载、OctoMap 可视化和编辑。
- `octo_planner`：基于 OctoMap 的 3D 路径规划、路径跟踪控制和 Web 测试/导航 launch。

## 功能概览

- 将 PCD 点云地图导入为 OctoMap。
- 将 ROS 2D 栅格地图导入为 3D OctoMap。
- 将 Gazebo `.world` / `.sdf` 场景转换为 OctoMap。
- 保存、加载 OctoMap 地图包。
- 使用 Qt/VTK GUI 查看和编辑 OctoMap 栅格。
- 使用 Web 页面查看 OctoMap、选择起点/终点并进行路径规划。
- 提供面向安装了留形科技 Odin 1 的 智元 D1 机器狗的导航入口和独立网页测试入口。

## 介绍视频

- Bilibili：[【开源】基于ROS2的3D导航系统](https://www.bilibili.com/video/BV1jgR9BmELw)
- YouTube：[【开源】基于ROS2的3D导航系统](https://www.youtube.com/watch?v=CepO90mzIeI)

## 目录结构

```text
jie_3d_nav/
├── jie_map_msgs/        # 自定义 srv 接口
├── jie_octomap/         # OctoMap 导入、管理、编辑、Web/GUI 工具
├── octo_planner/        # 3D 路径规划、控制器、导航 launch
├── jie_octomap/worlds/  # 示例 Gazebo world
└── install_deps_humble.sh
```

## 二次开发目标与任务约束

当前仓库已从原始上游代码独立出来，后续开发目标不是复刻智元科技 D1 / Odin 1 的整套环境，而是：

- 充分复用本仓库现有的 Qt / Web GUI、OctoMap 管理能力和 3D 路径可视化能力。
- 基于 3D 点云地图和 3D 点云重定位，构建一套交互性强、便于调试和二次开发的导航系统。
- 先完成“地图加载 -> 交互设点 -> 3D 路径规划 -> 路径显示 -> 控制指令桥接”的最小闭环，再逐步增加真实重定位、底盘闭环和避障能力。

当前阶段的明确约束如下：

- 优先保留并利用现有 `jie_octomap` GUI / Web 交互能力，不先推翻重写前端或地图编辑流程。
- 优先保留现有 `jie_path_node` 的 3D 路径规划输出接口 `/planned_path`，避免过早改动规划器核心逻辑。
- 当前底盘通讯以工作区内 `MK-mini-ros2/` 为准，后续新增桥接节点时优先适配其 `ctrl_cmd` 接口。
- 当前不优先处理车体 `base_link` 与激光雷达安装外参，早期验证阶段先直接使用激光雷达坐标系作为导航跟踪坐标系。
- 当前不纳入动态避障、局部避障、全局任务编排等扩展需求，先把点云重定位与路径执行主链跑通。
- 每一步改造必须尽量小、可回滚、可独立验证，避免在单次改动中同时引入“新定位 + 新控制 + 新任务层”三类变化。

## 许可与引用说明

本仓库目前三个 ROS 2 包的 `package.xml` 均声明为 `MIT` 许可：

- `jie_map_msgs/package.xml`
- `jie_octomap/package.xml`
- `octo_planner/package.xml`

本仓库的二次开发来源于原始项目：

- 上游仓库：<https://github.com/6-robot/jie_3d_nav>

后续继续分发、开源或闭源集成时，建议至少保留以下信息：

- 原始项目来源链接与作者归属说明。
- 当前包级别的 `MIT` 许可声明。
- 仓库内已 vendored 的第三方前端文件许可头，例如 `jie_octomap/web/vendor/three.module.js` 顶部保留的上游许可证信息。

说明：本 README 当前先补充“许可引用与来源说明”；如果后续需要公开发布此独立仓库，建议再在仓库根目录补充正式的 `LICENSE` 文件，并统一整理第三方依赖清单。

## 当前改造主线

为避免二次开发失控，当前主线固定为：

1. 保留 `jie_octomap` 地图导入、地图包管理、Web / Qt GUI 和 `/planned_path` 可视化链路。
2. 新建与 D1 / Odin 1 解耦的导航入口 `octo_planner/launch/my_robot_nav.launch.py`。
3. 接入 `MID360 + FAST-LIO2` 一类 3D 里程计，先解决 `odom -> lidar_frame`。
4. 接入 3D 点云重定位，解决 `map -> odom`，让 GUI 中的机器人位姿与地图对齐。
5. 新增 `/cmd_vel -> MK-mini ctrl_cmd` 桥接节点，打通到底盘控制链路。
6. 在低速环境下完成路径跟踪闭环。
7. 最后再补车体 TF、动态避障、复杂任务编排。

不在当前主线中的内容：

- 先行重构为 Nav2 全家桶。
- 先行引入复杂行为树任务系统。
- 在定位尚未稳定前就同时推进避障、底盘动力学、任务调度三条线。

## 即将参考的代码仓库与文档

下面这些仓库是当前阶段预计重点参考的外部实现，选择它们的原则是：优先贴近 `MID360`、ROS 2、点云重定位和小步集成。

- `FAST_LIO`
  用途：提供 LiDAR-Inertial Odometry 主体算法思路与实现基线。
  链接：<https://github.com/hku-mars/FAST_LIO>
- `livox_ros_driver2`
  用途：作为 `MID360` 官方 ROS 驱动入口，先打通点云和 IMU 数据流。
  链接：<https://github.com/Livox-SDK/livox_ros_driver2>
- `lidar_localization_ros2`
  用途：作为 ROS 2 环境下 3D 点云重定位 / scan-to-map 的首选参考实现。
  链接：<https://github.com/rsasaki0109/lidar_localization_ros2>
- `hdl_localization`
  用途：作为经典 3D LiDAR 定位思路参考，用于对照 scan matching / registration 路线。
  链接：<https://github.com/koide3/hdl_localization>
- 工作区内 `MK-mini-ros2`
  用途：底盘控制与反馈接口来源，后续桥接节点直接参考其 `yhs_can_interfaces/msg/CtrlCmd.msg` 和 `yhs_can_control` 实现。

这些参考仓库在当前项目中的角色约束如下：

- `FAST_LIO` / `livox_ros_driver2` 用于补定位与传感器链，不直接替换现有 GUI / 规划层。
- `lidar_localization_ros2` / `hdl_localization` 用于补重定位，不直接替换现有 `jie_path_node`。
- `MK-mini-ros2` 用于补底盘执行链，不直接修改 GUI 和地图管理逻辑。

## 分阶段改造计划

下面的计划以“每一步都能验证”为原则组织，优先跑通主链，再逐步加能力。

### 阶段 0：仓库收敛与统一入口

目标：

- 将当前仓库作为独立工程维护。
- 使用 `my_robot_nav.launch.py` 作为后续通用入口。

当前状态：

- 已完成 `jie_3d_nav` 独立 git 初始化。
- 已新增 `octo_planner/launch/my_robot_nav.launch.py` 作为去 D1 / Odin 1 绑定的骨架入口。

验证方式：

- `python3 -m py_compile octo_planner/launch/my_robot_nav.launch.py`

### 阶段 1：仅验证 GUI / 地图 / 规划链路

目标：

- 不接真实定位，不接底盘，仅验证地图显示、交互设点和 `/planned_path` 输出。

建议做法：

- 使用 `my_robot_nav.launch.py`，临时开启假定位 TF。
- 加载已有地图包或通过 GUI 导入 PCD / 栅格地图。

验证项：

- Web 页面可打开。
- 可以交互设置起点和终点。
- `/planned_path` 正常输出。
- GUI / Web 能稳定显示规划路径。

### 阶段 2：接入 MID360 原始数据链

目标：

- 跑通 `livox_ros_driver2`，稳定获得点云与 IMU 数据。

约束：

- 这一步只解决传感器数据链，不改规划器和控制器。

验证项：

- 点云与 IMU 话题稳定。
- 激光雷达坐标系命名固定下来，后续先以该 frame 作为导航跟踪坐标系。

### 阶段 3：接入 FAST-LIO2 / LIO 里程计

目标：

- 稳定提供 `odom -> lidar_frame`。

约束：

- 暂不要求全局重定位。
- 暂不要求车体 `base_link` 外参。

验证项：

- 里程计连续。
- `d1_controller` 或后续控制链能读取该跟踪 frame。

### 阶段 4：接入 3D 点云重定位

目标：

- 提供 `map -> odom`，让机器人位姿真正落到全局地图上。

优先参考：

- `lidar_localization_ros2`
- `hdl_localization`

验证项：

- Web 中“已定位”状态正常。
- 机器人当前位姿、地图、路径规划在同一全局坐标系下。

## MID360 + FAST-LIVO2 + lidar_localization_ros2 联调准备

当前工作区已经接入一条最小可运行链路：

- `livox_ros_driver2` 提供 MID360 原始数据。
- `FAST-LIVO2-ROS2` 提供 `odom -> livox_frame` 和 `/cloud_registered`。
- `lidar_localization_ros2` 消费 `/cloud_registered`，发布 `map -> odom`。
- `my_robot_nav.launch.py` 作为统一入口，负责把定位、重定位、地图、规划和可视化串起来。

当前第一版约束：

- 先使用 `livox_frame` 作为 `base_frame`。
- 先使用 `FAST-LIVO2` 输出的 `/cloud_registered` 做 scan-to-map。
- 先关闭 `lidar_localization_ros2` 的 IMU 预积分，避免与 `FAST-LIVO2` 的 IMU 融合重复叠加。
- 地图文件建议单独放在仓库外部目录，运行时通过绝对路径传入 `lidar_localization_map_path`。

已新增的关键文件：

- `octo_planner/config/lidar_localization_mid360_fastlivo.yaml`
- `octo_planner/launch/mid360_relocalization.launch.py`
- `octo_planner/launch/my_robot_nav.launch.py`

### 推荐启动顺序

1. 先编译并加载工作区环境：

```bash
cd /home/yangxuan/ros2_ws/src
colcon build --symlink-install
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_LOG_DIR=/tmp/ros_logs
```

2. 准备一份用于重定位的全局点云地图，例如：

```text
/data/maps/site_a/site_a_global_map.pcd
```

3. 启动整套链路：

```bash
ros2 launch octo_planner my_robot_nav.launch.py \
  launch_livox_driver:=true \
  launch_fastlivo:=true \
  launch_lidar_localization:=true \
  publish_static_odom_to_base:=false \
  base_frame:=livox_frame \
  lidar_localization_map_path:=/data/maps/site_a/site_a_global_map.pcd
```

4. 如果已知机器人初始位姿，再补充初始位姿参数：

```bash
ros2 launch octo_planner my_robot_nav.launch.py \
  launch_livox_driver:=true \
  launch_fastlivo:=true \
  launch_lidar_localization:=true \
  publish_static_odom_to_base:=false \
  base_frame:=livox_frame \
  lidar_localization_map_path:=/data/maps/site_a/site_a_global_map.pcd \
  lidar_localization_set_initial_pose:=true \
  lidar_localization_initial_pose_x:=0.0 \
  lidar_localization_initial_pose_y:=0.0 \
  lidar_localization_initial_pose_z:=0.0 \
  lidar_localization_initial_pose_qx:=0.0 \
  lidar_localization_initial_pose_qy:=0.0 \
  lidar_localization_initial_pose_qz:=0.0 \
  lidar_localization_initial_pose_qw:=1.0
```

### 联调时优先检查的 topic

- `/livox/imu`
- `/livox/lidar`
- `/cloud_registered`
- `/localization/pose`
- `/tf`
- `/tf_static`

推荐检查命令：

```bash
ros2 topic list | sort
ros2 topic hz /cloud_registered
ros2 topic echo /localization/pose --once
```

### 联调时优先检查的 TF

理想 TF 链应为：

```text
map -> odom -> livox_frame
```

推荐检查命令：

```bash
ros2 run tf2_ros tf2_echo odom livox_frame
ros2 run tf2_ros tf2_echo map odom
ros2 run tf2_ros tf2_echo map livox_frame
```

判断标准：

- `odom -> livox_frame` 持续变化，说明 `FAST-LIVO2` 里程计正常。
- `map -> odom` 存在且较稳定，说明重定位链路已经接管全局配准。
- `map -> livox_frame` 连续变化且与机器人真实运动一致，说明全链路基本打通。

### 这版联调最容易卡住的点

- `lidar_localization_map_path` 为空或路径错误，重定位节点会启动但无法真正匹配地图。
- `base_frame` 不是 `livox_frame`，而 TF 中又没有对应变换，会导致重定位无法正确取姿态。
- `FAST-LIVO2` 没有稳定输出 `/cloud_registered`，重定位节点会一直等输入点云。
- 地图坐标系与建图时使用的里程计坐标系差异过大，未设置初始位姿时可能长时间无法收敛。
- 若后续切回原始点云而不是 `/cloud_registered`，需要重新检查去畸变、时间同步和点云 frame 命名。

### 初始位姿的几种方式与差别

当前这版文档里给出的初始位姿参数：

- `lidar_localization_set_initial_pose`
- `lidar_localization_initial_pose_x/y/z/qx/qy/qz/qw`

本质上是“启动时给一个固定 seed”，不是算法只能写死，而是为了先把第一版链路稳定跑通。

常见做法可以分成三类：

- 启动参数写死
  适合已知起点、重复测试和录包回放。优点是最稳、最容易复现。缺点是每次换场地或换起点都要改参数。
- RViz 手动给初始位姿
  适合现场调试。`lidar_localization_ros2` 本身支持从 `/initialpose` 接收 `geometry_msgs/msg/PoseWithCovarianceStamped`，也就是可以走 RViz 里的 `2D Pose Estimate` / `SetInitialPose` 这类工具来人工给 seed。它和启动参数的本质差别不大，都是“给一个初值后再局部配准”，只是 RViz 更灵活，不用重启节点。
- 自动全局配准
  这类方案通常不是单纯的局部 NDT/GICP，而是先做全局搜索、回环候选检索、描述子匹配或多初值尝试，再把结果交给局部配准细化。优点是更自动，缺点是计算量更大、误匹配风险更高、参数和场景依赖更强。

对你现在这套 `MID360 + FAST-LIVO2 + lidar_localization_ros2`，我建议分两步走：

- 当前阶段先保留“启动参数 seed + 必要时 RViz 手动修正”。
- 等现场链路稳定后，再考虑补自动全局初始化或失败后自动重定位。

也就是说，当前方案并不是不能从 RViz 给位姿，而是我先把最稳的入口参数接好了。后面如果你想要，我可以再帮你把 RViz 初始位姿这条交互链单独接顺。

### FAST-LIVO2 建图并导出全局点云地图

`FAST-LIVO2` 这边已经具备建图和导出点云地图的能力。当前配置文件是：

- `FAST-LIVO2-ROS2/config/mid360_lio_only.yaml`

里面现在的相关配置是：

```yaml
pcd_save:
  pcd_save_en: false
  colmap_output_en: false
  filter_size_pcd: 0.15
  interval: -1
```

含义可以先这样理解：

- `pcd_save_en: true`
  开启 PCD 保存。
- `filter_size_pcd`
  导出前对地图点云做体素滤波，值越大文件越小、细节越少。
- `interval`
  保存间隔控制。通常 `-1` 表示结束时统一输出，具体行为以上游实现为准。

推荐流程：

1. 先把 `pcd_save_en` 改成 `true`。
2. 单独启动 `FAST-LIVO2` 做建图，不急着开重定位。
3. 手动走完整个目标区域，尽量闭环、多方向覆盖。
4. 正常结束节点后，到 `FAST-LIVO2` 的输出目录确认导出的地图文件。
5. 对导出的地图做一次体素降采样或裁剪，得到更适合作为重定位输入的全局 `.pcd`。
6. 把这个 `.pcd` 通过 `lidar_localization_map_path:=/absolute/path/to/map.pcd` 喂给重定位链。

建议把“建图用原始大地图”和“重定位用精简地图”分开保存：

- 建图原始图：尽量完整保留
- 重定位运行图：适当裁剪、降采样、只保留主要可观测结构

这样运行时会更稳，也更省内存和匹配时间。

### 连车前的底盘准备

如果要真正连上车体，除了定位和规划链路，还需要先把 CAN 和底盘驱动准备好。

推荐顺序：

1. 激活 `can0`：

```bash
sudo ip link set can0 up type can bitrate 500000
```

2. 加载工作区环境：

```bash
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source install/setup.bash
```

3. 启动底盘驱动：

```bash
ros2 launch yhs_can_control yhs_can_control.launch.py
```

4. 再启动导航主链，或者先单独测试 `/ctrl_cmd` 是否能被底盘侧接收。

当前底盘相关默认约定：

- CAN 设备名默认是 `can0`
- `yhs_can_control` 默认订阅 `/ctrl_cmd`
- `octo_planner` 里的桥接节点负责把 `/cmd_vel` 转成 `yhs_can_interfaces/msg/CtrlCmd`

如果后面要做整套实车 bringup，推荐拆成三个终端：

- 终端 1：`yhs_can_control`
- 终端 2：`my_robot_nav.launch.py`
- 终端 3：`ros2 topic echo /ctrl_cmd`、`ros2 topic echo /cmd_vel`、`ros2 run tf2_ros tf2_echo map livox_frame` 做观测

### 阶段 5：新增底盘桥接节点

目标：

- 将控制器输出的 `/cmd_vel` 转换为 `MK-mini-ros2` 需要的 `ctrl_cmd`。

约束：

- 先只做桥接，不改底盘底层驱动。
- 先不处理复杂动力学补偿。

验证项：

- `/cmd_vel` 到 `/ctrl_cmd` 的转换链路可单独测试。
- `yhs_can_control` 能接收到预期控制指令。

### 阶段 6：低速路径跟踪闭环

目标：

- 在低速、空旷、可控环境下完成点到点路径执行。

约束：

- 先不追求复杂地形、狭窄通道和高动态场景。

验证项：

- 能从 GUI / Web 发起导航。
- 机器人能沿 `/planned_path` 行进并停止在终点附近。

### 阶段 7：补充车体 TF、避障与任务层

目标：

- 在主链稳定后，再补车体坐标外参、局部避障和复杂任务系统。

这部分明确后置，不在当前最小落地主线中优先推进。

## 环境要求

- Ubuntu 22.04
- ROS 2 Humble
- `colcon`
- OctoMap / octomap_msgs
- OpenCV
- Open3D C++ 开发库
- PyQt5、VTK、NumPy、Pillow、PyYAML
- 可选：`rosbridge_server`，用于 Web 页面通过 websocket 访问 ROS

### ROS 2 Foxy 复现说明

本项目主要面向 Ubuntu 22.04 / ROS 2 Humble。Ubuntu 20.04 / ROS 2 Foxy 可用于验证核心链路（Gazebo world 或 PCD 地图导入为 OctoMap，再进行 3D 路径规划），但需要额外注意：

- 安装 Foxy 的 Python 点云工具包：`sudo apt-get install ros-foxy-sensor-msgs-py`。
- Ubuntu 20.04 默认提供 `python3-vtk7`，其 Qt 入口是 `vtk.qt.QVTKRenderWindowInteractor`；较新的 VTK 使用 `vtkmodules.qt.QVTKRenderWindowInteractor`。
- 如果 Open3D C++ 安装在系统路径之外，编译时需要通过 `Open3D_DIR` 或 `CMAKE_PREFIX_PATH` 指向 `Open3DConfig.cmake`。
- 如果运行 `pcd_to_octomap_node` 时出现 `libtbb.so.12: cannot open shared object file`，需要把 Open3D 安装目录下的 `lib/` 加入运行库路径，例如：

```bash
export LD_LIBRARY_PATH=/path/to/open3d_install/lib:${LD_LIBRARY_PATH}
```

基础编译不需要以下两个包：

- `d1_bringup`
- `d1_description`

注意：完整智元科技 D1 机器狗导航入口 `octo_planner/launch/nav.launch.py` 仍然会在运行时使用 `d1_bringup` 和 `d1_description`，因为它会启动 `d1_core` 并读取智元科技 D1 机器狗的 URDF。

## 安装依赖

可以使用仓库内脚本安装常用依赖：

```bash
cd ~/ros2_ws/src/jie_3d_nav
bash install_deps_humble.sh
```

如果 CMake 找不到 Open3D，需要额外安装 Open3D C++ 开发库，并确保 `Open3DConfig.cmake` 能被 CMake 找到，例如通过 `Open3D_DIR` 或 `CMAKE_PREFIX_PATH` 指定。

## 推荐隔离环境启动方式

`jie_octomap` 除了 ROS 2 / apt 依赖外，还会使用 `open3d`、`numpy`、`scipy`、`scikit-learn` 等 Python 包。若这些包同时混用了系统 Python、`~/.local` 下的 `pip install --user` 包和 ROS 环境，容易出现类似下面的兼容性问题：

- `A NumPy version >=1.17.3 and <1.25.0 is required for this version of SciPy`
- `AttributeError: _ARRAY_API not found`
- `ImportError: numpy.core.multiarray failed to import`

推荐做法是：ROS 2、apt 和 `colcon` 继续使用系统环境；仅把 Python 侧的 `open3d` 相关依赖放进单独的虚拟环境中，并在启动前禁用用户目录 `site-packages`。

### 1. 创建虚拟环境

在 ROS 2 工作区根目录创建带 `system-site-packages` 的 venv，这样仍然可以复用系统里通过 apt 安装的 ROS Python 包：

```bash
cd ~/ros2_ws
python3 -m venv --system-site-packages .venv-jie3d
source .venv-jie3d/bin/activate
export PYTHONNOUSERSITE=1
python -m pip install -U pip
python -m pip install --no-cache-dir \
  "numpy<1.25" \
  "scikit-learn<1.4" \
  "scipy<1.16" \
  "open3d==0.19.0"
```

如果之前已经创建过一个装乱的 `.venv-jie3d`，建议直接删除后重建：

```bash
cd ~/ros2_ws
deactivate 2>/dev/null || true
rm -rf .venv-jie3d
```

### 2. 验证 Python 包来源

确认关键包已经从 venv 中导入，而不是继续读到 `~/.local/lib/python3.10/site-packages`：

```bash
cd ~/ros2_ws
source .venv-jie3d/bin/activate
export PYTHONNOUSERSITE=1
python - <<'PY'
import numpy, scipy, sklearn, open3d, sys
print(sys.executable)
print("numpy:", numpy.__version__, numpy.__file__)
print("scipy:", scipy.__version__, scipy.__file__)
print("sklearn:", sklearn.__version__, sklearn.__file__)
print("open3d:", open3d.__version__, open3d.__file__)
PY
```

正常情况下，上述路径应位于 `~/ros2_ws/.venv-jie3d/...`。

### 3. 首次构建或源码变更后再编译

```bash
cd ~/ros2_ws
source .venv-jie3d/bin/activate
export PYTHONNOUSERSITE=1
source /opt/ros/humble/setup.bash
colcon build --packages-select jie_map_msgs jie_octomap octo_planner
source install/setup.bash
```

只有在以下情况之一发生时，才需要重新执行 `colcon build`：

- 第一次搭建这个工作区。
- 修改了 `jie_map_msgs`、`jie_octomap`、`octo_planner` 的源码、`launch`、`CMakeLists.txt`、`package.xml` 等内容。
- 新增或调整了依赖，或清理过 `build/`、`install/`、`log/`。

### 4. 日常启动已编译好的工作区

如果工作区已经成功编译过，且期间没有发生上述变更，日常启动通常只需要重新 `source` 环境：

```bash
cd ~/ros2_ws
source .venv-jie3d/bin/activate
export PYTHONNOUSERSITE=1
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch jie_octomap import_pcd_map.launch.py
```

之后运行 `import_ros_map.launch.py`、`import_gazebo_world.launch.py`、`octomap_test.launch.py` 等依赖 `jie_octomap` Python GUI 的命令时，也建议沿用同一套启动方式。

## 编译

从 ROS 2 工作区根目录编译。不要在源码包目录 `src/jie_3d_nav` 内直接执行 `colcon build`，否则会在源码目录下生成多余的 `build/`、`install/`、`log/`：

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select jie_map_msgs jie_octomap octo_planner
source install/setup.bash
```

如果 Open3D C++ 不在默认 CMake 搜索路径中：

```bash
colcon build --packages-select jie_map_msgs jie_octomap octo_planner \
  --cmake-args -DOpen3D_DIR=/path/to/open3d_install/lib/cmake/Open3D
```

如果源码目录移动过，旧 CMake 缓存可能还指向旧路径，可以清理缓存后重编：

```bash
colcon build --packages-select jie_map_msgs jie_octomap octo_planner --cmake-clean-cache
```

如果误在源码包目录内编译过，可以删除源码目录下被 `.gitignore` 忽略的临时产物：

```bash
rm -rf build install log
```

## 快速体验

运行如下指令加载例子地图：

```bash
ros2 launch jie_octomap import_gazebo_world.launch.py world_name:=2_storey.world
```

在弹出的窗口中，加载gazebo的world文件，设置地图的截取边长，点击加载按钮即可将world文件转换成OctoMap，并显示在窗口中。

<p align="center">
  <img src="./media/2.png" alt="加载地图" width="600">
</p>

先点击“起始点”按钮，用鼠标在地图上设置起始点位置。再点击“目标点”按钮，用鼠标在地图上设置目标点位置，即可规划出可行的路径。

<p align="center">
  <img src="./media/3.png" alt="规划路径" width="600">
</p>

## 地图导入

### 导入 PCD 点云地图

```bash
ros2 launch jie_octomap import_pcd_map.launch.py
```

该 launch 会启动：

- `pcd_to_octomap_node`
- `octomap_to_occupied_markers_node`
- `map_package_manager`
- `pcd_map_import_gui`
- `octo_planner/jie_path_node`

`pcd_map_import_gui` 支持读取 PCD 后在左侧预览点云，并在转换前做常用清理：

- `推荐转换参数`：根据当前点云的点间距、点数和地图范围，自动填入 OctoMap 分辨率、每体素最少点数和最小连通体素数。
- `预处理降采样(m)`：读取 PCD 时对 GUI 工作点云进行体素降采样。修改该值后需要重新选择/读取 PCD 才会应用到当前点云。
- `启用选区方块`：显示可移动选区方块，`W/S`、`A/D`、`Q/E` 分别沿 X/Y/Z 移动。
- `抹除框内点云`：删除选区方块内的点。
- `仅保留框内点云`：保留选区方块内的点，移除外部点，适合从大范围点云中裁剪出待转换区域。

稀疏或大范围 PCD 建议先点击 `推荐转换参数`，再转换为 OctoMap。转换后重点观察终端日志中的 `kept_voxels`、`occupied_voxels`：

- `kept_voxels` 只有几十或几百，通常表示分辨率过细或 `每体素最少点数` 过高。
- `kept_voxels` 特别大，通常表示分辨率过细或裁剪范围过大，Web/Qt 显示和规划会变慢。
- 稀疏点云的起步配置通常使用 `每体素最少点数=1`、`最小连通体素数=1`。

转换成功时，终端应看到类似日志：

```text
Loaded PCD file: ... source_points=... kept_voxels=... occupied_voxels=...
Preprocess mask rebuilt...
Preblocked costmap rebuilt...
```

保存地图包时，GUI 默认根目录为当前用户的 `~/maps`。如果手动选择保存目录，确保该目录属于当前用户并可写，不要使用只适用于作者机器人环境的 `/home/robot/maps`。

如果 GUI 右侧没有显示转换后的 OctoMap，或保存地图包时提示 `not ready` / `octomap not ready`，优先检查终端中 `pcd_to_octomap_node` 是否已经退出。常见原因是 Open3D 依赖的运行库没有被动态链接器找到，例如：

```text
error while loading shared libraries: libtbb.so.12: cannot open shared object file
```

这时先确认依赖是否可见：

```bash
ldd install/jie_octomap/lib/jie_octomap/pcd_to_octomap_node | grep -E "not found|tbb"
```

如果 `libtbb.so.12` 未找到，把 Open3D 安装目录下的 `lib/` 加入 `LD_LIBRARY_PATH` 后重新启动 launch：

```bash
export LD_LIBRARY_PATH=/path/to/open3d_install/lib:${LD_LIBRARY_PATH}
ros2 launch jie_octomap import_pcd_map.launch.py
```

也可以在命令行直接覆盖转换节点的默认参数：

```bash
ros2 launch jie_octomap import_pcd_map.launch.py \
  resolution:=0.5 \
  voxel_downsample_m:=0.0 \
  min_points_per_voxel:=1 \
  min_cluster_voxels:=1
```

### 导入 ROS 2D 栅格地图

```bash
ros2 launch jie_octomap import_ros_map.launch.py
```

该 launch 会启动：

- `occupancy_grid_to_octomap_node`
- `octomap_to_occupied_markers_node`
- `map_package_manager`
- `ros_map_import_gui`
- `octo_planner/jie_path_node`

### 导入 Gazebo World / SDF

加载包内示例 world 时，推荐使用 `world_name`：

```bash
ros2 launch jie_octomap import_gazebo_world.launch.py world_name:=field.world
```

加载外部 world 文件时，继续使用绝对路径：

```bash
ros2 launch jie_octomap import_gazebo_world.launch.py world_file:=/absolute/path/to/map.world
```

如果同时传入 `world_file` 和 `world_name`，优先使用 `world_file`。

`jie_octomap/worlds/` 目录内提供了两个示例 world 文件，并会随 `jie_octomap` 包安装到 `share/jie_octomap/worlds/`：

- `2_storey.world`：双层建筑/楼层示例。
- `field.world`：场地示例。

加载双层建筑示例：

```bash
ros2 launch jie_octomap import_gazebo_world.launch.py world_name:=2_storey.world
```

加载场地示例：

```bash
ros2 launch jie_octomap import_gazebo_world.launch.py world_name:=field.world
```

该 launch 会启动：

- `world_to_octomap_node`
- `world_selector_gui.py`
- `map_package_manager`
- `octo_planner/jie_path_node`

## 地图管理与编辑

OctoMap 管理和编辑主入口：

```bash
ros2 launch jie_octomap map_manager.launch.py
```

该 launch 会启动：

- `map_package_manager`
- `octomap_to_occupied_markers_node`
- `map_viewer_gui`
- 可选 `octo_planner/jie_path_node`

`map_viewer_gui` 支持：

- 打开地图包
- 刷新地图
- 保存地图
- 查看占据、禁行、可通行、风险代价图层
- 编辑栅格：`occupied`、`preblocked`、`traversable`、`clear`
- 选择起点、终点、导航目标

## Web 可视化

### 加载地图并启动 Web 页面

```bash
ros2 launch jie_octomap web_octomap.launch.py map_package:=~/maps/map
```

常用参数：

- `map_package`：已保存的地图包目录。
- `http_port`：静态 Web 服务端口，默认 `8080`。
- `launch_rosbridge`：是否启动 `rosbridge_websocket`。
- `launch_map_gui`：是否同时启动 Qt 保存/加载窗口。

如果 `8080` 已被占用，会出现 `OSError: [Errno 98] Address already in use`。这不是实机或机器人 IP 问题，换一个端口即可：

```bash
ros2 launch jie_octomap web_octomap.launch.py \
  map_package:=~/maps/map \
  http_port:=8081
```

如果需要网页与 ROS 通信，启动 `rosbridge_websocket`：

```bash
ros2 launch jie_octomap web_octomap.launch.py \
  map_package:=~/maps/map \
  http_port:=8081 \
  launch_rosbridge:=true
```

如果系统未安装 rosbridge：

```bash
sudo apt install ros-${ROS_DISTRO}-rosbridge-server
```

浏览器访问：

```text
http://localhost:8081
```

如果从另一台设备访问，使用运行该 launch 的电脑 IP，例如 `http://<电脑IP>:8081`。只有 Web 服务运行在机器人上时才使用机器人 IP。

### Web 功能测试

```bash
ros2 launch octo_planner web_test.launch.py
```

`web_test.launch.py` 用于测试网页访问、地图显示、Web 起终点选择、路径规划和基础控制链路。该 launch 已去除对 `d1_bringup` 和 `d1_description` 的依赖，会使用一个最小 `base_link` URDF 启动 `robot_state_publisher`。

启动前同样需要根据实际环境配置：

```text
octo_planner/config/nav_params.yaml
```

至少需要部署好：

- `relocalization_bin_file`：重定位使用的 `.bin` 地图文件。
- `map_package_dir`：已经保存好的 OctoMap 地图包目录。

## 智元科技 D1 机器狗完整导航

完整机器人导航入口：

```bash
ros2 launch octo_planner nav.launch.py
```

该 launch 面向智元科技 D1 机器狗实际导航，并结合留形科技 Odin 1 空间定位模组相关驱动流程，会启动或使用：

- `d1_bringup/d1_core`
- `d1_description/urdf/d1.urdf`
- `odin_ros_driver`
- `octo_planner/jie_path_node`
- `octo_planner/d1_controller`
- `jie_octomap/map_package_manager`
- Web viewer 和 `rosbridge_websocket`

运行前需要根据实际环境修改：

```text
octo_planner/config/nav_params.yaml
```

重点字段：

- `relocalization_bin_file`
- `map_package_dir`
- `relocalization_pcd_file`
- `show_rviz`
- `show_map_gui`
- `publish_d1_odom`
- `use_static_odom_to_base`

同时需要确认留形科技 Odin 1 空间定位模组驱动配置：

```text
odin_ros_driver/config/control_command.yaml
```

将其中的 `custom_map_mode` 设置为 `2`，即 `Relocalization mode`。

`octo_planner/config/nav_params.yaml` 中至少需要部署好：

- `relocalization_bin_file`：重定位使用的 `.bin` 地图文件。
- `map_package_dir`：已经保存好的 OctoMap 地图包目录。

如果需要使用 RViz 观察定位效果，还需要部署：

- `relocalization_pcd_file`：用于 RViz 显示的 `.pcd` 点云地图文件。

## 其他 Launch

```bash
ros2 launch jie_octomap octomap_test.launch.py
ros2 launch jie_octomap octomap_open3d.launch.py
ros2 launch jie_octomap odin1_slam.launch.py
ros2 launch jie_octomap odin1_loc.launch.py
```

其中 `odin1_slam.launch.py` 和 `odin1_loc.launch.py` 面向留形科技 Odin 1 空间定位模组流程，运行时需要 `odin_ros_driver`，并可选使用 `odin_costmap` 配置。

## 入门教材推荐

《机器人操作系统（ROS2）入门与实践》

<p align="center">
  <img src="./media/book_1.jpg" alt="机器人操作系统 ROS2 入门与实践" width="400">
</p>

淘宝链接：[《机器人操作系统（ROS2）入门与实践》](https://world.taobao.com/item/820988259242.htm)

## 关注公众号

欢迎关注公众号，后续会继续带来更多有意思的机器人、ROS 2 和具身智能相关开源项目。

<p align="center">
  <img src="./media/AJQR.jpg" alt="公众号二维码" width="360">
</p>
