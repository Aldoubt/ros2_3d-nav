# agt_nav_console

`agt_nav_console` 是当前工作空间里的导航总控与上层联调包，围绕 `ROS 2 + MID360 + FAST-LIVO2 + Nav2` 这条实际使用链路，提供总控 GUI、安全仲裁、障碍急停、Qt GUI 对接和导航测试记录能力。

这个包的定位不是单独做算法，而是把现场最常用的“启动、切换、接管、记录、排障”能力集中起来，作为整套系统的上层控制入口。

## 包定位

当前 `agt_nav_console` 主要负责：

- 提供总控 GUI 入口
- 串联安全导航主链
- 管理自动导航与手动速度仲裁
- 提供障碍急停链路
- 对接外部 Qt 上位机
- 提供导航实验记录与分析工具

在整套工作空间里，它更像是“流程组织层”和“上层控制层”。

## 核心能力

### 1. 总控 GUI

总控脚本：

- `scripts/nav_ops_console.py`

启动命令：

```bash
export WS_ROOT=/path/to/your/ros2_ws
export ROS_DISTRO=${ROS_DISTRO:-humble}

source "/opt/ros/${ROS_DISTRO}/setup.bash"
source "${WS_ROOT}/install/setup.bash"

ros2 run agt_nav_console nav_ops_console
```

当前总控 GUI 已支持：

- 启动在线建图模式
- 保存 `pgm + yaml` 地图
- 导出最新全局点云地图
- 自动回填导航地图与点云路径
- 启动 Qt GUI
- 启动导航主链
- 选择 `safe` 或 `raw` 导航模式
- 关闭动态障碍物更新
- 在线覆盖局部 / 全局膨胀半径
- 启动导航记录器
- 一键停止相关进程

### 2. 安全导航主链

当前主入口：

- `launch/safe_online_nav_demo.launch.py`

这条链路会把：

- `mid360_nav_demo/online_nav_demo.launch.py`
- `Nav2`
- `safety_guard_node`
- `obstacle_stop_demo.launch.py`
- `cmd_vel_to_ctrl_cmd_bridge`

串成一条完整的安全导航链。

整体逻辑可以概括为：

```text
Nav2 /cmd_vel
  -> /agt/cmd_vel_nav
  -> safety_guard_node
  -> /cmd_vel_safe
  -> cmd_vel_to_ctrl_cmd_bridge
  -> /ctrl_cmd + /io_cmd
```

### 3. 安全仲裁与障碍急停

当前已接入的核心节点：

- `safety_guard_node`
  - 对自动导航速度、手动速度、障碍急停和急停服务做仲裁
  - 输出最终安全速度 `/cmd_vel_safe`
- `obstacle_stop_node`
  - 基于前方激光窗口检测最近障碍物
  - 输出 `/agt/obstacle_stop` 和障碍距离信息

### 4. Qt GUI 对接

当前工作空间对接了外部项目：

- `src/Ros_Qt5_Gui_App`

本包不重写该 GUI，只负责：

- 提供启动脚本
- 统一 topic / frame 映射说明
- 让它能接入当前导航链路

启动脚本：

- `scripts/start_qt_gui.sh`

示例：

```bash
export WS_ROOT=/path/to/your/ros2_ws
export ROS_DISTRO=${ROS_DISTRO:-humble}
export ROS_QT5_GUI_APP_DIR=${ROS_QT5_GUI_APP_DIR:-$WS_ROOT/src/Ros_Qt5_Gui_App}

source "/opt/ros/${ROS_DISTRO}/setup.bash"
source "${WS_ROOT}/install/setup.bash"

"${WS_ROOT}/src/agt_nav_console/scripts/start_qt_gui.sh" \
  "${ROS_QT5_GUI_APP_DIR}"
```

### 5. 导航实验记录与分析

当前包内集成了：

- `scripts/nav_test_recorder.py`
- `scripts/analyze_nav_test.py`
- `scripts/offline_nav_test_feeder.py`

支持能力包括：

- 自动创建单次测试目录
- 自动启动 `ros2 bag record`
- 保存 `metrics.csv`
- 保存 `events.csv`
- GUI 打事件、写备注、看资源占用
- 离线复盘路径长度、到点时间、终点误差等指标

推荐启动方式：

```bash
source "/opt/ros/${ROS_DISTRO}/setup.bash"
source "${WS_ROOT}/install/setup.bash"

ros2 run agt_nav_console nav_test_recorder \
  --gui \
  --profile debug \
  --output-root "${WS_ROOT}/nav_tests" \
  --test-name example_nav_run_01
```

## 关键文件

- `launch/safe_online_nav_demo.launch.py`
  安全导航主入口
- `launch/obstacle_stop_demo.launch.py`
  障碍急停链入口
- `config/topic_mapping.yaml`
  当前平台统一的 topic / frame / service 配置入口
- `config/safety.yaml`
  安全仲裁参数
- `config/obstacle_stop.yaml`
  障碍急停参数
- `scripts/nav_ops_console.py`
  总控 GUI
- `scripts/start_qt_gui.sh`
  Qt GUI 启动脚本

## 推荐 Topic / Frame 映射

当前链路建议统一参考：

- `config/topic_mapping.yaml`

常用映射包括：

- `map_topic`: `/map`
- `odom_topic`: `/aft_mapped_to_init`
- `scan_topic`: `/scan`
- `initial_pose_topic`: `/initialpose`
- `goal_topic`: `/goal_pose`
- `manual_cmd_topic`: `/agt/cmd_vel_manual`
- `nav_cmd_topic`: `/agt/cmd_vel_nav`
- `safe_cmd_topic`: `/cmd_vel_safe`
- `global_path_topic`: `/plan`
- `local_path_topic`: `/local_plan`
- `robot_footprint_topic`: `/local_costmap/published_footprint`
- `base_frame_id`: `livox_frame`

## 与其他包的关系

- `mid360_nav_demo`
  负责建图、地图保存、重定位和原始导航链
- `octo_planner`
  负责 Nav2 相关启动和底盘桥接
- `FAST-LIVO2-ROS2`
  提供在线里程计和建图点云
- `Ros_Qt5_Gui_App`
  提供交互式地图和目标点界面

## 迁移与二开提示

为了便于迁移和二次开发，当前这个包已经开始把关键配置从源码中抽离出来。后续建议优先保持下面这几个原则：

- 优先通过 `topic_mapping.yaml` 改 topic / frame，而不是直接改源码
- 优先通过 launch 参数改地图、点云和模式，而不是写死路径
- 总控 GUI 负责流程组织，不要把底层算法逻辑继续堆进去
- 测试输出、bag、地图导出目录尽量与源码目录分离

## 参考文档

- [README.md](/home/yangxuan/ros2_ws/README.md:1)
- [导航测试流程.md](/home/yangxuan/ros2_ws/导航测试流程.md:1)
- [迁移与二开整改清单.md](/home/yangxuan/ros2_ws/迁移与二开整改清单.md:1)
