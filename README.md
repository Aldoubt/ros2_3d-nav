# ros2_ws

这个工作区用于统一维护当前这套 `MID360 + FAST-LIVO2 + 重定位 + Nav2 + Qt 可视化 + 导航测试记录` 的实际联调代码。

当前已经完成并持续使用的能力主要有：

- `Nav2` 自动导航主链路接入
- `FAST-LIVO2` 在线建图与运行时里程计输出
- 基于全局点云地图的重定位链路接入
- 外部 `chengyangkj/Ros_Qt5_Gui_App` 可视化任务界面接入
- 自动导航实验记录与分析 GUI 工具

后续将继续围绕 `jie_octomap / octo_planner` 推进三维地图管理、三维路径规划与更完整的上层任务交互。

## 工作区当前完成的任务

### 1. Nav2 自动导航

当前已经打通一条可实际使用的二维自动导航链路：

- `FAST-LIVO2` 提供运行时位姿与配准点云
- 重定位节点提供 `map -> odom`
- `Nav2` 负责全局/局部规划与控制
- `agt_nav_console` 负责安全速度仲裁、障碍急停与底盘桥接

这一条主链的统一入口目前使用：

- `src/agt_nav_console/launch/safe_online_nav_demo.launch.py`

### 2. Qt 可视化任务界面接入

工作区已经接入外部项目 `chengyangkj/Ros_Qt5_Gui_App`，当前策略是：

- 保持外部 GUI 仓库独立
- 不直接改写上游 GUI 源码
- 通过 topic 对齐和启动脚本完成接入

当前使用的启动脚本：

- `src/agt_nav_console/scripts/start_qt_gui.sh`

Qt GUI 当前主要用于：

- 地图显示
- 机器人位姿显示
- 初始位姿设置
- 目标点输入
- 路径显示
- 手动速度输入与安全速度观测

### 3. 自动导航评价 GUI

工作区内新增了导航实验记录与分析工具，支持：

- 自动创建单次测试目录
- 自动启动 `ros2 bag record`
- 记录 `metrics.csv`
- 记录 `events.csv`
- GUI 模式下打事件、加备注、看资源占用
- 后处理输出路径长度、到点时间、最大速度、终点误差

当前主要脚本：

- `src/agt_nav_console/scripts/nav_test_recorder.py`
- `src/agt_nav_console/scripts/analyze_nav_test.py`
- `src/agt_nav_console/scripts/offline_nav_test_feeder.py`

### 4. 后续研究方向

当前已经验证并稳定使用的是 `Nav2 + 重定位 + Qt GUI + 记录器` 这条链路。

后续计划继续推进：

- `jie_octomap` 三维地图导入、编辑、管理
- `octo_planner` 三维路径规划与可视化
- 三维地图下的交互式设点与任务执行
- 更贴近真实任务的自动评价指标扩展

## 关键目录

- `src/agt_nav_console`
  当前导航控制台、速度仲裁、急停、测试记录工具
- `src/mid360_nav_demo`
  MID360 在线建图、重定位、Nav2 demo
- `src/jie_3d_nav`
  三维导航相关总目录，包含 `jie_octomap` 与 `octo_planner`
- `src/Ros_Qt5_Gui_App`
  外部 Qt GUI 工程源码
- `src/FAST-LIVO2-ROS2`
  MID360 点云里程计与建图
- `src/lidar_localization_ros2`
  点云重定位相关代码

## 实际测试使用到的代码

### 建图与地图编辑

- `src/FAST-LIVO2-ROS2/config/mid360_lio_only.yaml`
- `src/mid360_nav_demo/launch/online_mapping_demo.launch.py`
- `src/jie_3d_nav/jie_octomap/launch/import_pcd_map.launch.py`
- `src/jie_3d_nav/jie_octomap/launch/map_manager.launch.py`

### 重定位与 Nav2 导航

- `src/FAST-LIVO2-ROS2/config/mid360_lio_relocalization.yaml`
- `src/mid360_nav_demo/launch/online_nav_demo.launch.py`
- `src/agt_nav_console/launch/safe_online_nav_demo.launch.py`
- `src/mid360_nav_demo/config/icp_relocalizer.yaml`

### Qt GUI 接入

- `src/agt_nav_console/scripts/start_qt_gui.sh`
- `src/agt_nav_console/config/topic_mapping.yaml`
- `src/Ros_Qt5_Gui_App`

### 导航测试记录与分析

- `src/agt_nav_console/scripts/nav_test_recorder.py`
- `src/agt_nav_console/scripts/analyze_nav_test.py`
- `src/agt_nav_console/scripts/offline_nav_test_feeder.py`

## 实际测试流程

下面这套流程按“已经在现场联调用过的思路”整理，分为建图/地图编辑、重定位导航、Qt GUI 设点、测试记录四部分。

### 1. 编译工作区

