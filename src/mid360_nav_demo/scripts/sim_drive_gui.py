#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk

import rclpy
from geometry_msgs.msg import Twist


class SimDriveGui:
    def __init__(self, root):
        self.root = root
        self.root.title("Gazebo Sim Drive")
        self.node = rclpy.create_node("sim_drive_gui")
        self.publisher = self.node.create_publisher(Twist, "/cmd_vel_chassis", 10)

        self.linear = tk.DoubleVar(value=0.0)
        self.angular = tk.DoubleVar(value=0.0)
        self.step_linear = tk.DoubleVar(value=0.25)
        self.step_angular = tk.DoubleVar(value=0.6)
        self.status = tk.StringVar(value="Publishing /cmd_vel_chassis")

        self._build()
        self._publish_loop()

    def _build(self):
        self.root.columnconfigure(0, weight=1)

        frame = ttk.LabelFrame(self.root, text="Velocity")
        frame.grid(row=0, column=0, padx=10, pady=8, sticky="ew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="linear x").grid(row=0, column=0, sticky="w")
        ttk.Scale(frame, from_=-1.0, to=1.0, variable=self.linear).grid(
            row=0, column=1, sticky="ew", padx=6
        )
        ttk.Label(frame, textvariable=self.linear).grid(row=0, column=2, sticky="e")

        ttk.Label(frame, text="angular z").grid(row=1, column=0, sticky="w")
        ttk.Scale(frame, from_=-2.0, to=2.0, variable=self.angular).grid(
            row=1, column=1, sticky="ew", padx=6
        )
        ttk.Label(frame, textvariable=self.angular).grid(row=1, column=2, sticky="e")

        step = ttk.LabelFrame(self.root, text="Step")
        step.grid(row=1, column=0, padx=10, pady=6, sticky="ew")
        ttk.Label(step, text="linear").grid(row=0, column=0, sticky="w")
        ttk.Entry(step, textvariable=self.step_linear, width=8).grid(row=0, column=1)
        ttk.Label(step, text="angular").grid(row=0, column=2, sticky="w", padx=(10, 0))
        ttk.Entry(step, textvariable=self.step_angular, width=8).grid(row=0, column=3)

        buttons = ttk.LabelFrame(self.root, text="Drive")
        buttons.grid(row=2, column=0, padx=10, pady=8, sticky="ew")
        for col in range(3):
            buttons.columnconfigure(col, weight=1)

        ttk.Button(buttons, text="Forward", command=self.forward).grid(
            row=0, column=1, sticky="ew", padx=3, pady=3
        )
        ttk.Button(buttons, text="Left", command=self.left).grid(
            row=1, column=0, sticky="ew", padx=3, pady=3
        )
        ttk.Button(buttons, text="STOP", command=self.stop).grid(
            row=1, column=1, sticky="ew", padx=3, pady=3
        )
        ttk.Button(buttons, text="Right", command=self.right).grid(
            row=1, column=2, sticky="ew", padx=3, pady=3
        )
        ttk.Button(buttons, text="Backward", command=self.backward).grid(
            row=2, column=1, sticky="ew", padx=3, pady=3
        )

        ttk.Label(self.root, textvariable=self.status).grid(
            row=3, column=0, sticky="ew", padx=10, pady=6
        )

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def forward(self):
        self.linear.set(self.step_linear.get())
        self.angular.set(0.0)

    def backward(self):
        self.linear.set(-self.step_linear.get())
        self.angular.set(0.0)

    def left(self):
        self.angular.set(self.step_angular.get())

    def right(self):
        self.angular.set(-self.step_angular.get())

    def stop(self):
        self.linear.set(0.0)
        self.angular.set(0.0)

    def _publish_loop(self):
        msg = Twist()
        msg.linear.x = float(self.linear.get())
        msg.angular.z = float(self.angular.get())
        self.publisher.publish(msg)
        self.root.after(50, self._publish_loop)

    def close(self):
        self.stop()
        for _ in range(5):
            msg = Twist()
            self.publisher.publish(msg)
        self.node.destroy_node()
        rclpy.shutdown()
        self.root.destroy()


def main():
    rclpy.init()
    root = tk.Tk()
    SimDriveGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
