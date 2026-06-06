#!/usr/bin/python3

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze nav_test_recorder outputs from metrics.csv and events.csv."
    )
    parser.add_argument(
        "test_dir",
        help="Navigation test directory containing metrics.csv and optional events.csv.",
    )
    return parser.parse_args()


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_float(value: str) -> Optional[float]:
    if value == "":
        return None
    return float(value)


def compute_path_length(rows: List[Dict[str, str]]) -> float:
    total = 0.0
    prev = None
    for row in rows:
        x = parse_float(row.get("pose_x", ""))
        y = parse_float(row.get("pose_y", ""))
        z = parse_float(row.get("pose_z", ""))
        if x is None or y is None or z is None:
            continue
        current = (x, y, z)
        if prev is not None:
            total += math.dist(prev, current)
        prev = current
    return total


def compute_arrival_time(event_rows: List[Dict[str, str]]) -> Optional[float]:
    start_time = None
    for row in event_rows:
        event = row.get("event", "")
        t = parse_float(row.get("relative_time", ""))
        if t is None:
            continue
        if event == "start" and start_time is None:
            start_time = t
        if event == "arrive":
            if start_time is None:
                return t
            return t - start_time
    return None


def compute_max_speed(rows: List[Dict[str, str]]) -> Optional[float]:
    max_speed = None
    for row in rows:
        vx = parse_float(row.get("linear_vel_x", ""))
        vy = parse_float(row.get("linear_vel_y", ""))
        vz = parse_float(row.get("linear_vel_z", ""))
        if vx is None or vy is None or vz is None:
            continue
        speed = math.sqrt(vx * vx + vy * vy + vz * vz)
        if max_speed is None or speed > max_speed:
            max_speed = speed
    return max_speed


def compute_goal_error(rows: List[Dict[str, str]]) -> Optional[float]:
    if not rows:
        return None
    last = rows[-1]
    pose_x = parse_float(last.get("pose_x", ""))
    pose_y = parse_float(last.get("pose_y", ""))
    pose_z = parse_float(last.get("pose_z", ""))
    goal_x = parse_float(last.get("goal_x", ""))
    goal_y = parse_float(last.get("goal_y", ""))
    goal_z = parse_float(last.get("goal_z", ""))
    if None in {pose_x, pose_y, pose_z, goal_x, goal_y, goal_z}:
        return None
    return math.dist(
        (pose_x, pose_y, pose_z),
        (goal_x, goal_y, goal_z),
    )


def format_metric(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.3f}"


def main() -> int:
    args = parse_args()
    test_dir = Path(args.test_dir).expanduser().resolve()
    metrics_rows = load_csv_rows(test_dir / "metrics.csv")
    event_rows = load_csv_rows(test_dir / "events.csv")

    if not metrics_rows:
        print(f"metrics.csv not found or empty in {test_dir}", file=sys.stderr)
        return 1

    path_length = compute_path_length(metrics_rows)
    arrival_time = compute_arrival_time(event_rows)
    max_speed = compute_max_speed(metrics_rows)
    goal_error = compute_goal_error(metrics_rows)

    print(f"test_dir: {test_dir}")
    print(f"path_length_m: {format_metric(path_length)}")
    print(f"arrival_time_s: {format_metric(arrival_time)}")
    print(f"max_speed_mps: {format_metric(max_speed)}")
    print(f"goal_error_m: {format_metric(goal_error)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
