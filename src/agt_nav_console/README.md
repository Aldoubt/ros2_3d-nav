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

## 导航总控上位机

为减少现场手工敲命令和路径切换，包内新增了一个总控 GUI：

- `scripts/nav_ops_console.py`

可直接通过下面命令启动：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 run agt_nav_console nav_ops_console
```

当前这版总控 GUI 主要用于把现场流程串起来：

- 进入建图模式
- 把 `pgm / yaml` 保存到指定路径
- 把最新 `all_raw_points.pcd` 导出到指定路径，避免后续再次建图时被覆盖
- 保存 2D 地图或导出点云后，自动回填导航模式使用的 YAML / PCD 路径
- 启动 `Ros_Qt5_Gui_App`
- 启动导航模式
- 启动导航记录器
- 一键停止全部相关进程

它更像是你当前工作流上的“流程总控层”，不替代 `Ros_Qt5_Gui_App` 本身的地图编辑能力，也不替代 `jie_octomap` 的专业地图管理 GUI。

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

## 导航实验记录流程

包内新增了两个脚本：

- `scripts/nav_test_recorder.py`: 创建测试目录、启动 `ros2 bag record`、记录 `metrics.csv` 与 `events.csv`
- `scripts/analyze_nav_test.py`: 从 `metrics.csv` 和 `events.csv` 计算基础导航指标
- `scripts/offline_nav_test_feeder.py`: GUI 发布假 `odom/cmd/goal/obstacle`，用于离线联调

内置两套录制预设：

- `lite`：
  - `/aft_mapped_to_init`
  - `/cmd_vel_safe`
  - `/goal_pose`
  - `/agt/obstacle_stop`
- `debug`：
  - `lite` 全部话题
  - `/cloud_registered`
  - `/plan`
  - `/local_plan`

当前默认使用 `lite`。如果你这套链路主要依赖 `MID360` 做传感器和规划、暂时不想把系统复杂化，推荐优先用 `debug`，它已经覆盖了常见导航复盘最需要的点云和路径话题，但不会额外强制录制 `TF`。

### 1. 启动记录

先 source ROS 环境：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash
```

如果当前 shell 里曾经切换过 Conda、旧工作区或失败过的 install 环境，建议先开一个新终端再执行上面两行。

若想先确认脚本已经被 ROS 识别，可执行：

```bash
ros2 pkg executables agt_nav_console
```

正常情况下应能看到：

- `agt_nav_console nav_test_recorder`
- `agt_nav_console analyze_nav_test`

推荐优先使用 GUI 模式启动记录器：

```bash
ros2 run agt_nav_console nav_test_recorder --gui
```

GUI 打开后默认先进入待命状态，需要点击界面内的“开始录制”才会真正启动 `ros2 bag record`。

如果想启用更适合导航问题复盘的预设，推荐：

```bash
ros2 run agt_nav_console nav_test_recorder --gui --profile debug
```

也可以直接指定输出目录或测试名：

```bash
ros2 run agt_nav_console nav_test_recorder \
  --gui \
  --profile debug \
  --output-root /home/yangxuan/nav_tests \
  --test-name lab_a_run_01
```

如果指定的 `--test-name` 已经存在，记录器会自动切换到一个不冲突的新目录，并在启动日志中提示最终使用的目录名。

如果后面有少量临时话题想补录，又不想改代码，可以使用：

```bash
ros2 run agt_nav_console nav_test_recorder \
  --gui \
  --profile debug \
  --extra-topics /some_extra_topic /another_topic
```

如果显式传入 `--topics`，则会完全覆盖 `--profile`：

```bash
ros2 run agt_nav_console nav_test_recorder \
  --gui \
  --topics /aft_mapped_to_init /cmd_vel_safe /goal_pose /agt/obstacle_stop /cloud_registered
```

如果当前环境没有桌面显示，也可以继续使用终端模式：

```bash
ros2 run agt_nav_console nav_test_recorder
```

启动后会自动创建单次测试目录，目录内包含：

- `bag/`: 由 `ros2 bag record` 自动生成
- `metrics.csv`: 里程计采样、速度、目标点、障碍急停状态
- `events.csv`: 人工事件标记
- `metadata.yaml`: 本次测试的基本信息与记录配置

### 2. GUI 交互说明

`--gui` 模式下会弹出轻量窗口，适合实验现场快速感知系统状态。

界面内可直接看到：

- 当前测试目录
- rosbag 是否正在录制
- `metrics.csv` 已写入行数
- 当前录制预设 `lite / debug`
- 当前实际录制的话题列表
- 最近一次事件
- `/aft_mapped_to_init`、`/cmd_vel_safe`、`/goal_pose`、`/agt/obstacle_stop` 的最近更新时间
- 当前最新位姿、目标点和安全速度
- 当前 `bag` 文件大小
- 当前累计录制时长
- 当前系统 `CPU / 内存 / 磁盘` 占用率
- 当内存、磁盘或 CPU 占用过高时，界面会给出提醒，便于提前发现资源风险

界面内可直接操作：

- 点击“开始录制”启动 rosbag
- 点击“结束录制并保存”结束本次实验
- 按钮事件：`start`、`arrive`、`fail`、`obstacle`、`takeover`
- 文本备注：输入后点击“添加备注”
- 结束测试：点击“停止并保存”

