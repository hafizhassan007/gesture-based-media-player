"""
utils.py
--------
Small reusable helpers: FPS meter, timestamp formatting, CSV log writer.
"""

from __future__ import annotations

import csv
import os
import time
from collections import deque
from datetime import datetime
from typing import Deque, Iterable, List


class FPSMeter:
    """Rolling FPS estimator based on frame timestamps."""

    def __init__(self, window: int = 30) -> None:
        self._stamps: Deque[float] = deque(maxlen=window)

    def tick(self) -> float:
        now = time.time()
        self._stamps.append(now)
        if len(self._stamps) < 2:
            return 0.0
        elapsed = self._stamps[-1] - self._stamps[0]
        if elapsed <= 0:
            return 0.0
        return (len(self._stamps) - 1) / elapsed


def timestamp() -> str:
    """Human-readable timestamp for log entries."""
    return datetime.now().strftime("%H:%M:%S")


def filename_timestamp() -> str:
    """Filesystem-safe timestamp for log filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: str) -> None:
    """Create a directory if it does not already exist."""
    if path and not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def export_log_csv(rows: Iterable[Iterable[str]], path: str) -> None:
    """Write activity-log rows to a CSV file."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timestamp", "gesture", "action", "mode"])
        for row in rows:
            writer.writerow(list(row))


def export_log_txt(lines: List[str], path: str) -> None:
    """Write activity-log lines to a plain-text file."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
