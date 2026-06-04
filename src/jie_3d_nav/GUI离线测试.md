# GUI 离线测试

本文档用于测试 `Ros_Qt5_Gui_App` 在离线条件下是否工作正常。

这里的“离线”分成两类：

1. 不启动实车、不接底盘，只测试 GUI 本体。
2. 不启动实车，但通过 `bag` 回放测试 GUI 与当前导航链的话题联动。

适用目录约定：

```text
工作空间: /home/yangxuan/ros2_ws
源码目录: /home/yangxuan/ros2_ws/src
GUI 工程: /home/yangxuan/ros2_ws/src/Ros_Qt5_Gui_App
导航控制包: /home/yangxuan/ros2_ws/src/agt_nav_console
bag 目录: /home/yangxuan/ros2_ws/src/bags
```

---

## 1. 测试目标

建议把测试拆开，不要一上来就直接验证“整套导航任务都能跑通”。

### 1.1 纯 GUI 离线测试

主要确认：

```text
GUI 能否正常启动
本地 yaml 地图能否正常加载
同名 .topology 文件能否自动加载
拓扑点、连线、编辑、保存是否正常
多点导航界面本身是否正常显示
```

这一类测试不依赖机器人在线数据。

### 1.2 bag 回放联调测试

主要确认：

```text
GUI 是否能显示 /map
GUI 是否能显示 /aft_mapped_to_init
GUI 是否能显示 /scan
GUI 发布 /initialpose 和 /goal_pose 是否正常
安全导航主链是否能接收到 GUI 发出的目标
```

这一类测试不接实车，但需要 ROS 节点和 `bag` 回放。

### 1.3 当前不要作为离线验收目标的内容

当前这部分还不适合作为“离线已通过”标准：

```text
底盘真实运动效果
复杂窄路口的最终避障效果
Nav2 原生多点 Action 的完整行为验证
```

原因是：

```text
Ros_Qt5_Gui_App 的 Task 面板现在已经可以顺序发送多个 /goal_pose
但这属于 GUI 侧的逐点串行发单点目标
它不是 Nav2 的 NavigateThroughPoses / FollowWaypoints 原生 Action 链
离线阶段更适合先验收目标发布、路径显示和控制链联通
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

如果 GUI 还没编译好，先编译 GUI：

```bash
cd /home/yangxuan/ros2_ws/src/Ros_Qt5_Gui_App
cmake --build build --target channel_ros2 ros_qt5_gui_app -j$(nproc)
```

当前 GUI 默认已经对齐到这条导航链：

```text
map_topic: /map
odom_topic: /aft_mapped_to_init
scan_topic: /scan
initial_pose_topic: /initialpose
goal_topic: /goal_pose
manual_cmd_topic: /agt/cmd_vel_manual
safe_cmd_topic: /cmd_vel_safe
global_path_topic: /plan
local_path_topic: /local_plan
robot_footprint_topic: /local_costmap/published_footprint
BaseFrameId: livox_frame
```

---

## 3. 测试一：纯 GUI 离线测试

### 3.1 启动 GUI

```bash
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash

/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/start_qt_gui.sh \
  /home/yangxuan/ros2_ws/src/Ros_Qt5_Gui_App
