#!/usr/bin/python3

import os
import queue
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional

import tkinter as tk
import yaml
from tkinter import filedialog, messagebox, ttk


WS_ROOT = Path("/home/yangxuan/ros2_ws")
ROS_SETUP = "/opt/ros/humble/setup.bash"
WS_SETUP = str(WS_ROOT / "install" / "setup.bash")
FAST_LIVO_RAW_PCD = WS_ROOT / "src" / "FAST-LIVO2-ROS2" / "Log" / "PCD" / "all_raw_points.pcd"
DEFAULT_MAP_PREFIX = WS_ROOT / "src" / "mid360_nav_demo" / "maps" / "site1"
DEFAULT_MAP_YAML = WS_ROOT / "src" / "mid360_nav_demo" / "maps" / "site1.yaml"
DEFAULT_GLOBAL_PCD = FAST_LIVO_RAW_PCD
DEFAULT_NAV2_PARAMS = WS_ROOT / "src" / "jie_3d_nav" / "octo_planner" / "config" / "nav2_mid360_params.yaml"
DEFAULT_QT_GUI_DIR = WS_ROOT / "src" / "Ros_Qt5_Gui_App"
DEFAULT_RECORD_ROOT = Path("/tmp/nav_tests")


def bash_command(command: str) -> list[str]:
    return ["bash", "-lc", f"source {ROS_SETUP} && source {WS_SETUP} && {command}"]


class ManagedProcess:
    def __init__(
        self,
        name: str,
        command: list[str],
        cwd: Path,
        log_callback: Callable[[str], None],
        on_exit: Callable[[str, int], None],
    ):
        self.name = name
        self.command = command
        self.cwd = cwd
        self.log_callback = log_callback
        self.on_exit = on_exit
        self.process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._wait_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.is_running():
            self.log_callback(f"[{self.name}] 已在运行。")
            return
        self.log_callback(f"[{self.name}] 启动命令: {' '.join(self.command)}")
        self.process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            preexec_fn=os.setsid,
        )
        self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()
        self._wait_thread = threading.Thread(target=self._wait, daemon=True)
        self._wait_thread.start()

    def _read_output(self) -> None:
        if self.process is None or self.process.stdout is None:
            return
        for line in self.process.stdout:
            self.log_callback(f"[{self.name}] {line.rstrip()}")

    def _wait(self) -> None:
        if self.process is None:
            return
        return_code = self.process.wait()
        self.on_exit(self.name, return_code)

    def stop(self) -> None:
        if not self.is_running():
            return
        assert self.process is not None
        self.log_callback(f"[{self.name}] 正在停止...")
        os.killpg(os.getpgid(self.process.pid), signal.SIGINT)

    def kill(self) -> None:
        if not self.is_running():
            return
        assert self.process is not None
        self.log_callback(f"[{self.name}] 正在强制终止...")
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None


