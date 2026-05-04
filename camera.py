"""
camera.py
---------
Thin OpenCV webcam wrapper.

Keeping camera I/O isolated lets the rest of the app stay testable
(e.g. swap in a video file or a fake source for unit tests).
"""

from __future__ import annotations

from typing import Optional, Tuple

import cv2
import numpy as np

from config import CAMERA_INDEX, FRAME_HEIGHT, FRAME_WIDTH, FLIP_HORIZONTAL


class Camera:
    """Context-managed webcam capture."""

    def __init__(
        self,
        index: int = CAMERA_INDEX,
        width: int = FRAME_WIDTH,
        height: int = FRAME_HEIGHT,
        flip: bool = FLIP_HORIZONTAL,
    ) -> None:
        self.index = index
        self.width = width
        self.height = height
        self.flip = flip
        self._cap: Optional[cv2.VideoCapture] = None

    # ------------------------------------------------------------------ #
    def open(self) -> bool:
        """Open the camera. Returns True on success."""
        # CAP_DSHOW gives much faster startup on Windows.
        self._cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self.index)
        if not self._cap.isOpened():
            return False
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return True

    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read a single frame, applying horizontal flip if configured."""
        if self._cap is None:
            return False, None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return False, None
        if self.flip:
            frame = cv2.flip(frame, 1)
        return True, frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    # Context-manager sugar
    def __enter__(self) -> "Camera":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
