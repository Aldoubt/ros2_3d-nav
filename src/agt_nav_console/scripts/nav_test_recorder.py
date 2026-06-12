#!/usr/bin/python3

import argparse
import csv
import math
import os
import signal
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import rclpy
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import Bool
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_TOPIC_CONFIG = SCRIPT_DIR.parent / "config" / "topic_mapping.yaml"


def load_topic_mapping(config_path: Path) -> Dict[str, str]:
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except OSError as exc:
        raise SystemExit(f"Failed to read topic config: {config_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Topic config must be a YAML mapping: {config_path}")
    return {str(key): value for key, value in data.items()}


def build_topic_profiles(topic_mapping: Dict[str, str]) -> Dict[str, list[str]]:
    default_topics = [
        topic_mapping["odom_topic"],
        topic_mapping["safe_cmd_topic"],
        topic_mapping["goal_topic"],
        topic_mapping["obstacle_stop_topic"],
    ]
    return {
        "lite": list(default_topics),
        "debug": list(default_topics)
        + [
            topic_mapping["cloud_topic"],
            topic_mapping["global_path_topic"],
            topic_mapping["local_path_topic"],
        ],
    }


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def format_float(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def ros_time_to_float(msg) -> float:
    return float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


class SystemMonitor:
    def __init__(self, disk_path: Path):
        self.disk_path = disk_path
        self._last_cpu_total: Optional[int] = None
        self._last_cpu_idle: Optional[int] = None

    def _read_cpu_percent(self) -> Optional[float]:
        try:
            with open("/proc/stat", "r", encoding="utf-8") as handle:
                fields = handle.readline().strip().split()
        except OSError:
            return None
        if len(fields) < 5 or fields[0] != "cpu":
            return None
        values = [int(item) for item in fields[1:]]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        if self._last_cpu_total is None or self._last_cpu_idle is None:
            self._last_cpu_total = total
            self._last_cpu_idle = idle
            return None
        total_delta = total - self._last_cpu_total
        idle_delta = idle - self._last_cpu_idle
        self._last_cpu_total = total
        self._last_cpu_idle = idle
        if total_delta <= 0:
            return None
        return max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))

    def _read_mem_percent(self) -> Optional[float]:
        mem_total = None
        mem_available = None
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("MemTotal:"):
                        mem_total = int(line.split()[1]) * 1024
                    elif line.startswith("MemAvailable:"):
                        mem_available = int(line.split()[1]) * 1024
                    if mem_total is not None and mem_available is not None:
                        break
        except OSError:
            return None
        if not mem_total or mem_available is None:
            return None
        used = mem_total - mem_available
        return max(0.0, min(100.0, used * 100.0 / mem_total))

    def _read_disk_percent(self) -> Optional[float]:
        try:
            usage = shutil.disk_usage(self.disk_path)
        except OSError:
            return None
        if usage.total <= 0:
            return None
        return usage.used * 100.0 / usage.total

    def sample(self) -> Dict[str, Optional[float]]:
        return {
            "cpu_percent": self._read_cpu_percent(),
            "mem_percent": self._read_mem_percent(),
            "disk_percent": self._read_disk_percent(),
        }


def format_percent(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}%"