推荐在工作区根目录构建：

```bash
cd /home/yangxuan/ros2_ws
source /opt/ros/humble/setup.bash
colcon build
source /home/yangxuan/ros2_ws/install/setup.bash
```

如果当前终端容易被 Conda 或 venv 污染，建议直接使用：

```bash
/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/build_ros_clean_env.sh --packages-up-to agt_nav_console
```

### 2. 启动建图

建图阶段建议使用 `FAST-LIVO2` 的建图配置，先产出全局点云地图：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 launch mid360_nav_demo online_mapping_demo.launch.py
```

如果你更想直接单独跑 `FAST-LIVO2`，也可以改为：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 launch fast_livo mapping_mid360_lio.launch.py \
  params_file:=/home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/config/mid360_lio_only.yaml
```

说明：

- 建图结束后，需要确认 `FAST-LIVO2-ROS2/Log/PCD/` 下导出了全局 `.pcd`
- 后续重定位建议使用裁剪或降采样后的地图

### 3. GUI 地图编辑

导出全局点云地图后，可使用 `jie_octomap` 的 GUI 做地图转换、裁剪和管理。

导入 PCD 并转换：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 launch jie_octomap import_pcd_map.launch.py
```

地图包管理与编辑主入口：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 launch jie_octomap map_manager.launch.py
```

这一部分当前主要用于：

- 把 `.pcd` 转成更适合交互和规划使用的地图格式
- 做简单裁剪与清理
- 保存地图包供后续三维规划研究使用

### 4. 启动重定位模式

当前实测导航链建议使用 `safe_online_nav_demo.launch.py`，它会把：

- `FAST-LIVO2`
- ICP 重定位
- `Nav2`
- 安全速度仲裁
- 障碍急停
- 底盘控制桥接

串成一条完整的实测链路。

示例：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 launch agt_nav_console safe_online_nav_demo.launch.py \
  global_map_pcd:=/home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/Log/PCD/all_raw_points.pcd \
  map:=/home/yangxuan/ros2_ws/src/jie_3d_nav/octo_planner/maps/syswaiwei.yaml
```

如果只是单独验证重定位，也可以使用 `jie_3d_nav` 当前的入口：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 launch octo_planner my_robot_nav.launch.py \
  launch_livox_driver:=true \
  launch_fastlivo:=true \
  launch_lidar_localization:=true \
  publish_static_odom_to_base:=false \
  base_frame:=livox_frame \
  lidar_localization_map_path:=/data/maps/site_a/site_a_global_map.pcd
```

### 5. 启动 Qt GUI，在界面中输入目标点

如果 `Ros_Qt5_Gui_App` 已经完成编译，可以直接通过工作区内的脚本拉起：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/start_qt_gui.sh \
  /home/yangxuan/ros2_ws/src/Ros_Qt5_Gui_App
```

或者：

```bash
export ROS_QT5_GUI_APP_DIR=/home/yangxuan/ros2_ws/src/Ros_Qt5_Gui_App
/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/start_qt_gui.sh
```

Qt GUI 中建议按下面的 topic 映射配置：

- `map_topic`: `/map`
- `odom_topic`: `/aft_mapped_to_init`
- `initial_pose_topic`: `/initialpose`
- `goal_topic`: `/goal_pose`
- `safe_cmd_topic`: `/cmd_vel_safe`

现场使用时的常见步骤：

1. 先确认地图、位姿和 TF 已稳定。
2. 在 Qt GUI 中设置初始位姿，或通过 RViz 向 `/initialpose` 发布初值。
3. 在 Qt GUI 中输入目标点，发布到 `/goal_pose`。
4. 观察全局路径、局部路径和 `/cmd_vel_safe` 输出。

### 6. 启动导航测试记录 GUI

建议在单独终端启动记录器：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 run agt_nav_console nav_test_recorder \
  --gui \
  --profile debug \
  --output-root /tmp/nav_tests \
  --test-name nav2_qt_gui_run_01
```

如果这个测试名之前已经用过，记录器会自动避让到新的目录名，不会再因为同名目录已存在而直接退出。

这里建议优先使用 `--profile debug`。当前这套预设会在基础导航话题之外额外录制：

- `/cloud_registered`
- `/plan`
- `/local_plan`

这样既能保留点云和路径信息，方便复盘导航问题，又不会额外把 `TF` 链路复杂度引进来。

记录器 GUI 当前支持：

- 手动点击“开始录制”
- 自动拉起 `ros2 bag record`
- 查看 `bag` 文件大小和累计录制时长
- 查看最近位姿、目标点、速度与障碍状态
- 查看 `CPU / 内存 / 磁盘` 占用率
- 资源过高时自动写入 `events.csv`
- 手动打事件：`start / arrive / fail / obstacle / takeover`
- 手动添加备注

### 7. 完成一次实际测试并保存记录