### 3. 终端事件标记

记录器启动后，可在终端输入以下命令：

- `start`: 开始正式计时或发车
- `arrive`: 到达目标点
- `fail`: 任务失败
- `obstacle`: 发生障碍物干预
- `takeover`: 人工接管
- `note`: 追加文字备注
- `q`: 停止记录并结束本次测试

其中 `note` 支持两种写法：

```bash
note lidar noise near shelf
```

或先输入：

```bash
note
```

再按提示补充备注文本。

如果你发现终端模式偶发出现 `stdin closed`，通常是终端输入链路被外层环境、IDE 集成终端或重定向影响。现场使用时更推荐 `--gui` 模式。

### 4. 结果分析

记录结束后，可对单次实验目录执行：

```bash
ros2 run agt_nav_console analyze_nav_test /path/to/nav_test_20260606_120000
```

当前脚本已支持输出以下基础指标：

- 路径长度 `path_length_m`
- 到点时间 `arrival_time_s`
- 最大速度 `max_speed_mps`
- 终点误差 `goal_error_m`

这些指标后续都基于 `metrics.csv` 持续扩展，不影响原始 bag 留档。

### 5. 离线测试流程

如果当前没有真实底盘、建图或导航链路，也可以先在本机做一次“假数据联调”，验证记录器、事件标记和分析脚本是否工作正常。

建议开 2 个终端。

终端 1：启动记录器

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 run agt_nav_console nav_test_recorder \
  --gui \
  --output-root /tmp/nav_tests \
  --test-name offline_smoke_test
```

终端 2：启动离线 feeder GUI

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 run agt_nav_console offline_nav_test_feeder
```

feeder GUI 会持续发布：

- `/aft_mapped_to_init`
- `/cmd_vel_safe`
- `/goal_pose`
- `/agt/obstacle_stop`

你可以在 GUI 内直接调整：

- 当前 pose
- 线速度 / 角速度
- goal 坐标
- `Obstacle Stop` 开关
- `Auto Motion` 开关
- `Publish Goal Once`

随后回到记录器窗口，点击或输入：

```text
start
note offline dry run
arrive
q
```

若使用 GUI：

- 点击 `start`
- 在备注框输入 `offline dry run` 后点击 `Add Note`
- 点击 `arrive`
- 点击 `Stop And Save`

结束后会生成：

- `/tmp/nav_tests/offline_smoke_test/bag`
- `/tmp/nav_tests/offline_smoke_test/metrics.csv`
- `/tmp/nav_tests/offline_smoke_test/events.csv`
- `/tmp/nav_tests/offline_smoke_test/metadata.yaml`

再执行分析：

```bash
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/install/setup.bash

ros2 run agt_nav_console analyze_nav_test /tmp/nav_tests/offline_smoke_test
```

如果只想做最小检查，也可以先不发 topic，仅验证：

- `ros2 pkg executables agt_nav_console`
- `ros2 run agt_nav_console nav_test_recorder --help`
- `ros2 run agt_nav_console analyze_nav_test --help`

## ROS 工作区干净构建流程

如果机器上装过 Conda、Python 虚拟环境，或者曾经在 `~/ros2_ws/src` 下又单独做过一套 colcon 工作区，建议在构建前先清理环境，再从 `~/ros2_ws` 根目录统一构建。

### 1. 推荐方式

直接运行：

```bash
/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/build_ros_clean_env.sh
```

只构建当前包：

```bash
/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/build_ros_clean_env.sh \
  --packages-select agt_nav_console
```

### 2. 脚本做了什么

- 若当前处于 Python venv，则自动 `deactivate`
- 清理 `CONDA_*` 和 `PYTHONPATH`
- 强制使用 `/usr/bin/python3`
- 从 `/home/yangxuan/ros2_ws` 根目录执行 `colcon build`
- 统一传入：

```bash
--cmake-args \
  -DPYTHON_EXECUTABLE=/usr/bin/python3 \
  -DPython3_EXECUTABLE=/usr/bin/python3
```

### 3. 首次彻底修复旧缓存

如果某些包之前已经被 Conda Python 污染过缓存，建议先做一次全清理：

```bash
/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/build_ros_clean_env.sh --clean
```

这个选项会删除：

- `/home/yangxuan/ros2_ws/build`
- `/home/yangxuan/ros2_ws/install`
- `/home/yangxuan/ros2_ws/log`
- `/home/yangxuan/ros2_ws/src/build`
- `/home/yangxuan/ros2_ws/src/install`
- `/home/yangxuan/ros2_ws/src/log`

只会删除工作区生成产物，不会删除源码。

### 4. 已知现象

- `topology_msgs` 之前失败的根因是旧的 `CMakeCache.txt` 把 `PYTHON_EXECUTABLE` 缓存成了 `miniconda3/bin/python3`
- `vikit_py` 的 `distutils` / `Unknown distribution option` 目前只是警告，不一定导致构建失败
- `Livox-SDK2` 的 rapidjson `#pragma` 警告目前也是编译警告，不是这次 Python 环境问题

## 当前状态

当前提交已经提供安全速度仲裁、障碍物急停、底盘安全接管链路，以及外部 Qt GUI 的接入说明与启动脚本。