def format_bytes(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{num_bytes} B"


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "-"
    total = max(0, int(seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def resource_severity(value: Optional[float], warn: float, crit: float) -> str:
    if value is None:
        return "unknown"
    if value >= crit:
        return "critical"
    if value >= warn:
        return "warning"
    return "normal"


class NavTestRecorder(Node):
    def __init__(self, args: argparse.Namespace, test_dir: Path):
        super().__init__("nav_test_recorder")
        self.args = args
        self.test_dir = test_dir
        self.metrics_path = test_dir / "metrics.csv"
        self.events_path = test_dir / "events.csv"
        self.metadata_path = test_dir / "metadata.yaml"
        self.bag_path = test_dir / "bag"
        self.started_wall_time = time.time()
        self.latest_cmd = {"linear_x": None, "linear_y": None, "angular_z": None}
        self.latest_goal = {"x": None, "y": None, "z": None, "yaw": None}
        self.latest_obstacle_stop = False
        self.latest_pose = {"x": None, "y": None, "z": None, "yaw": None}
        self.latest_twist = {
            "linear_x": None,
            "linear_y": None,
            "linear_z": None,
            "angular_z": None,
        }
        self.topic_last_seen: Dict[str, Optional[float]] = {
            args.odom_topic: None,
            args.cmd_vel_topic: None,
            args.goal_topic: None,
            args.obstacle_topic: None,
        }
        self.metrics_count = 0
        self.last_event = "session_created"
        self.last_event_detail = ""
        self.recording_started_at: Optional[float] = None
        self.session_created = False
        self._csv_lock = threading.Lock()
        self._bag_process: Optional[subprocess.Popen] = None
        self._stopping = False

        self._metrics_file = self.metrics_path.open("w", newline="", encoding="utf-8")
        self._metrics_writer = csv.writer(self._metrics_file)
        self._metrics_writer.writerow(
            [
                "stamp",
                "wall_time",
                "pose_x",
                "pose_y",
                "pose_z",
                "yaw",
                "linear_vel_x",
                "linear_vel_y",
                "linear_vel_z",
                "angular_vel_z",
                "cmd_linear_x",
                "cmd_linear_y",
                "cmd_angular_z",
                "goal_x",
                "goal_y",
                "goal_z",
                "goal_yaw",
                "obstacle_stop",
            ]
        )
        self._metrics_file.flush()

        self._events_file = self.events_path.open("w", newline="", encoding="utf-8")
        self._events_writer = csv.writer(self._events_file)
        self._events_writer.writerow(["wall_time", "relative_time", "event", "detail"])
        self._events_file.flush()

        self._write_metadata(status="initializing")

        self.create_subscription(Odometry, args.odom_topic, self._on_odom, 50)
        self.create_subscription(Twist, args.cmd_vel_topic, self._on_cmd_vel, 50)
        self.create_subscription(PoseStamped, args.goal_topic, self._on_goal, 20)
        self.create_subscription(Bool, args.obstacle_topic, self._on_obstacle, 20)

    def start_bag_recording(self) -> None:
        if self.is_bag_recording():
            return
        bag_cmd = [
            "ros2",
            "bag",
            "record",
            "-o",
            str(self.bag_path),
            *self.args.topics,
        ]
        self.get_logger().info("Starting rosbag: %s" % " ".join(bag_cmd))
        self._bag_process = subprocess.Popen(
            bag_cmd,
            cwd=str(self.test_dir),
            stdout=None,
            stderr=None,
            preexec_fn=os.setsid,
        )
        self.recording_started_at = time.time()
        self._write_metadata(status="recording", bag_command=bag_cmd)

    def stop(self) -> None:
        if self._stopping:
            return
        self._stopping = True
        self._stop_bag_process()
        self._write_metadata(status="finished")
        self._metrics_file.close()
        self._events_file.close()

    def _stop_bag_process(self) -> None:
        if self._bag_process is None:
            return
        if self._bag_process.poll() is not None:
            return
        self.get_logger().info("Stopping rosbag recorder...")
        os.killpg(os.getpgid(self._bag_process.pid), signal.SIGINT)
        try:
            self._bag_process.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            self.get_logger().warning("rosbag did not exit after SIGINT, sending SIGTERM.")
            os.killpg(os.getpgid(self._bag_process.pid), signal.SIGTERM)
            self._bag_process.wait(timeout=5.0)
        self.recording_started_at = None

    def record_event(self, event: str, detail: str = "") -> None:
        wall_time = time.time()
        with self._csv_lock:
            self._events_writer.writerow(
                [
                    f"{wall_time:.6f}",
                    f"{wall_time - self.started_wall_time:.6f}",
                    event,
                    detail,
                ]
            )
            self._events_file.flush()
        self.last_event = event
        self.last_event_detail = detail
        self.get_logger().info(f"Event recorded: {event} {detail}".strip())

    def is_bag_recording(self) -> bool:
        return self._bag_process is not None and self._bag_process.poll() is None

    def start_session(self) -> None:
        if not self.session_created:
            self.record_event("session_created", self.test_dir.name)
            self.session_created = True
        self.start_bag_recording()

    def get_bag_size_bytes(self) -> int:
        total = 0
        if not self.bag_path.exists():
            return 0
        for path in self.bag_path.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def get_status_snapshot(self) -> Dict[str, object]:
        return {
            "test_dir": str(self.test_dir),
            "bag_recording": self.is_bag_recording(),
            "recording_duration": (
                time.time() - self.recording_started_at
                if self.recording_started_at is not None
                else None
            ),
            "bag_size_bytes": self.get_bag_size_bytes(),
            "metrics_count": self.metrics_count,
            "last_event": self.last_event,
            "last_event_detail": self.last_event_detail,
            "latest_pose": dict(self.latest_pose),
            "latest_goal": dict(self.latest_goal),
            "latest_cmd": dict(self.latest_cmd),
            "latest_twist": dict(self.latest_twist),
            "latest_obstacle_stop": self.latest_obstacle_stop,
            "topic_last_seen": dict(self.topic_last_seen),
        }

    def _write_metadata(self, status: str, bag_command: Optional[list] = None) -> None:
        lines = [
            f"test_name: {self.test_dir.name}",
            f"status: {status}",
            f"created_at: {iso_now()}",
            f"host: {socket.gethostname()}",
            f"cwd: {Path.cwd()}",
            f"package: agt_nav_console",
            f"topic_profile: {self.args.profile}",
            f"odom_topic: {self.args.odom_topic}",
            f"cmd_vel_topic: {self.args.cmd_vel_topic}",
            f"goal_topic: {self.args.goal_topic}",
            f"obstacle_topic: {self.args.obstacle_topic}",
            "topics:",
        ]
        for topic in self.args.topics:
            lines.append(f"  - {topic}")
        if bag_command:
            lines.append("bag_command:")
            lines.append(f"  shell: {' '.join(shell_quote(item) for item in bag_command)}")
        lines.extend(
            [
                "artifacts:",
                f"  bag: {self.bag_path.name}",
                f"  metrics: {self.metrics_path.name}",
                f"  events: {self.events_path.name}",
                f"  metadata: {self.metadata_path.name}",
            ]
        )
        self.metadata_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _on_cmd_vel(self, msg: Twist) -> None:
        self.topic_last_seen[self.args.cmd_vel_topic] = time.time()
        self.latest_cmd["linear_x"] = msg.linear.x
        self.latest_cmd["linear_y"] = msg.linear.y
        self.latest_cmd["angular_z"] = msg.angular.z

    def _on_goal(self, msg: PoseStamped) -> None:
        self.topic_last_seen[self.args.goal_topic] = time.time()
        orientation = msg.pose.orientation
        self.latest_goal["x"] = msg.pose.position.x
        self.latest_goal["y"] = msg.pose.position.y
        self.latest_goal["z"] = msg.pose.position.z
        self.latest_goal["yaw"] = quaternion_to_yaw(
            orientation.x, orientation.y, orientation.z, orientation.w
        )

    def _on_obstacle(self, msg: Bool) -> None:
        self.topic_last_seen[self.args.obstacle_topic] = time.time()
        self.latest_obstacle_stop = bool(msg.data)

    def _on_odom(self, msg: Odometry) -> None:
        self.topic_last_seen[self.args.odom_topic] = time.time()
        pose = msg.pose.pose
        twist = msg.twist.twist
        orientation = pose.orientation
        self.latest_pose["x"] = pose.position.x
        self.latest_pose["y"] = pose.position.y
        self.latest_pose["z"] = pose.position.z
        self.latest_pose["yaw"] = quaternion_to_yaw(
            orientation.x, orientation.y, orientation.z, orientation.w
        )
        self.latest_twist["linear_x"] = twist.linear.x
        self.latest_twist["linear_y"] = twist.linear.y
        self.latest_twist["linear_z"] = twist.linear.z
        self.latest_twist["angular_z"] = twist.angular.z
        row = [
            f"{ros_time_to_float(msg):.6f}",
            f"{time.time():.6f}",
            format_float(pose.position.x),
            format_float(pose.position.y),
            format_float(pose.position.z),
            format_float(
                quaternion_to_yaw(
                    orientation.x, orientation.y, orientation.z, orientation.w
                )
            ),
            format_float(twist.linear.x),
            format_float(twist.linear.y),
            format_float(twist.linear.z),
            format_float(twist.angular.z),
            format_float(self.latest_cmd["linear_x"]),
            format_float(self.latest_cmd["linear_y"]),
            format_float(self.latest_cmd["angular_z"]),
            format_float(self.latest_goal["x"]),
            format_float(self.latest_goal["y"]),
            format_float(self.latest_goal["z"]),
            format_float(self.latest_goal["yaw"]),
            "1" if self.latest_obstacle_stop else "0",
        ]
        with self._csv_lock:
            self._metrics_writer.writerow(row)
            self._metrics_file.flush()
            self.metrics_count += 1


def build_topic_list(args: argparse.Namespace) -> list[str]:
    if args.topics:
        return list(dict.fromkeys(args.topics))
    selected = list(args.topic_profiles[args.profile])
    if args.extra_topics:
        selected.extend(args.extra_topics)
    return list(dict.fromkeys(selected))


def parse_args() -> argparse.Namespace:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument(
        "--topic-config",
        default=str(DEFAULT_TOPIC_CONFIG),
        help="YAML file that defines the platform topic/frame mapping.",
    )
    bootstrap_args, remaining_argv = bootstrap.parse_known_args()

    default_topic_mapping = load_topic_mapping(Path(bootstrap_args.topic_config))
    default_topic_profiles = build_topic_profiles(default_topic_mapping)
    parser = argparse.ArgumentParser(
        description="Record navigation test artifacts, rosbag, and manual event marks."
    )
    parser.add_argument(
        "--topic-config",
        default=str(DEFAULT_TOPIC_CONFIG),
        help="YAML file that defines the platform topic/frame mapping.",
    )
    parser.add_argument(
        "--output-root",
        default=str(Path.cwd() / "nav_tests"),
        help="Root directory for all navigation test runs.",
    )
    parser.add_argument(
        "--test-name",
        default="",
        help="Optional test directory name. Defaults to nav_test_YYYYmmdd_HHMMSS.",
    )
    parser.add_argument("--odom-topic", default=default_topic_mapping["odom_topic"])
    parser.add_argument("--cmd-vel-topic", default=default_topic_mapping["safe_cmd_topic"])
    parser.add_argument("--goal-topic", default=default_topic_mapping["goal_topic"])
    parser.add_argument("--obstacle-topic", default=default_topic_mapping["obstacle_stop_topic"])
    parser.add_argument(
        "--profile",
        choices=sorted(default_topic_profiles.keys()),
        default="lite",
        help="Built-in rosbag topic preset. Defaults to lite.",
    )
    parser.add_argument(
        "--topics",
        nargs="+",
        default=None,
        help="Explicit rosbag topic list. Overrides --profile when provided.",
    )
    parser.add_argument(
        "--extra-topics",
        nargs="+",
        default=[],
        help="Additional rosbag topics appended on top of the selected --profile.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch a lightweight GUI for event marks and runtime status.",
    )
    parser.add_argument(
        "--auto-start",
        action="store_true",
        help="Start rosbag recording immediately when GUI mode opens.",
    )
    args = parser.parse_args(remaining_argv)
    args.topic_mapping = load_topic_mapping(Path(args.topic_config))
    args.topic_profiles = build_topic_profiles(args.topic_mapping)
    args.topics = build_topic_list(args)
    return args


def interactive_loop(recorder: NavTestRecorder) -> None:
    help_text = (
        "Commands: start | arrive | fail | obstacle | takeover | note <text> | q"
    )
    print(help_text, flush=True)
    while rclpy.ok():
        try:
            raw = input("> ").strip()
        except EOFError:
            recorder.record_event("q", "stdin closed")
            break
        except KeyboardInterrupt:
            recorder.record_event("q", "keyboard interrupt")
            break

        if not raw:
            continue

        if raw == "q":
            recorder.record_event("q", "user requested stop")
            break

        if raw.startswith("note"):
            detail = raw[4:].strip()
            if not detail:
                detail = input("note> ").strip()
            recorder.record_event("note", detail)
            continue

        if raw in {"start", "arrive", "fail", "obstacle", "takeover"}:
            recorder.record_event(raw)
            continue

        print(help_text, flush=True)


def format_status_age(stamp: Optional[float]) -> str:
    if stamp is None:
        return "waiting"
    age = time.time() - stamp
    if age < 1.0:
        return "fresh"
    return f"{age:.1f}s ago"


class RecorderGui:
    def __init__(self, recorder: NavTestRecorder):
        import tkinter as tk
        from tkinter import ttk

        self.recorder = recorder
        self.monitor = SystemMonitor(recorder.test_dir)
        self.tk = tk
        self.root = tk.Tk()
        self.root.title("导航实验记录器")
        self.root.geometry("860x700")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._stop_requested = False
        self._resource_event_last_emit = {"cpu": 0.0, "mem": 0.0, "disk": 0.0}

        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        self.summary_var = tk.StringVar()
        self.pose_var = tk.StringVar()
        self.goal_var = tk.StringVar()
        self.cmd_var = tk.StringVar()
        self.metrics_var = tk.StringVar()
        self.bag_var = tk.StringVar()
        self.profile_var = tk.StringVar()
        self.topics_var = tk.StringVar()
        self.note_var = tk.StringVar()
        self.last_event_var = tk.StringVar()
        self.resource_var = tk.StringVar()
        self.warning_var = tk.StringVar()
        self.record_button_var = tk.StringVar(value="开始录制")
        self.topic_vars = {
            recorder.args.odom_topic: tk.StringVar(),
            recorder.args.cmd_vel_topic: tk.StringVar(),
            recorder.args.goal_topic: tk.StringVar(),
            recorder.args.obstacle_topic: tk.StringVar(),
        }

        ttk.Label(frame, text="导航实验记录器", font=("TkDefaultFont", 14, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, textvariable=self.summary_var).pack(anchor=tk.W, pady=(6, 2))
        ttk.Label(frame, textvariable=self.metrics_var).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(frame, textvariable=self.profile_var).pack(anchor=tk.W, pady=(0, 2))
        ttk.Label(frame, textvariable=self.topics_var, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 8))

        help_frame = ttk.LabelFrame(frame, text="使用说明", padding=10)
        help_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            help_frame,
            text=(
                "1. 点击“开始记录”标记导航起点。\n"
                "2. 导航结束时点击“到达目标”，异常时点击“任务失败 / 障碍触发 / 人工接管”。\n"
                "3. 备注输入框可记录现场现象，再点“添加备注”。\n"
                "4. 结束实验时点击“停止并保存”，自动停止 rosbag 并写入全部文件。"
            ),
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        state_frame = ttk.LabelFrame(frame, text="运行状态", padding=10)
        state_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(state_frame, textvariable=self.pose_var).pack(anchor=tk.W)
        ttk.Label(state_frame, textvariable=self.goal_var).pack(anchor=tk.W)
        ttk.Label(state_frame, textvariable=self.cmd_var).pack(anchor=tk.W)
        ttk.Label(state_frame, textvariable=self.bag_var).pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(state_frame, textvariable=self.last_event_var).pack(anchor=tk.W, pady=(4, 0))
        self.resource_label = self.tk.Label(state_frame, textvariable=self.resource_var, anchor="w")
        self.resource_label.pack(anchor=tk.W, pady=(4, 0))
        self.warning_label = self.tk.Label(state_frame, textvariable=self.warning_var, anchor="w")
        self.warning_label.pack(anchor=tk.W, pady=(4, 0))

        topic_frame = ttk.LabelFrame(frame, text="Topic 心跳", padding=10)
        topic_frame.pack(fill=tk.X, pady=(0, 10))
        for topic, var in self.topic_vars.items():
            ttk.Label(topic_frame, textvariable=var).pack(anchor=tk.W)

        event_frame = ttk.LabelFrame(frame, text="事件标记", padding=10)
        event_frame.pack(fill=tk.X, pady=(0, 10))
        button_row = ttk.Frame(event_frame)
        button_row.pack(fill=tk.X)
        button_specs = [
            ("开始记录", "start"),
            ("到达目标", "arrive"),
            ("任务失败", "fail"),
            ("障碍触发", "obstacle"),
            ("人工接管", "takeover"),
        ]
        for text, event_name in button_specs:
            ttk.Button(
                button_row,
                text=text,
                command=lambda event_name=event_name: self._record_event(event_name),
            ).pack(side=tk.LEFT, padx=(0, 8))

        note_row = ttk.Frame(event_frame)
        note_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Entry(note_row, textvariable=self.note_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(note_row, text="添加备注", command=self._record_note).pack(side=tk.LEFT)

        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X)
        ttk.Button(
            action_frame,
            textvariable=self.record_button_var,
            command=self._toggle_recording,
        ).pack(side=tk.LEFT)
        ttk.Button(action_frame, text="停止并保存", command=self._on_close).pack(side=tk.RIGHT)

        self.log_text = tk.Text(frame, height=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self._append_log(f"输出目录: {self.recorder.test_dir}")
        self._refresh()

    def _record_event(self, event_name: str) -> None:
        self.recorder.record_event(event_name)
        self._append_log(f"事件: {event_name}")

    def _record_note(self) -> None:
        detail = self.note_var.get().strip()
        if not detail:
            return
        self.recorder.record_event("note", detail)
        self._append_log(f"备注: {detail}")
        self.note_var.set("")

    def _toggle_recording(self) -> None:
        if self.recorder.is_bag_recording():
            self._append_log("结束录制并准备保存。")
            self._on_close()
            return
        self.recorder.start_session()
        self.recorder.record_event("start")
        self._append_log("开始录制。")

    def _append_log(self, line: str) -> None:
        self.log_text.configure(state=self.tk.NORMAL)
        self.log_text.insert(self.tk.END, f"{iso_now()}  {line}\n")
        self.log_text.see(self.tk.END)
        self.log_text.configure(state=self.tk.DISABLED)

    def _refresh(self) -> None:
        snapshot = self.recorder.get_status_snapshot()
        bag_state = "录制中" if snapshot["bag_recording"] else "已停止"
        self.record_button_var.set("结束录制并保存" if snapshot["bag_recording"] else "开始录制")
        self.summary_var.set(
            f"测试名: {self.recorder.test_dir.name} | rosbag: {bag_state} | 输出目录: {self.recorder.test_dir}"
        )
        self.metrics_var.set(
            f"metrics 行数: {snapshot['metrics_count']} | 障碍急停: {snapshot['latest_obstacle_stop']}"
        )
        self.profile_var.set(
            f"录制预设: {self.recorder.args.profile} | rosbag 话题数: {len(self.recorder.args.topics)}"
        )
        self.topics_var.set(
            "录制话题: " + " | ".join(self.recorder.args.topics)
        )
        self.bag_var.set(
            "录制信息: "
            f"时长={format_duration(snapshot['recording_duration'])} | "
            f"bag 大小={format_bytes(snapshot['bag_size_bytes'])}"
        )
        pose = snapshot["latest_pose"]
        goal = snapshot["latest_goal"]
        cmd = snapshot["latest_cmd"]
        self.pose_var.set(
            "当前位姿: "
            f"x={format_float(pose['x']) or '-'} "
            f"y={format_float(pose['y']) or '-'} "
            f"yaw={format_float(pose['yaw']) or '-'}"
        )
        self.goal_var.set(
            "当前目标: "
            f"x={format_float(goal['x']) or '-'} "
            f"y={format_float(goal['y']) or '-'} "
            f"yaw={format_float(goal['yaw']) or '-'}"
        )
        self.cmd_var.set(
            "安全速度: "
            f"vx={format_float(cmd['linear_x']) or '-'} "
            f"vy={format_float(cmd['linear_y']) or '-'} "
            f"wz={format_float(cmd['angular_z']) or '-'}"
        )
        last_detail = snapshot["last_event_detail"]
        last_event_line = snapshot["last_event"]
        if last_detail:
            last_event_line += f" ({last_detail})"
        self.last_event_var.set(f"最近事件: {last_event_line}")
        for topic, var in self.topic_vars.items():
            var.set(f"{topic}: {format_status_age(snapshot['topic_last_seen'][topic])}")
        resources = self.monitor.sample()
        self.resource_var.set(
            "系统资源: "
            f"CPU={format_percent(resources['cpu_percent'])} | "
            f"内存={format_percent(resources['mem_percent'])} | "
            f"磁盘={format_percent(resources['disk_percent'])}"
        )
        cpu_state = resource_severity(resources["cpu_percent"], 70.0, 90.0)
        mem_state = resource_severity(resources["mem_percent"], 75.0, 85.0)
        disk_state = resource_severity(resources["disk_percent"], 75.0, 85.0)
        warnings = []
        if cpu_state == "critical":
            warnings.append("CPU占用过高")
        elif cpu_state == "warning":
            warnings.append("CPU占用偏高")
        if mem_state == "critical":
            warnings.append("内存占用过高")
        elif mem_state == "warning":
            warnings.append("内存占用偏高")
        if disk_state == "critical":
            warnings.append("磁盘占用过高")
        elif disk_state == "warning":
            warnings.append("磁盘占用偏高")
        self.warning_var.set("系统提醒: " + ("；".join(warnings) if warnings else "资源正常"))
        overall_state = "normal"
        if "critical" in {cpu_state, mem_state, disk_state}:
            overall_state = "critical"
        elif "warning" in {cpu_state, mem_state, disk_state}:
            overall_state = "warning"
        color_map = {
            "normal": "#15803d",
            "warning": "#b45309",
            "critical": "#b91c1c",
            "unknown": "#475569",
        }
        self.resource_label.configure(fg=color_map[overall_state])
        self.warning_label.configure(fg=color_map[overall_state])
        self._maybe_record_resource_alert("cpu", resources["cpu_percent"], cpu_state)
        self._maybe_record_resource_alert("mem", resources["mem_percent"], mem_state)
        self._maybe_record_resource_alert("disk", resources["disk_percent"], disk_state)
        if not self._stop_requested:
            self.root.after(400, self._refresh)

    def _maybe_record_resource_alert(
        self,
        resource_name: str,
        value: Optional[float],
        severity: str,
    ) -> None:
        if severity not in {"warning", "critical"} or value is None:
            return
        now = time.time()
        if now - self._resource_event_last_emit[resource_name] < 30.0:
            return
        detail = f"{resource_name}={value:.1f}% severity={severity}"
        self.recorder.record_event("resource_warn", detail)
        self._append_log(f"系统资源告警: {detail}")
        self._resource_event_last_emit[resource_name] = now

    def _on_close(self) -> None:
        if self._stop_requested:
            return
        self._stop_requested = True
        self.recorder.record_event("q", "gui requested stop")
        self.root.quit()

    def run(self) -> None:
        self.root.mainloop()


def run_interaction(recorder: NavTestRecorder, use_gui: bool) -> None:
    if not use_gui:
        interactive_loop(recorder)
        return

    try:
        gui = RecorderGui(recorder)
    except Exception as exc:
        recorder.get_logger().warning(
            f"GUI startup failed ({exc}), falling back to terminal mode."
        )
        interactive_loop(recorder)
        return
    gui.run()


def reserve_test_dir(output_root: str, requested_test_name: Optional[str]) -> Path:
    root_dir = Path(output_root).expanduser().resolve()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = requested_test_name or f"nav_test_{timestamp}"

    candidate = root_dir / base_name
    if not candidate.exists():
        candidate.mkdir(parents=True, exist_ok=False)
        return candidate

    for index in range(1, 1000):
        suffix = f"{index:02d}_{timestamp}"
        candidate = root_dir / f"{base_name}_{suffix}"
        if candidate.exists():
            continue
        candidate.mkdir(parents=True, exist_ok=False)
        return candidate

    raise RuntimeError(
        f"Could not allocate a unique test directory under {root_dir} for base name {base_name}"
    )


def main() -> int:
    args = parse_args()
    test_dir = reserve_test_dir(args.output_root, args.test_name)

    rclpy.init()
    recorder = NavTestRecorder(args, test_dir)
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(recorder)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    try:
        if args.test_name and test_dir.name != args.test_name:
            recorder.get_logger().warning(
                f"Requested test directory already existed, switched to: {test_dir.name}"
            )
        if not args.gui or args.auto_start:
            recorder.start_session()
        run_interaction(recorder, args.gui)
    finally:
        recorder.stop()
        executor.shutdown()
        recorder.destroy_node()
        rclpy.shutdown()
        spin_thread.join(timeout=1.0)
        print(f"Artifacts saved to: {test_dir}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
