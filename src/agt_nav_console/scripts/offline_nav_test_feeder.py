#!/usr/bin/python3

import argparse
import math
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import rclpy
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import Bool
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TOPIC_CONFIG = SCRIPT_DIR.parent / "config" / "topic_mapping.yaml"


def load_topic_mapping(config_path: Path) -> dict[str, str]:
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except OSError as exc:
        raise SystemExit(f"Failed to read topic config: {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Topic config must be a YAML mapping: {config_path}")
    return {str(key): value for key, value in data.items()}


def quaternion_from_yaw(yaw: float) -> tuple[float, float, float, float]:
    half = yaw * 0.5
    return 0.0, 0.0, math.sin(half), math.cos(half)


@dataclass
class FeederState:
    pose_x: float = 0.0
    pose_y: float = 0.0
    pose_z: float = 0.0
    yaw: float = 0.0
    linear_x: float = 0.3
    linear_y: float = 0.0
    angular_z: float = 0.1
    goal_x: float = 3.0
    goal_y: float = 1.0
    goal_z: float = 0.0
    goal_yaw: float = 0.0
    obstacle_stop: bool = False
    auto_motion: bool = True
    publish_goal_each_second: bool = True


class OfflineNavTestFeeder(Node):
    def __init__(self, args: argparse.Namespace):
        super().__init__("offline_nav_test_feeder")
        self.args = args
        self.state = FeederState()
        self._lock = threading.Lock()

        self.odom_pub = self.create_publisher(Odometry, args.odom_topic, 10)
        self.cmd_pub = self.create_publisher(Twist, args.cmd_topic, 10)
        self.goal_pub = self.create_publisher(PoseStamped, args.goal_topic, 10)
        self.obstacle_pub = self.create_publisher(Bool, args.obstacle_topic, 10)

        self.create_timer(1.0 / args.odom_rate, self._publish_odom)
        self.create_timer(1.0 / args.cmd_rate, self._publish_cmd)
        self.create_timer(1.0 / args.obstacle_rate, self._publish_obstacle)
        self.create_timer(1.0, self._publish_goal_if_needed)

    def snapshot(self) -> FeederState:
        with self._lock:
            return FeederState(**self.state.__dict__)

    def update(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self.state, key, value)

    def publish_goal_once(self) -> None:
        goal = PoseStamped()
        goal.header.stamp = self.get_clock().now().to_msg()
        goal.header.frame_id = self.args.frame_id
        snap = self.snapshot()
        goal.pose.position.x = snap.goal_x
        goal.pose.position.y = snap.goal_y
        goal.pose.position.z = snap.goal_z
        _, _, qz, qw = quaternion_from_yaw(snap.goal_yaw)
        goal.pose.orientation.z = qz
        goal.pose.orientation.w = qw
        self.goal_pub.publish(goal)
        self.get_logger().info(
            f"Published goal: x={snap.goal_x:.2f}, y={snap.goal_y:.2f}, yaw={snap.goal_yaw:.2f}"
        )

    def _publish_goal_if_needed(self) -> None:
        if self.snapshot().publish_goal_each_second:
            self.publish_goal_once()

    def _publish_cmd(self) -> None:
        snap = self.snapshot()
        msg = Twist()
        msg.linear.x = snap.linear_x
        msg.linear.y = snap.linear_y
        msg.angular.z = snap.angular_z
        self.cmd_pub.publish(msg)

    def _publish_obstacle(self) -> None:
        msg = Bool()
        msg.data = self.snapshot().obstacle_stop
        self.obstacle_pub.publish(msg)

    def _publish_odom(self) -> None:
        snap = self.snapshot()
        if snap.auto_motion:
            dt = 1.0 / self.args.odom_rate
            new_yaw = snap.yaw + snap.angular_z * dt
            new_x = snap.pose_x + snap.linear_x * math.cos(new_yaw) * dt
            new_y = snap.pose_y + snap.linear_x * math.sin(new_yaw) * dt
            self.update(pose_x=new_x, pose_y=new_y, yaw=new_yaw)
            snap = self.snapshot()

        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.args.frame_id
        msg.child_frame_id = self.args.child_frame_id
        msg.pose.pose.position.x = snap.pose_x
        msg.pose.pose.position.y = snap.pose_y
        msg.pose.pose.position.z = snap.pose_z
        _, _, qz, qw = quaternion_from_yaw(snap.yaw)
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        msg.twist.twist.linear.x = snap.linear_x
        msg.twist.twist.linear.y = snap.linear_y
        msg.twist.twist.angular.z = snap.angular_z
        self.odom_pub.publish(msg)