```

如果脚本启动失败，也可以直接运行：

```bash
cd /home/yangxuan/ros2_ws/src/Ros_Qt5_Gui_App/build
./start.sh
```

### 3.2 加载本地地图

在 GUI 顶部工具栏点击“打开地图”，选择：

```text
/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/site1.yaml
```

或你自己的其他 `yaml` 地图。

预期结果：

```text
地图成功显示
缩放、拖动正常
不会报“无法打开地图文件”
```

### 3.3 自动加载 topology

如果同目录下存在同名 `.topology` 文件，例如：

```text
/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/site1.topology
```

则 GUI 打开 `site1.yaml` 后应自动加载对应拓扑数据。

预期结果：

```text
历史导航点自动出现
历史拓扑连线自动出现
导航点名称正常显示
```

如果没有现成 `.topology` 文件，可以继续下一步手工创建。

### 3.4 手工创建拓扑点和连线

建议至少测试：

```text
新增 3 个导航点
拖动导航点位置
修改导航点名称
连接 2 条拓扑连线
删除 1 个点或 1 条线
```

预期结果：

```text
编辑操作有可见反馈
点位和连线状态刷新正常
不会闪退
```

### 3.5 保存并重新打开

保存当前地图相关数据。

预期结果：

```text
生成或更新同名 .topology 文件
重新打开 GUI 后仍可重新加载
点位和连线不会丢失
```

### 3.6 Task 面板正确用法

`Task` 面板默认可能是隐藏的，需要先在菜单中打开：

```text
View -> Task
```

推荐使用顺序：

```text
1. 先进入“编辑地图”
2. 在地图上新增工位点，并保存 topology
3. 打开 Task 面板
4. 点击 Add Point，为任务列表新增一行
5. 在每一行左侧下拉框中选择一个已有工位点
6. 根据需要使用 Run 或 Start Task Chain
```

注意：

```text
只有已经存在于当前 topology 里的工位点，才会出现在下拉框中
如果刚新增工位点后下拉框没有刷新，先保存地图，再重新打开当前地图
如果任务状态显示 Point Not Found!，说明任务行里选中的点名不在当前 topology 中
```

### 3.7 Run 和 Start Task Chain 的区别

两者作用不同：

```text
Run: 只发送当前这一行选中的单个工位点，相当于一次单点导航测试
Start Task Chain: 按表格从上到下依次发送每一行工位点，用于多点顺序任务
Loop Task: 配合 Start Task Chain 使用，表示列表跑完后循环执行
```

建议测试顺序：

```text
先用 Run 测单点
确认 /goal_pose、/plan、/cmd_vel_safe 正常后
再用 Start Task Chain 测多点顺序任务
```

### 3.8 GUI 和 Nav2 的职责边界

当前这套链路里，GUI 不是规划器，也不是跟踪控制器。

GUI 负责：

```text
显示地图、位姿、激光、路径
编辑工位点和 topology
发布 /initialpose
发布 /goal_pose
发布 /agt/cmd_vel_manual
在 Task 面板里按顺序发送多个单点目标
```

Nav2 负责：

```text
根据 /goal_pose 和地图计算全局路径 /plan
根据局部代价地图和全局路径计算局部路径 /local_plan
输出 /cmd_vel 进行路径跟踪
```

当前实际控制链为：

```text
GUI -> /goal_pose -> Nav2 规划与跟踪 -> /cmd_vel -> safety_guard -> /cmd_vel_safe -> 底盘
```

所以需要注意：

```text
GUI 里工位点之间的连线只是拓扑关系或任务顺序的可视化
它不等于机器人最终实际行驶轨迹
真正的绕障、贴边、转向和速度控制由 Nav2 完成
```

### 3.9 纯离线测试通过标准

满足下面这些就可以认为 GUI 本体基本正常：

```text
GUI 能正常启动
yaml 地图能正常打开
topology 能正常加载
拓扑编辑正常
topology 保存和再次加载正常
多点导航面板能打开，任务列表能编辑
Task 面板可以选点
Run 可以发送单点目标
Start Task Chain 可以顺序发送多个目标
```

---

## 4. 测试二：bag 回放联调测试

这一组测试用于确认 GUI 和当前导航链的话题交互是否正常。

### 4.1 bag 内容要求

推荐至少包含：

```text
/livox/lidar
/livox/imu
/cloud_registered
/aft_mapped_to_init
/tf
/tf_static
```

如果还包含 `/projected_map`、`/map` 更方便。

先检查 bag：

```bash
ros2 bag info /home/yangxuan/ros2_ws/src/bags/你的bag目录
```

### 4.2 启动安全导航主链

不接底盘，使用仿真时间：

```bash
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash

ros2 launch agt_nav_console safe_online_nav_demo.launch.py \
  map:=/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/site1.yaml \
  global_map_pcd:=/home/yangxuan/ros2_ws/src/FAST-LIVO2-ROS2/Log/PCD/all_raw_points.pcd \
  use_sim_time:=true \
  launch_chassis:=false \
  launch_rviz:=false
```

说明：

```text
这一步主要是把 /goal_pose、/initialpose、/cmd_vel_safe、/scan 相关链路先拉起来
这里只做离线联调，不需要真的控制底盘
```

### 4.3 回放 bag

新开终端：

```bash
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash

ros2 bag play /home/yangxuan/ros2_ws/src/bags/mid360_mapping_20260603_195044
```

### 4.4 启动 GUI

再开一个终端：

```bash
cd /home/yangxuan/ros2_ws/src
source /opt/ros/humble/setup.bash
source /home/yangxuan/ros2_ws/src/install/setup.bash

/home/yangxuan/ros2_ws/src/agt_nav_console/scripts/start_qt_gui.sh \
  /home/yangxuan/ros2_ws/src/Ros_Qt5_Gui_App