推荐现场操作顺序：

1. 启动重定位与导航主链。
2. 启动 Qt GUI。
3. 启动 `nav_test_recorder --gui`。
4. 点击“开始录制”。
5. 点击 `start` 标记正式开始。
6. 在 Qt GUI 中输入目标点，开始自动导航。
7. 过程中根据现场情况记录 `obstacle`、`takeover`、`note` 等事件。
8. 到点后点击 `arrive`，若失败则点击 `fail`。
9. 点击“停止并保存”结束本次实验。

保存后的单次测试目录通常包含：

- `bag/`
- `metrics.csv`
- `events.csv`
- `metadata.yaml`

### 8. 结果分析

记录结束后可直接分析：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 run agt_nav_console analyze_nav_test /tmp/nav_tests/nav2_qt_gui_run_01
```

当前已支持输出：

- 路径长度
- 到点时间
- 最大速度
- 终点误差

## 测试记录流程建议

建议每次真实测试至少保留下面这些信息：

### 基本信息

- 测试日期
- 场地名称
- 地图版本
- 重定位地图文件
- Nav2 参数版本
- Qt GUI 配置版本

### 过程事件

- `start`
- `arrive`
- `fail`
- `obstacle`
- `takeover`
- `note`
- 自动资源告警 `resource_warn`

### 输出留档

- `rosbag`
- `metrics.csv`
- `events.csv`
- `metadata.yaml`
- 若有需要，再补现场视频和故障截图

## 推荐终端分工

现场联调时，建议至少分 3 到 4 个终端，避免日志互相覆盖，也方便随时单独重启某一环。

### 终端 1：导航主链

用途：

- 启动 `FAST-LIVO2`
- 启动重定位
- 启动 `Nav2`
- 启动安全仲裁和底盘桥接

推荐命令：

```bash
cd /home/yangxuan/ros2_ws
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 launch agt_nav_console safe_online_nav_demo.launch.py \
  global_map_pcd:=/home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/Log/PCD/all_raw_points.pcd \
  map:=/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/site1.yaml
```

这一终端主要观察：

- 重定位是否收敛
- `Nav2` 是否成功接到目标
- `/cmd_vel_safe` 是否持续输出
- 是否出现障碍急停或底盘桥接异常

### 终端 2：Qt GUI 任务界面

用途：

- 观察地图与位姿
- 设置初始位姿
- 输入目标点
- 观察路径和状态

推荐命令：

```bash
cd /home/yangxuan/ros2_ws
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/start_qt_gui.sh \
  /home/yangxuan/ros2_ws/src/Ros_Qt5_Gui_App
```

这一终端对应的 GUI 主要操作：

1. 确认地图已显示。
2. 确认机器人位姿稳定。
3. 必要时先设置 `/initialpose`。
4. 在 GUI 中输入目标点并发起导航。

### 终端 3：导航测试记录器

用途：

- 开始和结束录制
- 查看录制状态
- 记录到点、失败、接管、障碍等事件
- 观察 CPU / 内存 / 磁盘资源

推荐命令：

```bash
cd /home/yangxuan/ros2_ws
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 run agt_nav_console nav_test_recorder \
  --gui \
  --output-root /tmp/nav_tests \
  --test-name nav2_qt_gui_run_01
```

推荐操作顺序：

1. 主链稳定后打开 recorder。
2. 点击“开始录制”。
3. 发车瞬间点击 `start`。
4. 途中按实际情况记录 `obstacle`、`takeover`、`note`。
5. 到点点击 `arrive`，失败点击 `fail`。
6. 点击“停止并保存”。

### 终端 4：辅助检查与临时排障

用途：

- 单独看 topic / TF
- 临时发初始位姿
- 查看节点是否都起来
- 出问题时快速定位，不干扰主链日志

常用命令：

```bash
cd /home/yangxuan/ros2_ws
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 node list | sort
ros2 topic list | sort
ros2 topic echo /localization/pose --once
ros2 run tf2_ros tf2_echo map odom
```

如果现场要手动发初始位姿，优先建议走 Qt GUI 或 RViz；终端注入更适合排障时短时使用。

### 推荐启动顺序

推荐按下面顺序开：

1. 终端 1：先把导航主链拉起来。
2. 终端 2：打开 Qt GUI，确认地图和位姿正常。
3. 终端 3：打开 recorder，准备记录。
4. 终端 4：留作检查和排障备用。

这样分工的好处是：

- 主链日志不会被 GUI 或记录器输出淹没
- 记录器可以单独重启，不影响导航
- Qt GUI 卡住时不影响主链继续跑
- 排障命令有独立终端，不会打断现场操作

## 参考文档

- `src/agt_nav_console/README.md`
- `src/jie_3d_nav/README.md`
- `src/mid360_nav_demo/README.md`
- `src/Ros_Qt5_Gui_App/README.md`
