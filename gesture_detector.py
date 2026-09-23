"""
gesture_detector.py
-------------------
MediaPipe hand gesture + improved swipe detection.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple

import cv2 as cv
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from config import (
    GESTURE_FINGER_MAP,
    HISTORY_LENGTH,
    CONFIRM_THRESHOLD,
    MODEL_PATH,
)
"""     GESTURE_FINGER_MAP= {
    (1, 0, 0, 0, 0): "PLAY_PAUSE",
    (0, 1, 1, 1, 1): "STOP",
    (0, 0, 0, 0, 0): "MUTE",
    (1, 0, 0, 0, 1): "FULLSCREEN",
    (0, 1, 0, 0, 0): "VOL_UP",
    (0, 0, 0, 0, 1): "VOL_DOWN",
    (0, 1, 1, 0, 0): "FORWARD",
    (0, 0, 1, 1, 1): "BACKWARD",
    (1, 1, 1, 0, 0): "SPEED_UP",
    (1, 1, 0, 0, 0): "SPEED_DOWN"}
    HISTORY_LENGTH=8
    confirm_threshold=3
    MODEL_PATH='D:\\project final code 5-5-26\\gbmcp\\hand_landmarker.task'
"""
# ------------------------------------------------
HAND_CONNECTIONS: Tuple[Tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
)

# ---------------------------------------------------------------------------
@dataclass
class DetectionResult:
    gesture: Optional[str]
    stable_gesture: Optional[str]
    confidence: float
    landmarks: Optional[List[Tuple[int, int]]]

# ---------------------------------------------------------------------------
class GestureDetector:
    def __init__(self,
        model_path: str = MODEL_PATH,
        history_length: int = HISTORY_LENGTH,
        confirm_threshold: int = CONFIRM_THRESHOLD,
    ) -> None:
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            running_mode=mp_vision.RunningMode.IMAGE,
        )
        self._detector = mp_vision.HandLandmarker.create_from_options(options)

        self._history: Deque[str] = deque(maxlen=history_length)
        self._history_length = history_length
        self.confirm_threshold = confirm_threshold

        # Position history for swipe detection
        self._pos_history: Deque[Tuple[int, int]] = deque(maxlen=10)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _get_fingers(lm) -> Tuple[int, int, int, int, int]:
        thumb = int(lm[4].x < lm[3].x)
        tips = (8, 12, 16, 20)
        pips = (6, 10, 14, 18)
        others = tuple(int(lm[t].y < lm[p].y) for t, p in zip(tips, pips))
        return (thumb,) + others

    @staticmethod
    def _classify(fingers: Tuple[int, int, int, int, int]) -> Optional[str]:
        return GESTURE_FINGER_MAP.get(fingers)

    # ------------------------------------------------------------------ #
    def _get_center(self, lm, frame_shape) -> Tuple[int, int]:
        h, w = frame_shape[:2]
        xs = [p.x * w for p in lm]
        ys = [p.y * h for p in lm]
        return int(sum(xs) / len(xs)), int(sum(ys) / len(ys))

    # ------------------------------------------------------------------ #
    # 🔥 IMPROVED SWIPE DETECTION
    def _detect_swipe(self) -> Optional[str]:
        if len(self._pos_history) < 5:
            return None

        xs = [p[0] for p in self._pos_history]
        ys = [p[1] for p in self._pos_history]

        dx = xs[-1] - xs[0]
        dy = ys[-1] - ys[0]

        distance = abs(dx)

        # velocity (frame-to-frame movement)
        velocities = [abs(xs[i] - xs[i - 1]) for i in range(1, len(xs))]
        avg_velocity = sum(velocities) / len(velocities)

        # thresholds (tuned)
        MIN_DISTANCE = 60
        MIN_VELOCITY = 12
        MAX_VERTICAL_DRIFT = 80

        # ignore vertical movement
        if abs(dy) > MAX_VERTICAL_DRIFT:
            return None

        # detect both slow and fast swipes
        if distance > MIN_DISTANCE or avg_velocity > MIN_VELOCITY:
            self._pos_history.clear()
            return "SWIPE_RIGHT" if dx > 0 else "SWIPE_LEFT"

        return None

    # ------------------------------------------------------------------ #
    def detect(self, frame_bgr: np.ndarray) -> DetectionResult:
        rgb = cv.cvtColor(frame_bgr, cv.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._detector.detect(mp_image)

        if not result.hand_landmarks:
            self._history.clear()
            self._pos_history.clear()
            return DetectionResult(None, None, 0.0, None)

        lm = result.hand_landmarks[0]
        h, w = frame_bgr.shape[:2]
        pixel_points = [(int(p.x * w), int(p.y * h)) for p in lm]

        # Track movement
        cx, cy = self._get_center(lm, frame_bgr.shape)
        self._pos_history.append((cx, cy))

        # 👉 Only allow swipe on OPEN PALM
        fingers = self._get_fingers(lm)

        if fingers == (1, 1, 1, 1, 1):
            swipe = self._detect_swipe()
        else:
            swipe = None
            self._pos_history.clear()

        if swipe:
            self._history.clear()
            return DetectionResult(swipe, swipe, 1.0, pixel_points)

        # =========================
        # STATIC GESTURE LOGIC
        # =========================
        gesture = self._classify(fingers)

        stable: Optional[str] = None
        confidence: float = 0.5

        if gesture is not None:
            self._history.append(gesture)
            count = self._history.count(gesture)
            confidence = count / self._history_length

            if count > self.confirm_threshold:
                stable = gesture
        else:
            self._history.clear()

        return DetectionResult(gesture, stable, confidence, pixel_points)

    # ------------------------------------------------------------------ #
    def clear_history(self) -> None:
        self._history.clear()
        self._pos_history.clear()

    def close(self) -> None:
        try:
            self._detector.close()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    @staticmethod
    def draw_landmarks(
        frame: np.ndarray,
        points: List[Tuple[int, int]],
        color_point: Tuple[int, int, int] = (110, 231, 249),
        color_line: Tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        for a, b in HAND_CONNECTIONS:
            if a < len(points) and b < len(points):
                cv.line(frame, points[a], points[b], color_line, 2, cv.LINE_AA)
        for (x, y) in points:
            cv.circle(frame, (x, y), 4, color_point, -1, cv .LINE_AA)