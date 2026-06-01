#!/usr/bin/env python3

import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


PARAMS = [
    ("pointcloud_min_z", -0.20, 1.00, 0.01),
    ("occupancy_min_z", -0.20, 1.00, 0.01),
    ("pointcloud_max_z", 0.20, 3.00, 0.05),
    ("occupancy_max_z", 0.20, 3.00, 0.05),
]


class OctomapTuningGui:
    def __init__(self, root):
        self.root = root
        self.root.title("MID360 Octomap Tuning")
        self.node_name = tk.StringVar(value="/octomap_server")
        self.map_topic = tk.StringVar(value="/projected_map")
        self.map_prefix = tk.StringVar(
            value="/home/yangxuan/ros2_ws/src/mid360_nav_demo/maps/tuned_map"
        )
        self.timeout_sec = tk.StringVar(value="20.0")
        self.filter_speckles = tk.BooleanVar(value=True)
        self.filter_ground = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Ready")
        self.vars = {}
        self.labels = {}

        self._build()
        self.refresh_params()

    def _build(self):
        root = self.root
        root.columnconfigure(0, weight=1)

        target = ttk.LabelFrame(root, text="Target")
        target.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        target.columnconfigure(1, weight=1)
        ttk.Label(target, text="octomap node").grid(row=0, column=0, sticky="w")
        ttk.Entry(target, textvariable=self.node_name).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        ttk.Button(target, text="Refresh", command=self.refresh_params).grid(
            row=0, column=2, padx=4
        )

        params = ttk.LabelFrame(root, text="Height Filters")
        params.grid(row=1, column=0, sticky="ew", padx=10, pady=8)
        params.columnconfigure(1, weight=1)
        for row, (name, min_v, max_v, step) in enumerate(PARAMS):
            var = tk.DoubleVar(value=0.0)
            self.vars[name] = var
            ttk.Label(params, text=name).grid(row=row, column=0, sticky="w")
            scale = ttk.Scale(
                params,
                from_=min_v,
                to=max_v,
                variable=var,
                command=lambda _value, n=name: self._update_value_label(n),
            )
            scale.grid(row=row, column=1, sticky="ew", padx=6)
            label = ttk.Label(params, width=8)
            label.grid(row=row, column=2, sticky="e")
            self.labels[name] = label
            ttk.Button(
                params,
                text="-",
                width=3,
                command=lambda n=name, s=step: self._nudge(n, -s),
            ).grid(row=row, column=3, padx=1)
            ttk.Button(
                params,
                text="+",
                width=3,
                command=lambda n=name, s=step: self._nudge(n, s),
            ).grid(row=row, column=4, padx=1)

        toggles = ttk.Frame(root)
        toggles.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        ttk.Checkbutton(
            toggles, text="filter_speckles", variable=self.filter_speckles
        ).grid(row=0, column=0, sticky="w", padx=4)
        ttk.Checkbutton(
            toggles, text="filter_ground", variable=self.filter_ground
        ).grid(row=0, column=1, sticky="w", padx=4)

        actions = ttk.LabelFrame(root, text="Actions")
        actions.grid(row=3, column=0, sticky="ew", padx=10, pady=8)
        actions.columnconfigure(0, weight=1)
        ttk.Button(actions, text="Apply Parameters", command=self.apply_params).grid(
            row=0, column=0, sticky="ew", padx=4, pady=4
        )
        ttk.Button(
            actions,
            text="Apply + Reset Octomap",
            command=lambda: self.apply_params(reset_after=True),
        ).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(actions, text="Reset Only", command=self.reset_octomap).grid(
            row=0, column=2, sticky="ew", padx=4, pady=4
        )

        save = ttk.LabelFrame(root, text="Save /projected_map")
        save.grid(row=4, column=0, sticky="ew", padx=10, pady=8)
        save.columnconfigure(1, weight=1)
        ttk.Label(save, text="topic").grid(row=0, column=0, sticky="w")
        ttk.Entry(save, textvariable=self.map_topic).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        ttk.Label(save, text="prefix").grid(row=1, column=0, sticky="w")
        ttk.Entry(save, textvariable=self.map_prefix).grid(
            row=1, column=1, sticky="ew", padx=6
        )
        ttk.Button(save, text="Browse", command=self.browse_prefix).grid(
            row=1, column=2, padx=4
        )
        ttk.Label(save, text="timeout").grid(row=2, column=0, sticky="w")
        ttk.Entry(save, textvariable=self.timeout_sec, width=10).grid(
            row=2, column=1, sticky="w", padx=6
        )
        ttk.Button(save, text="Save PGM/YAML", command=self.save_map).grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=4, pady=4
        )

        status = ttk.Label(root, textvariable=self.status, anchor="w")
        status.grid(row=5, column=0, sticky="ew", padx=10, pady=6)

    def _update_value_label(self, name):
        self.labels[name].configure(text=f"{self.vars[name].get():.2f}")

    def _nudge(self, name, step):
        self.vars[name].set(self.vars[name].get() + step)
        self._update_value_label(name)

    def _run_async(self, title, commands, done=None):
        def worker():
            try:
                for command in commands:
                    self._set_status("Running: " + " ".join(command[:4]))
                    result = subprocess.run(
                        command,
                        check=True,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                    )
                    if result.stdout.strip():
                        print(result.stdout)
                self._set_status(f"{title}: success")
                if done:
                    self.root.after(0, done)
            except subprocess.CalledProcessError as exc:
                output = exc.stdout.strip() if exc.stdout else str(exc)
                self._set_status(f"{title}: failed")
                self.root.after(0, lambda: messagebox.showerror(title, output))

        threading.Thread(target=worker, daemon=True).start()

    def _set_status(self, text):
        self.root.after(0, lambda: self.status.set(text))

    def _param_command(self, name, value):
        return ["ros2", "param", "set", self.node_name.get(), name, str(value)]

    def _bool_value(self, value):
        return "true" if value else "false"

    def refresh_params(self):
        def worker():
            for name, _min_v, _max_v, _step in PARAMS:
                try:
                    result = subprocess.run(
                        ["ros2", "param", "get", self.node_name.get(), name],
                        check=True,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                    )
                    value = float(result.stdout.strip().split()[-1])
                    self.root.after(0, lambda n=name, v=value: self.vars[n].set(v))
                    self.root.after(0, lambda n=name: self._update_value_label(n))
                except Exception:
                    pass
            for name, var in [
                ("filter_speckles", self.filter_speckles),
                ("filter_ground", self.filter_ground),
            ]:
                try:
                    result = subprocess.run(
                        ["ros2", "param", "get", self.node_name.get(), name],
                        check=True,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                    )
                    value = result.stdout.strip().split()[-1].lower() == "true"
                    self.root.after(0, lambda v=value, target=var: target.set(v))
                except Exception:
                    pass
            self._set_status("Refreshed parameters")

        threading.Thread(target=worker, daemon=True).start()

    def apply_params(self, reset_after=False):
        commands = []
        for name in self.vars:
            commands.append(self._param_command(name, f"{self.vars[name].get():.3f}"))
        commands.append(
            self._param_command(
                "filter_speckles", self._bool_value(self.filter_speckles.get())
            )
        )
        commands.append(
            self._param_command(
                "filter_ground", self._bool_value(self.filter_ground.get())
            )
        )
        if reset_after:
            commands.append(
                ["ros2", "service", "call", f"{self.node_name.get()}/reset", "std_srvs/srv/Empty", "{}"]
            )
        self._run_async("Apply parameters", commands)

    def reset_octomap(self):
        self._run_async(
            "Reset octomap",
            [["ros2", "service", "call", f"{self.node_name.get()}/reset", "std_srvs/srv/Empty", "{}"]],
        )

    def browse_prefix(self):
        path = filedialog.asksaveasfilename(
            title="Map prefix without extension",
            initialfile="tuned_map",
            defaultextension="",
        )
        if path:
            for suffix in [".pgm", ".yaml"]:
                if path.endswith(suffix):
                    path = path[: -len(suffix)]
            self.map_prefix.set(path)

    def save_map(self):
        commands = [
            [
                "ros2",
                "run",
                "nav2_map_server",
                "map_saver_cli",
                "-t",
                self.map_topic.get(),
                "-f",
                self.map_prefix.get(),
                "--fmt",
                "pgm",
                "--ros-args",
                "-p",
                "map_subscribe_transient_local:=false",
                "-p",
                f"save_map_timeout:={self.timeout_sec.get()}",
            ]
        ]
        self._run_async("Save map", commands)


def main():
    root = tk.Tk()
    OctomapTuningGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