class NavOpsConsole:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("导航总控上位机")
        self.root.geometry("1100x860")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._ui_queue: "queue.Queue[Callable[[], None]]" = queue.Queue()

        self.processes: Dict[str, ManagedProcess] = {}

        self.mapping_params_var = tk.StringVar(
            value=str(WS_ROOT / "src" / "FAST-LIVO2-ROS2" / "config" / "mid360_lio_only.yaml")
        )
        self.map_prefix_var = tk.StringVar(value=str(DEFAULT_MAP_PREFIX))
        self.export_pcd_var = tk.StringVar(value=str(WS_ROOT / "maps" / "site1_global_map.pcd"))
        self.qt_gui_dir_var = tk.StringVar(value=str(DEFAULT_QT_GUI_DIR))
        self.nav_map_yaml_var = tk.StringVar(value=str(DEFAULT_MAP_YAML))
        self.nav_global_pcd_var = tk.StringVar(value=str(DEFAULT_GLOBAL_PCD))
        self.nav2_params_file_var = tk.StringVar(value=str(DEFAULT_NAV2_PARAMS))
        self.local_inflation_radius_var = tk.StringVar(value="")
        self.global_inflation_radius_var = tk.StringVar(value="")
        self.nav2_inflation_hint_var = tk.StringVar(value="")
        self.nav_launch_mode_var = tk.StringVar(value="safe")
        self.disable_dynamic_obstacles_var = tk.BooleanVar(value=False)
        self.record_root_var = tk.StringVar(value=str(DEFAULT_RECORD_ROOT))
        self.record_name_var = tk.StringVar(value=f"nav_run_{time.strftime('%Y%m%d_%H%M%S')}")
        self.record_profile_var = tk.StringVar(value="debug")
        self.status_var = tk.StringVar(value="待命")
        self.proc_state_vars = {
            "mapping": tk.StringVar(value="未启动"),
            "nav": tk.StringVar(value="未启动"),
            "recorder": tk.StringVar(value="未启动"),
            "qt_gui": tk.StringVar(value="未启动"),
        }

        self._build()
        self._setup_auto_backfill()
        self.root.after(100, self._drain_ui_queue)

    def _build(self) -> None:
        root = self.root
        frame = ttk.Frame(root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(frame, text="导航总控上位机", font=("TkDefaultFont", 16, "bold"))
        title.pack(anchor=tk.W)
        ttk.Label(
            frame,
            text=(
                "目标：统一进入建图模式、按指定路径保存地图和点云、启动 Qt GUI 编辑地图，"
                "再进入导航和记录模式。"
            ),
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 10))

        self._build_mapping_panel(frame)
        self._build_navigation_panel(frame)
        self._build_status_panel(frame)

        log_frame = ttk.LabelFrame(frame, text="运行日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.log_text = tk.Text(log_frame, height=18, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, textvariable=self.status_var).pack(anchor=tk.W, pady=(8, 0))

    def _build_mapping_panel(self, parent) -> None:
        panel = ttk.LabelFrame(parent, text="阶段 1：建图 / 保存地图", padding=10)
        panel.pack(fill=tk.X, pady=(0, 10))
        panel.columnconfigure(1, weight=1)

        ttk.Label(panel, text="建图参数文件").grid(row=0, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.mapping_params_var).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(panel, text="选择", command=lambda: self._pick_file(self.mapping_params_var, [("YAML", "*.yaml")])).grid(row=0, column=2)

        ttk.Label(panel, text="2D 地图保存前缀").grid(row=1, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.map_prefix_var).grid(row=1, column=1, sticky="ew", padx=6)
        ttk.Button(panel, text="选择", command=self._pick_map_prefix).grid(row=1, column=2)

        ttk.Label(panel, text="点云地图导出路径").grid(row=2, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.export_pcd_var).grid(row=2, column=1, sticky="ew", padx=6)
        ttk.Button(panel, text="选择", command=lambda: self._pick_save_file(self.export_pcd_var, ".pcd", [("PCD", "*.pcd")])).grid(row=2, column=2)

        button_row = ttk.Frame(panel)
        button_row.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(button_row, text="启动建图模式", command=self.start_mapping_mode).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="保存 PGM/YAML", command=self.save_projected_map).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="导出最新点云地图", command=self.export_latest_pcd).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="回填导航路径", command=self.backfill_navigation_paths).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="停止建图模式", command=lambda: self.stop_process("mapping")).pack(side=tk.LEFT)

        ttk.Label(
            panel,
            text=(
                "说明：FAST-LIVO2 建图模式仍会先写到固定的 Log/PCD 目录。"
                "这里通过“导出最新点云地图”把当前 all_raw_points.pcd 复制到你指定的位置，"
                "避免后续再次建图时被覆盖。保存地图或导出点云后，会自动回填导航模式使用的 YAML 和 PCD 路径。"
            ),
            justify=tk.LEFT,
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def _build_navigation_panel(self, parent) -> None:
        panel = ttk.LabelFrame(parent, text="阶段 2：地图编辑 / 导航 / 记录", padding=10)
        panel.pack(fill=tk.X, pady=(0, 10))
        panel.columnconfigure(1, weight=1)

        ttk.Label(panel, text="Qt GUI 目录").grid(row=0, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.qt_gui_dir_var).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(panel, text="选择", command=lambda: self._pick_dir(self.qt_gui_dir_var)).grid(row=0, column=2)

        ttk.Label(panel, text="导航地图 YAML").grid(row=1, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.nav_map_yaml_var).grid(row=1, column=1, sticky="ew", padx=6)
        ttk.Button(panel, text="选择", command=lambda: self._pick_file(self.nav_map_yaml_var, [("YAML", "*.yaml")])).grid(row=1, column=2)

        ttk.Label(panel, text="重定位点云地图").grid(row=2, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.nav_global_pcd_var).grid(row=2, column=1, sticky="ew", padx=6)
        ttk.Button(panel, text="选择", command=lambda: self._pick_file(self.nav_global_pcd_var, [("PCD", "*.pcd")])).grid(row=2, column=2)

        ttk.Label(panel, text="Nav2 参数文件").grid(row=3, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.nav2_params_file_var).grid(row=3, column=1, sticky="ew", padx=6)
        ttk.Button(panel, text="选择", command=lambda: self._pick_file(self.nav2_params_file_var, [("YAML", "*.yaml")])).grid(row=3, column=2)

        ttk.Label(panel, text="局部膨胀半径").grid(row=4, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.local_inflation_radius_var).grid(row=4, column=1, sticky="ew", padx=6)
        ttk.Label(panel, text="单位 m；留空则沿用参数文件").grid(row=4, column=2, sticky="w")

        ttk.Label(panel, text="全局膨胀半径").grid(row=5, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.global_inflation_radius_var).grid(row=5, column=1, sticky="ew", padx=6)
        ttk.Label(panel, textvariable=self.nav2_inflation_hint_var, justify=tk.LEFT).grid(row=5, column=2, sticky="w")

        ttk.Label(panel, text="导航启动模式").grid(row=6, column=0, sticky="w")
        ttk.Combobox(
            panel,
            textvariable=self.nav_launch_mode_var,
            values=["safe", "raw"],
            state="readonly",
        ).grid(row=6, column=1, sticky="w", padx=6)
        ttk.Label(
            panel,
            text="safe=总控安全链，raw=与你手工 online_nav_demo 一致",
            justify=tk.LEFT,
        ).grid(row=6, column=2, sticky="w")

        ttk.Label(panel, text="动态障碍物").grid(row=7, column=0, sticky="w")
        ttk.Checkbutton(
            panel,
            text="关闭动态障碍物更新，只保留静态地图",
            variable=self.disable_dynamic_obstacles_var,
        ).grid(row=7, column=1, columnspan=2, sticky="w", padx=6)

        ttk.Label(panel, text="记录输出目录").grid(row=8, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.record_root_var).grid(row=8, column=1, sticky="ew", padx=6)
        ttk.Button(panel, text="选择", command=lambda: self._pick_dir(self.record_root_var)).grid(row=8, column=2)

        ttk.Label(panel, text="测试名称").grid(row=9, column=0, sticky="w")
        ttk.Entry(panel, textvariable=self.record_name_var).grid(row=9, column=1, sticky="ew", padx=6)
        ttk.Frame(panel).grid(row=9, column=2)

        ttk.Label(panel, text="录制预设").grid(row=10, column=0, sticky="w")
        ttk.Combobox(
            panel,
            textvariable=self.record_profile_var,
            values=["lite", "debug"],
            state="readonly",
        ).grid(row=10, column=1, sticky="w", padx=6)

        button_row = ttk.Frame(panel)
        button_row.grid(row=11, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        ttk.Button(button_row, text="启动 Qt GUI", command=self.start_qt_gui).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="启动导航模式", command=self.start_navigation_mode).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="启动记录器", command=self.start_recorder).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="一键启动导航+记录", command=self.start_nav_and_recorder).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="停止导航模式", command=lambda: self.stop_process("nav")).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="停止记录器", command=lambda: self.stop_process("recorder")).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_row, text="停止 Qt GUI", command=lambda: self.stop_process("qt_gui")).pack(side=tk.LEFT)

    def _build_status_panel(self, parent) -> None:
        panel = ttk.LabelFrame(parent, text="进程状态", padding=10)
        panel.pack(fill=tk.X)

        for idx, key in enumerate(["mapping", "nav", "recorder", "qt_gui"]):
            ttk.Label(panel, text=f"{key}:").grid(row=idx, column=0, sticky="w")
            ttk.Label(panel, textvariable=self.proc_state_vars[key]).grid(row=idx, column=1, sticky="w", padx=(6, 20))

        ttk.Button(panel, text="停止全部", command=self.stop_all_processes).grid(row=0, column=2, rowspan=2, padx=(20, 0))

    def _append_log(self, line: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{timestamp}  {line}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _append_log_threadsafe(self, line: str) -> None:
        self._ui_queue.put(lambda line=line: self._append_log(line))

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)
        self._append_log(text)

    def _set_status_threadsafe(self, text: str) -> None:
        self._ui_queue.put(lambda text=text: self._set_status(text))

    def _set_proc_state(self, key: str, value: str) -> None:
        self.proc_state_vars[key].set(value)

    def _set_proc_state_threadsafe(self, key: str, value: str) -> None:
        self._ui_queue.put(lambda key=key, value=value: self._set_proc_state(key, value))

    def _show_error_threadsafe(self, title: str, message: str) -> None:
        self._ui_queue.put(
            lambda title=title, message=message: messagebox.showerror(title, message)
        )

    def _drain_ui_queue(self) -> None:
        while True:
            try:
                callback = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            callback()
        if self.root.winfo_exists():
            self.root.after(100, self._drain_ui_queue)

    def _pick_file(self, variable: tk.StringVar, filetypes) -> None:
        path = filedialog.askopenfilename(initialdir=str(Path(variable.get()).parent), filetypes=filetypes)
        if path:
            variable.set(path)

    def _pick_save_file(self, variable: tk.StringVar, suffix: str, filetypes) -> None:
        path = filedialog.asksaveasfilename(initialdir=str(Path(variable.get()).parent), filetypes=filetypes)
        if path:
            if not path.endswith(suffix):
                path += suffix
            variable.set(path)

    def _pick_dir(self, variable: tk.StringVar) -> None:
        initial = variable.get() or str(WS_ROOT)
        path = filedialog.askdirectory(initialdir=initial)
        if path:
            variable.set(path)

    def _pick_map_prefix(self) -> None:
        initial = self.map_prefix_var.get()
        path = filedialog.asksaveasfilename(
            title="选择地图保存前缀（不带扩展名）",
            initialdir=str(Path(initial).parent),
            initialfile=Path(initial).name,
        )
        if path:
            for suffix in [".pgm", ".yaml"]:
                if path.endswith(suffix):
                    path = path[: -len(suffix)]
            self.map_prefix_var.set(path)

    def _setup_auto_backfill(self) -> None:
        self.map_prefix_var.trace_add("write", lambda *_args: self._sync_map_yaml_from_prefix())
        self.export_pcd_var.trace_add("write", lambda *_args: self._sync_pcd_path_from_export())
        self.nav2_params_file_var.trace_add("write", lambda *_args: self._refresh_nav2_inflation_hint())
        self._sync_map_yaml_from_prefix()
        self._sync_pcd_path_from_export()
        self._refresh_nav2_inflation_hint()

    def _sync_map_yaml_from_prefix(self) -> None:
        prefix = self.map_prefix_var.get().strip()
        if not prefix:
            return
        self.nav_map_yaml_var.set(str(Path(prefix).with_suffix(".yaml")))

    def _sync_pcd_path_from_export(self) -> None:
        export_path = self.export_pcd_var.get().strip()
        if not export_path:
            return
        self.nav_global_pcd_var.set(export_path)

    def _refresh_nav2_inflation_hint(self) -> None:
        params_path = Path(self.nav2_params_file_var.get().strip())
        if not params_path.exists():
            self.nav2_inflation_hint_var.set("参数文件不存在")
            return
        try:
            with open(params_path, "r", encoding="utf-8") as f:
                params = yaml.safe_load(f) or {}
            local_radius = (
                params["local_costmap"]["local_costmap"]["ros__parameters"]["inflation_layer"][
                    "inflation_radius"
                ]
            )
            global_radius = (
                params["global_costmap"]["global_costmap"]["ros__parameters"]["inflation_layer"][
                    "inflation_radius"
                ]
            )
            self.nav2_inflation_hint_var.set(
                f"文件当前值: local={local_radius} m, global={global_radius} m"
            )
        except Exception as exc:
            self.nav2_inflation_hint_var.set(f"读取膨胀半径失败: {exc}")

    def backfill_navigation_paths(self) -> None:
        self._sync_map_yaml_from_prefix()
        self._sync_pcd_path_from_export()
        self._set_status(
            "已按当前建图结果回填导航路径："
            f"map={self.nav_map_yaml_var.get()} | pcd={self.nav_global_pcd_var.get()}"
        )

    def _ensure_parent_dir(self, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)

    def _register_process(self, key: str, process: ManagedProcess) -> None:
        self.processes[key] = process
        self._set_proc_state(key, "启动中")
        process.start()

    def _on_process_exit(self, name: str, return_code: int) -> None:
        self.root.after(0, lambda: self._handle_process_exit(name, return_code))

    def _handle_process_exit(self, name: str, return_code: int) -> None:
        key = self._process_key_by_name(name)
        if key:
            self._set_proc_state(key, f"已退出 ({return_code})")
        self._append_log(f"[{name}] 进程退出，返回码 {return_code}")

    def _process_key_by_name(self, name: str) -> Optional[str]:
        for key, proc in self.processes.items():
            if proc.name == name:
                return key
        return None

    def start_mapping_mode(self) -> None:
        if "mapping" in self.processes and self.processes["mapping"].is_running():
            self._set_status("建图模式已经在运行。")
            return
        params = Path(self.mapping_params_var.get())
        if not params.exists():
            messagebox.showerror("参数文件不存在", f"找不到建图参数文件：{params}")
            return
        command = bash_command(
            "ros2 launch mid360_nav_demo online_mapping_demo.launch.py "
            f"fast_livo_params:={params} launch_rviz:=true launch_tuning_gui:=true"
        )
        proc = ManagedProcess(
            "mapping_mode",
            command,
            WS_ROOT,
            self._append_log_threadsafe,
            self._on_process_exit,
        )
        self._register_process("mapping", proc)
        self._set_status("建图模式已启动。")

    def save_projected_map(self) -> None:
        prefix = Path(self.map_prefix_var.get())
        self._ensure_parent_dir(prefix)
        command = bash_command(
            "ros2 launch mid360_nav_demo save_projected_map.launch.py "
            f"map_prefix:={prefix}"
        )
        self._append_log(f"[save_map] 保存地图到 {prefix}.pgm/.yaml")

        def worker():
            try:
                result = subprocess.run(
                    command,
                    cwd=str(WS_ROOT),
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                if result.stdout.strip():
                    self._append_log_threadsafe(
                        "[save_map] " + result.stdout.strip().replace("\n", "\n[save_map] ")
                    )
                self._ui_queue.put(
                    lambda prefix=prefix: self.nav_map_yaml_var.set(str(prefix.with_suffix(".yaml")))
                )
                self._set_status_threadsafe(
                    f"2D 地图已保存到 {prefix}.pgm/.yaml，已自动回填导航地图路径。"
                )
            except subprocess.CalledProcessError as exc:
                output = exc.stdout.strip() if exc.stdout else str(exc)
                self._show_error_threadsafe("保存地图失败", output)

        threading.Thread(target=worker, daemon=True).start()

    def export_latest_pcd(self) -> None:
        source = FAST_LIVO_RAW_PCD
        target = Path(self.export_pcd_var.get())
        if not source.exists():
            messagebox.showerror("点云地图不存在", f"当前还没有找到最新点云地图：{source}")
            return
        self._ensure_parent_dir(target)
        shutil.copy2(source, target)
        self.nav_global_pcd_var.set(str(target))
        self._set_status(f"已导出点云地图到 {target}，已自动回填重定位点云路径。")

    def start_qt_gui(self) -> None:
        if "qt_gui" in self.processes and self.processes["qt_gui"].is_running():
            self._set_status("Qt GUI 已在运行。")
            return
        gui_dir = Path(self.qt_gui_dir_var.get())
        if not gui_dir.exists():
            messagebox.showerror("Qt GUI 目录不存在", f"找不到目录：{gui_dir}")
            return
        command = bash_command(
            f"{WS_ROOT / 'src' / 'agt_nav_console' / 'scripts' / 'start_qt_gui.sh'} {gui_dir}"
        )
        proc = ManagedProcess(
            "qt_gui",
            command,
            WS_ROOT,
            self._append_log_threadsafe,
            self._on_process_exit,
        )
        self._register_process("qt_gui", proc)
        self._set_status("Qt GUI 已启动。")

    def start_navigation_mode(self) -> None:
        if "nav" in self.processes and self.processes["nav"].is_running():
            self._set_status("导航模式已在运行。")
            return
        map_yaml = Path(self.nav_map_yaml_var.get())
        global_pcd = Path(self.nav_global_pcd_var.get())
        nav2_params = Path(self.nav2_params_file_var.get())
        launch_mode = self.nav_launch_mode_var.get().strip() or "safe"
        disable_dynamic_obstacles = self.disable_dynamic_obstacles_var.get()
        local_inflation_radius = self.local_inflation_radius_var.get().strip()
        global_inflation_radius = self.global_inflation_radius_var.get().strip()
        if not map_yaml.exists():
            messagebox.showerror("导航地图不存在", f"找不到地图 YAML：{map_yaml}")
            return
        if not global_pcd.exists():
            messagebox.showerror("重定位地图不存在", f"找不到点云地图：{global_pcd}")
            return
        if not nav2_params.exists():
            messagebox.showerror("Nav2 参数文件不存在", f"找不到 Nav2 参数文件：{nav2_params}")
            return
        for label, value in [
            ("局部膨胀半径", local_inflation_radius),
            ("全局膨胀半径", global_inflation_radius),
        ]:
            if not value:
                continue
            try:
                float(value)
            except ValueError:
                messagebox.showerror("膨胀半径格式错误", f"{label} 需要填写数字，当前值：{value}")
                return
        disable_dynamic_obstacles_arg = (
            " disable_dynamic_obstacles:=true" if disable_dynamic_obstacles else ""
        )
        local_inflation_arg = (
            f" local_inflation_radius:={local_inflation_radius}" if local_inflation_radius else ""
        )
        global_inflation_arg = (
            f" global_inflation_radius:={global_inflation_radius}" if global_inflation_radius else ""
        )
        if launch_mode == "raw":
            command = bash_command(
                "ros2 launch mid360_nav_demo online_nav_demo.launch.py "
                f"map:={map_yaml} "
                f"nav2_params_file:={nav2_params} "
                f"global_map_pcd:={global_pcd} "
                "launch_rviz:=true launch_cmd_bridge:=true "
                "launch_chassis:=true bridge_publish_rate:=30.0"
                f"{disable_dynamic_obstacles_arg}{local_inflation_arg}{global_inflation_arg}"
            )
        else:
            command = bash_command(
                "ros2 launch agt_nav_console safe_online_nav_demo.launch.py "
                f"map:={map_yaml} "
                f"nav2_params_file:={nav2_params} "
                f"global_map_pcd:={global_pcd} "
                "launch_rviz:=true launch_chassis:=true bridge_publish_rate:=30.0"
                f"{disable_dynamic_obstacles_arg}{local_inflation_arg}{global_inflation_arg}"
            )
        proc = ManagedProcess(
            "nav_mode",
            command,
            WS_ROOT,
            self._append_log_threadsafe,
            self._on_process_exit,
        )
        self._register_process("nav", proc)
        self._set_status(
            "导航模式已启动"
            f"（{launch_mode}，dynamic_obstacles={'off' if disable_dynamic_obstacles else 'on'}，"
            f"local_inflation={local_inflation_radius or 'yaml'}，"
            f"global_inflation={global_inflation_radius or 'yaml'}）。"
        )

    def start_recorder(self) -> None:
        if "recorder" in self.processes and self.processes["recorder"].is_running():
            self._set_status("记录器已在运行。")
            return
        output_root = Path(self.record_root_var.get())
        output_root.mkdir(parents=True, exist_ok=True)
        test_name = self.record_name_var.get().strip()
        profile = self.record_profile_var.get().strip() or "debug"
        command = bash_command(
            "ros2 run agt_nav_console nav_test_recorder "
            f"--gui --profile {profile} "
            f"--output-root {output_root} "
            f"--test-name {test_name}"
        )
        proc = ManagedProcess(
            "nav_test_recorder",
            command,
            WS_ROOT,
            self._append_log_threadsafe,
            self._on_process_exit,
        )
        self._register_process("recorder", proc)
        self._set_status("导航记录器已启动。")

    def start_nav_and_recorder(self) -> None:
        self.start_navigation_mode()
        self.root.after(1500, self.start_recorder)

    def stop_process(self, key: str) -> None:
        proc = self.processes.get(key)
        if proc is None or not proc.is_running():
            self._set_status(f"{key} 当前未运行。")
            return
        proc.stop()
        self._set_proc_state(key, "停止中")

    def stop_all_processes(self) -> None:
        for key in ["recorder", "qt_gui", "nav", "mapping"]:
            proc = self.processes.get(key)
            if proc and proc.is_running():
                proc.stop()
                self._set_proc_state(key, "停止中")
        self._set_status("已发送停止信号给全部进程。")

    def _on_close(self) -> None:
        running = [key for key, proc in self.processes.items() if proc.is_running()]
        if running:
            if not messagebox.askyesno("退出确认", "仍有进程在运行，是否停止全部并退出？"):
                return
            self.stop_all_processes()
            self.root.after(800, self.root.destroy)
            return
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    app = NavOpsConsole()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
