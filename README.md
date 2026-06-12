# ros2_ws

这个工作空间面向 `ROS 2 + Livox MID360` 的在线建图、地图保存、重定位、自动导航和现场联调，当前已经形成一套以总控 GUI 为核心入口的实际可用方案。

整套系统的目标不是单独验证某一个算法包，而是把：

- `MID360` 驱动
- `FAST-LIVO2` 在线里程计与建图
- 基于全局点云地图的重定位
- `Nav2` 自动导航
- 安全速度仲裁与障碍急停
- Qt 上位机交互
- 导航测试记录与复盘

串成一条适合现场调试和后续二次开发的完整链路。

## 当前工作空间定位

当前这套工作空间已经不只是一个“算法 demo 集合”，而是一套围绕总控上位机组织起来的导航联调环境。

核心特点是：

- 以 `ros2 run agt_nav_console nav_ops_console` 作为统一入口
- 支持在线建图、地图保存、点云导出、导航启动、录制管理等关键操作
- 支持根据现场需要，在 GUI 中选择导航模式和部分关键参数
- 支持结合 Qt GUI 做初始位姿设置、目标点输入和地图交互
- 支持用 `nav_test_recorder` 对单次导航实验做留档和复盘

## 核心能力

### 1. 总控 GUI

总控 GUI 是当前工作空间最重要的使用入口，脚本位于：

- `src/agt_nav_console/scripts/nav_ops_console.py`

启动命令：

```bash
source /opt/ros/${ROS_DISTRO:-humble}/setup.bash
source /path/to/your/ros2_ws/install/setup.bash

ros2 run agt_nav_console nav_ops_console
```

当前总控 GUI 已支持：

- 启动在线建图模式
- 保存 `pgm + yaml` 二维导航地图
- 导出最新全局点云地图
- 自动回填导航所需的地图路径
- 启动 Qt 地图交互界面
- 启动导航主链
- 按需选择 `safe` 或 `raw` 导航模式
- 在线选择是否关闭动态障碍物更新
- 在线覆盖局部 / 全局膨胀半径
- 启动导航测试记录器

### 2. 在线建图与地图导出

当前建图链路基于 `MID360 + FAST-LIVO2`，主要入口为：

- `src/mid360_nav_demo/launch/online_mapping_demo.launch.py`

建图阶段可配合总控 GUI 完成：

- 启动在线建图
- 观察建图结果
- 保存二维投影地图
- 导出后续重定位所需的 `.pcd` 地图

### 3. 重定位与自动导航

当前导航主链支持：

- `FAST-LIVO2` 提供运行时里程计与配准点云
- ICP 重定位提供 `map -> odom`
- `Nav2` 提供路径规划与控制输出
- 安全链对导航速度、手动速度和障碍急停进行仲裁
- 底盘桥接将速度指令转换为底盘控制消息

总控模式下的主入口是：

- `src/agt_nav_console/launch/safe_online_nav_demo.launch.py`

如果只想验证不带安全链的原始导航链，可使用：

- `src/mid360_nav_demo/launch/online_nav_demo.launch.py`

### 4. Qt 上位机交互

当前工作空间已经接入：

- `src/Ros_Qt5_Gui_App`

Qt GUI 主要用于：

- 地图显示
- 机器人位姿显示
- 初始位姿设置
- 目标点输入
- 路径显示
- 速度状态观察

启动脚本：

- `src/agt_nav_console/scripts/start_qt_gui.sh`

### 5. 导航测试记录与复盘

工作空间内已经集成导航测试记录工具，主要脚本包括：

- `src/agt_nav_console/scripts/nav_test_recorder.py`
- `src/agt_nav_console/scripts/analyze_nav_test.py`
- `src/agt_nav_console/scripts/offline_nav_test_feeder.py`

当前支持：

- 自动创建单次测试目录
- 自动启动 `ros2 bag record`
- 保存 `metrics.csv`
- 保存 `events.csv`
- 记录关键事件和备注
- 离线分析路径长度、到点时间、终点误差等指标

## 总体运行逻辑

当前总控 GUI 对外提供的是一套“两阶段”工作流：

### 阶段 1：建图与地图准备

1. 启动 `online_mapping_demo.launch.py`
2. 使用 `FAST-LIVO2` 在线建图
3. 保存二维地图 `pgm + yaml`
4. 导出点云地图 `.pcd`
5. 回填导航阶段要使用的地图路径