```

### 4.5 GUI 检查项

进入 GUI 后先确认这些配置项：

```text
Map topic: /map
Odometry topic: /aft_mapped_to_init
Laser topic: /scan
Initial pose topic: /initialpose
Goal topic: /goal_pose
Manual cmd topic: /agt/cmd_vel_manual
Global path topic: /plan
Local path topic: /local_plan
Robot footprint topic: /local_costmap/published_footprint
BaseFrameId: livox_frame
```

然后观察：

```text
地图是否显示
机器人位姿是否显示
激光是否显示
全局路径/局部路径是否有显示
```

### 4.6 发布目标测试

在 GUI 中依次做两件事：

```text
1. 发布初始位姿
2. 发布单点导航目标
```

同时在终端检查：

```bash
ros2 topic echo /initialpose --once
ros2 topic echo /goal_pose --once
```

预期结果：

```text
能收到 /initialpose
能收到 /goal_pose
消息 frame_id 为 map
```

如果要测试 Task 面板：

```text
先在编辑地图中确认 topology 已保存
打开 View -> Task
使用 Add Point 新增任务行
在下拉框中选择已有工位点
点击 Run 测试单点发布
点击 Start Task Chain 测试顺序发布
```

说明：

```text
Run 和 Start Task Chain 最终发送的都是 /goal_pose
区别只是一次发一个，还是按表格顺序依次发多个
```

### 4.7 安全链检查

如果 GUI 发了导航目标，再检查：

```bash
ros2 topic hz /agt/cmd_vel_nav -w 5
ros2 topic hz /cmd_vel_safe -w 5
ros2 topic echo /agt/obstacle_stop --once
ros2 topic echo /agt/obstacle_distance --once
```

预期结果：

```text
Nav2 有速度输出时，/agt/cmd_vel_nav 有数据
安全仲裁通过后，/cmd_vel_safe 有数据
障碍急停节点能给出当前状态
```

---

## 5. 推荐最小检查命令

如果你只想快速判断“GUI 现在大体对不对”，建议至少跑下面这些：

```bash
ros2 topic info /map -v
ros2 topic info /scan -v
ros2 topic info /aft_mapped_to_init -v
ros2 topic echo /initialpose --once
ros2 topic echo /goal_pose --once
ros2 run tf2_ros tf2_echo map odom
ros2 run tf2_ros tf2_echo odom livox_frame
```

---

## 6. 当前离线测试的通过标准

### 6.1 纯 GUI 通过标准

```text
GUI 可以启动
本地 yaml 地图可以打开
.topology 文件可以加载和保存
拓扑点和连线可编辑
多点导航界面本身可用
Task 面板可以看到并能新增任务行
Task 面板下拉框可以选到当前 topology 中的工位点
Run 可以发送单点任务
```

### 6.2 bag 联调通过标准

```text
GUI 能显示 /map
GUI 能显示 /aft_mapped_to_init
GUI 能显示 /scan
GUI 发布 /initialpose 正常
GUI 发布 /goal_pose 正常
安全链能接收到导航控制输出
Task 面板能正确选点并发目标
```

### 6.3 当前不作为通过标准

```text
真实底盘运动
复杂环境下的最终避障表现
Nav2 原生多点 Action 行为
```

---

## 7. 常见问题

### 7.1 GUI 打开后看不到地图

先确认：

```text
是否真的打开了本地 yaml
或者 /map 是否真的有发布
```

如果走本地离线方式，优先用“打开地图”手工选择 `yaml` 文件。

### 7.2 GUI 看不到机器人位姿

当前这套链路默认不是 `/odom`，而是：

```text
/aft_mapped_to_init
```

同时 `BaseFrameId` 应为：

```text
livox_frame
```

### 7.3 GUI 看不到激光

当前激光是通过：

```text
/cloud_registered -> pointcloud_to_laserscan -> /scan
```

如果 `/scan` 没有数据，先检查：

```bash
ros2 topic info /cloud_registered -v
ros2 topic info /scan -v
```

### 7.4 点了“开始任务”但多点导航没有自动跑

先区分你点的是哪个按钮。

当前正确用法是：

```text
Run: 发送当前行的单点目标
Start Task Chain: 从上到下依次发送多行任务点
```

如果点了 `Start Task Chain` 仍然不跑，优先检查：

```text
Task 行左侧下拉框里是否真的选中了已有工位点
任务状态是否显示 Point Not Found!
当前 topology 是否已经保存并和当前地图一致
是否已经能通过 ros2 topic echo /goal_pose --once 收到 GUI 发出的目标
```

这里要特别注意：

```text
GUI 的多点任务本质上是逐点串行发送 /goal_pose
真正的全局规划、局部跟踪和避障仍然由 Nav2 完成
所以 GUI 里看到的直线连线只是任务顺序示意，不是最终实际行驶轨迹
```
