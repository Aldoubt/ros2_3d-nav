# agt_nav_console

`agt_nav_console` 是一个独立的 ROS 2 C++ 导航控制台包，使用 `ament_cmake` 构建。

当前包定位为后续导航上层控制能力的承载点，主要用于：

- 导航 GUI 操作台
- 安全速度仲裁
- 障碍物急停
- 单点 / 多点导航桥接

## 目录结构

- `src/`: C++ 源码
- `include/`: 对外头文件
- `launch/`: 启动文件
- `config/`: 参数配置
- `scripts/`: 辅助脚本

## 设计原则

- 与现有导航/建图包解耦，作为独立上层控制包演进
- 不直接修改 `mid360_nav_demo`
- 不直接修改 `jie_3d_nav`
- 不直接修改 `FAST-LIVO2-ROS2`

## 已接入能力

- `safety_guard_node`: 对自动导航、手动速度、障碍急停和急停服务做速度仲裁，输出 `/cmd_vel_safe`
- `obstacle_stop_node`: 基于前方激光窗口检测最近障碍物，输出 `/agt/obstacle_stop`
- `safe_online_nav_demo.launch.py`: 将 `Nav2 /cmd_vel -> /agt/cmd_vel_nav -> /cmd_vel_safe -> 底盘桥接` 串起来

## 手动遥控说明

当前底盘已经具备外部遥控器控制能力，因此 `agt_nav_console` 暂时不负责实现或接管遥控器链路。

- `/agt/cmd_vel_manual` 目前保留为上层 GUI 或未来人工接管入口
- 当前默认运行链路仍以自动导航和安全仲裁为主
- 外部遥控器如何直接控制底盘，不在本包职责范围内

## 外部 Qt GUI 对接

本包准备对接外部项目 `chengyangkj/Ros_Qt5_Gui_App`，但不重写、不修改该项目源码。

- 本包只提供启动脚本和 topic 对齐说明
- 外部 GUI 仍保持独立仓库、独立编译、独立运行

启动脚本：

- [start_qt_gui.sh](/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/start_qt_gui.sh:1)

示例：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/start_qt_gui.sh \
  /path/to/Ros_Qt5_Gui_App
```

也可以通过环境变量：

```bash
export ROS_QT5_GUI_APP_DIR=/path/to/Ros_Qt5_Gui_App
/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/start_qt_gui.sh
```

如果脚本找不到可执行文件，会提示你先在外部仓库中完成 GUI 编译。

## GUI Topic Mapping

推荐在外部 GUI 的配置界面中按下面的映射填写，完整记录也见
[topic_mapping.yaml](/home/yangxuan/ros2_ws/src/agt_nav_console/config/topic_mapping.yaml:1)。

- `map_topic`: `/map`
- `odom_topic`: `/aft_mapped_to_init`
- `scan_topic`: `/scan`
- `initial_pose_topic`: `/initialpose`
- `goal_topic`: `/goal_pose`
- `manual_cmd_topic`: `/agt/cmd_vel_manual`
- `safe_cmd_topic`: `/cmd_vel_safe`
- `global_path_topic`: `/plan`
- `local_path_topic`: `/local_plan`
- `robot_footprint_topic`: `/local_costmap/published_footprint`
- `BaseFrameId`: `livox_frame`

其中当前链路需要注意：

- 当前 `FAST-LIVO2-ROS2` 实际发布的是 `/aft_mapped_to_init`
- 当前 `Nav2` 参数里使用的里程计话题也是 `/aft_mapped_to_init`
- GUI 默认 `BaseFrameId` 也应与当前导航参数保持一致，填写 `livox_frame`

GUI 配置界面填写建议：

- 地图显示项填写 `/map`
- 机器人位姿/里程计项填写 `/aft_mapped_to_init`
- 激光显示项填写 `/scan`
- 2D 初始位姿设置项填写 `/initialpose`
- 单点导航目标项填写 `/goal_pose`
- 手动速度控制发布项填写 `/agt/cmd_vel_manual`
- 若 GUI 需要监看最终安全输出速度，则填写 `/cmd_vel_safe`
- 全局路径显示项填写 `/plan`
- 局部路径显示项填写 `/local_plan`
- 机器人 footprint 显示项填写 `/local_costmap/published_footprint`
- 高级配置中的 `BaseFrameId` 填写 `livox_frame`

## 当前状态

当前提交已经提供安全速度仲裁、障碍物急停、底盘安全接管链路，以及外部 Qt GUI 的接入说明与启动脚本。