### 阶段 2：导航与测试

1. 启动 Qt GUI
2. 启动导航主链
3. 启动 `nav_test_recorder`
4. 设置初始位姿
5. 输入目标点
6. 执行自动导航
7. 记录测试事件
8. 保存并分析实验结果

总控 GUI 背后的主链路可以概括为：

```text
nav_ops_console
  -> online_mapping_demo.launch.py
  -> save_projected_map.launch.py
  -> safe_online_nav_demo.launch.py
       -> online_nav_demo.launch.py
       -> nav2_mid360.launch.py
       -> safety_guard_node
       -> obstacle_stop_demo.launch.py
       -> cmd_vel_to_ctrl_cmd_bridge
  -> start_qt_gui.sh
  -> nav_test_recorder
```

## 推荐使用方式

### 1. 环境准备

建议先约定这些变量：

```bash
export WS_ROOT=/path/to/your/ros2_ws
export ROS_DISTRO=${ROS_DISTRO:-humble}
export MAP_PATH=${MAP_PATH:-$WS_ROOT/src/mid360_nav_demo/maps/example_site.yaml}
export GLOBAL_MAP_PCD=${GLOBAL_MAP_PCD:-$WS_ROOT/src/FAST-LIVO2-ROS2/Log/PCD/all_raw_points.pcd}
export ROS_QT5_GUI_APP_DIR=${ROS_QT5_GUI_APP_DIR:-$WS_ROOT/src/Ros_Qt5_Gui_App}
export NAV_TEST_OUTPUT_ROOT=${NAV_TEST_OUTPUT_ROOT:-$WS_ROOT/nav_tests}
```

### 2. 编译工作空间

```bash
cd "${WS_ROOT}"
source "/opt/ros/${ROS_DISTRO}/setup.bash"
colcon build --symlink-install
source "${WS_ROOT}/install/setup.bash"
```

如果终端环境容易被 Conda 或虚拟环境污染，可以使用：

```bash
"${WS_ROOT}/src/agt_nav_console/scripts/build_ros_clean_env.sh" --packages-up-to agt_nav_console
```

### 3. 启动总控 GUI

```bash
cd "${WS_ROOT}"
source "/opt/ros/${ROS_DISTRO}/setup.bash"
source "${WS_ROOT}/install/setup.bash"

ros2 run agt_nav_console nav_ops_console
```

### 4. 如果临时不用总控 GUI

也可以按模块单独启动：

- 建图：`ros2 launch mid360_nav_demo online_mapping_demo.launch.py`
- 安全导航主链：`ros2 launch agt_nav_console safe_online_nav_demo.launch.py`
- 原始导航主链：`ros2 launch mid360_nav_demo online_nav_demo.launch.py`
- Qt GUI：`src/agt_nav_console/scripts/start_qt_gui.sh`
- 记录器：`ros2 run agt_nav_console nav_test_recorder --gui`

## 关键目录

- `src/agt_nav_console`
  当前总控 GUI、安全链、障碍急停、导航记录与分析工具
- `src/mid360_nav_demo`
  MID360 在线建图、地图导出、重定位与导航 demo
- `src/jie_3d_nav`
  三维导航相关代码总目录，包含 `jie_octomap` 和 `octo_planner`
- `src/Ros_Qt5_Gui_App`
  Qt 上位机工程源码
- `src/FAST-LIVO2-ROS2`
  MID360 在线里程计与建图相关代码
- `src/lidar_localization_ros2`
  点云重定位相关代码

## 当前适合的使用场景

这套工作空间当前更适合下面几类任务：

- 现场快速联调 `MID360 + 导航` 整链
- 产出可复用的二维导航地图和点云地图
- 在 Qt GUI 中完成设点与导航交互
- 对导航实验进行标准化留档
- 为后续代码迁移、平台替换和二次开发提供基础工程骨架

## 后续二开建议方向

后续如果继续围绕迁移和二次开发推进，建议优先做：

- 进一步收敛 topic / frame / service / chassis 参数到统一配置层
- 把地图、测试数据、bag、日志与源码目录彻底分离
- 补充更多“启动后自动自检”的总控能力
- 继续完善三维地图管理与三维规划交互

## 参考文档

- `导航测试流程.md`
- `迁移与二开整改清单.md`
- `src/agt_nav_console/README.md`
- `src/mid360_nav_demo/README.md`