class FeederGui:
    def __init__(self, feeder: OfflineNavTestFeeder):
        import tkinter as tk
        from tkinter import ttk

        self.feeder = feeder
        self.tk = tk
        self.root = tk.Tk()
        self.root.title("离线导航话题发布器")
        self.root.geometry("820x620")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        self.pose_x = tk.DoubleVar(value=0.0)
        self.pose_y = tk.DoubleVar(value=0.0)
        self.yaw = tk.DoubleVar(value=0.0)
        self.linear_x = tk.DoubleVar(value=0.3)
        self.linear_y = tk.DoubleVar(value=0.0)
        self.angular_z = tk.DoubleVar(value=0.1)
        self.goal_x = tk.DoubleVar(value=3.0)
        self.goal_y = tk.DoubleVar(value=1.0)
        self.goal_yaw = tk.DoubleVar(value=0.0)
        self.obstacle_stop = tk.BooleanVar(value=False)
        self.auto_motion = tk.BooleanVar(value=True)
        self.goal_repeat = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar()

        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="离线导航话题发布器", font=("TkDefaultFont", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(
            frame,
            text=(
                f"持续发布 {self.feeder.args.odom_topic}、{self.feeder.args.cmd_topic}、"
                f"{self.feeder.args.goal_topic}、{self.feeder.args.obstacle_topic}，"
                "配合 nav_test_recorder 做本地联调。"
            ),
        ).pack(anchor=tk.W, pady=(4, 10))

        grid = ttk.Frame(frame)
        grid.pack(fill=tk.X)

        self._add_spinbox(grid, "位姿 X", self.pose_x, 0)
        self._add_spinbox(grid, "位姿 Y", self.pose_y, 1)
        self._add_spinbox(grid, "航向 yaw(rad)", self.yaw, 2)
        self._add_spinbox(grid, "线速度 X", self.linear_x, 3)
        self._add_spinbox(grid, "线速度 Y", self.linear_y, 4)
        self._add_spinbox(grid, "角速度 Z", self.angular_z, 5)
        self._add_spinbox(grid, "目标 X", self.goal_x, 6)
        self._add_spinbox(grid, "目标 Y", self.goal_y, 7)
        self._add_spinbox(grid, "目标 yaw", self.goal_yaw, 8)

        toggle_frame = ttk.Frame(frame)
        toggle_frame.pack(fill=tk.X, pady=(10, 10))
        ttk.Checkbutton(toggle_frame, text="自动运动", variable=self.auto_motion, command=self._push_state).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(toggle_frame, text="障碍急停", variable=self.obstacle_stop, command=self._push_state).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(toggle_frame, text="每秒重复目标", variable=self.goal_repeat, command=self._push_state).pack(side=tk.LEFT)

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(button_frame, text="应用参数", command=self._push_state).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_frame, text="立即发送目标", command=self.feeder.publish_goal_once).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_frame, text="重置位姿", command=self._reset_pose).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_frame, text="关闭", command=self._close).pack(side=tk.RIGHT)

        ttk.Label(frame, textvariable=self.status_var).pack(anchor=tk.W)

        self.log_text = tk.Text(frame, height=14, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self._append_log("发布器已启动，修改参数后请点击“应用参数”。")
        self._refresh()

    def _add_spinbox(self, parent, label: str, variable, row: int) -> None:
        from tkinter import ttk

        ttk.Label(parent, text=label).grid(row=row // 3, column=(row % 3) * 2, sticky="w", padx=(0, 8), pady=4)
        spin = ttk.Spinbox(
            parent,
            textvariable=variable,
            from_=-999.0,
            to=999.0,
            increment=0.1,
            width=12,
        )
        spin.grid(row=row // 3, column=(row % 3) * 2 + 1, sticky="w", padx=(0, 24), pady=4)

    def _append_log(self, line: str) -> None:
        self.log_text.configure(state=self.tk.NORMAL)
        self.log_text.insert(self.tk.END, f"{time.strftime('%H:%M:%S')}  {line}\n")
        self.log_text.see(self.tk.END)
        self.log_text.configure(state=self.tk.DISABLED)

    def _push_state(self) -> None:
        self.feeder.update(
            pose_x=self.pose_x.get(),
            pose_y=self.pose_y.get(),
            yaw=self.yaw.get(),
            linear_x=self.linear_x.get(),
            linear_y=self.linear_y.get(),
            angular_z=self.angular_z.get(),
            goal_x=self.goal_x.get(),
            goal_y=self.goal_y.get(),
            goal_yaw=self.goal_yaw.get(),
            obstacle_stop=self.obstacle_stop.get(),
            auto_motion=self.auto_motion.get(),
            publish_goal_each_second=self.goal_repeat.get(),
        )
        self._append_log("已应用当前参数。")

    def _reset_pose(self) -> None:
        self.pose_x.set(0.0)
        self.pose_y.set(0.0)
        self.yaw.set(0.0)
        self._push_state()
        self._append_log("位姿已重置到原点。")

    def _refresh(self) -> None:
        snap = self.feeder.snapshot()
        self.status_var.set(
            f"发布中: odom={self.feeder.args.odom_topic}, cmd={self.feeder.args.cmd_topic}, "
            f"goal={self.feeder.args.goal_topic}, obstacle={self.feeder.args.obstacle_topic} | "
            f"当前位姿=({snap.pose_x:.2f}, {snap.pose_y:.2f}, yaw={snap.yaw:.2f})"
        )
        self.root.after(300, self._refresh)

    def _close(self) -> None:
        self.root.quit()

    def run(self) -> None:
        self.root.mainloop()


def parse_args() -> argparse.Namespace:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument(
        "--topic-config",
        default=str(DEFAULT_TOPIC_CONFIG),
        help="YAML file that defines the platform topic/frame mapping.",
    )
    bootstrap_args, remaining_argv = bootstrap.parse_known_args()
    topic_mapping = load_topic_mapping(Path(bootstrap_args.topic_config))

    parser = argparse.ArgumentParser(
        description="GUI helper for publishing fake nav topics during offline testing."
    )
    parser.add_argument(
        "--topic-config",
        default=str(DEFAULT_TOPIC_CONFIG),
        help="YAML file that defines the platform topic/frame mapping.",
    )
    parser.add_argument("--odom-topic", default=topic_mapping["odom_topic"])
    parser.add_argument("--cmd-topic", default=topic_mapping["safe_cmd_topic"])
    parser.add_argument("--goal-topic", default=topic_mapping["goal_topic"])
    parser.add_argument("--obstacle-topic", default=topic_mapping["obstacle_stop_topic"])
    parser.add_argument("--frame-id", default=topic_mapping["odom_frame_id"])
    parser.add_argument("--child-frame-id", default=topic_mapping["base_frame_id"])
    parser.add_argument("--odom-rate", type=float, default=10.0)
    parser.add_argument("--cmd-rate", type=float, default=5.0)
    parser.add_argument("--obstacle-rate", type=float, default=2.0)
    args = parser.parse_args(remaining_argv)
    args.topic_mapping = load_topic_mapping(Path(args.topic_config))
    return args


def main() -> int:
    args = parse_args()
    rclpy.init()
    feeder = OfflineNavTestFeeder(args)
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(feeder)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    try:
        gui = FeederGui(feeder)
    except Exception as exc:
        feeder.get_logger().error(f"GUI startup failed: {exc}")
        executor.shutdown()
        feeder.destroy_node()
        rclpy.shutdown()
        spin_thread.join(timeout=1.0)
        return 1

    try:
        gui.run()
    finally:
        executor.shutdown()
        feeder.destroy_node()
        rclpy.shutdown()
        spin_thread.join(timeout=1.0)

    return 0


if __name__ == "__main__":
    sys.exit(main())
