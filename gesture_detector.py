"""
gesture_detector.py
-------------------
Wraps Google MediaPipe Tasks (HandLandmarker) and turns 21-point
landmark output into one of the named gestures defined in config.py.

Two responsibilities:
  1. Run the landmark model on a BGR frame.
  2. Recognise the gesture and provide a confidence score derived
     from a smoothing history buffer (used by the UI confidence bar).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from config import (
    GESTURE_FINGER_MAP,
    HISTORY_LENGTH,
    MODEL_PATH,
)


# ---------------------------------------------------------------------------
# Hand connections used to draw the skeleton overlay
# ---------------------------------------------------------------------------
HAND_CONNECTIONS: Tuple[Tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4),         # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),         # index
    (5, 9), (9, 10), (10, 11), (11, 12),    # middle
    (9, 13), (13, 14), (14, 15), (15, 16),  # ring
    (13, 17), (17, 18), (18, 19), (19, 20), # pinky
    (0, 17),                                # palm base
)


@dataclass
class DetectionResult:
    """Output of a single frame inference."""
    gesture: Optional[str]          # raw gesture this frame (if any)
    stable_gesture: Optional[str]   # gesture once the smoother confirms it
    confidence: float               # 0.0..1.0 from history buffer
    landmarks: Optional[List[Tuple[int, int]]]  # pixel-space points


class GestureDetector:
    """MediaPipe-backed hand-gesture detector with smoothing."""

    def __init__(
        self,
        model_path: str = MODEL_PATH,
        history_length: int = HISTORY_LENGTH,
        confirm_threshold: int = 3,
    ) -> None:
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            running_mode=mp_vision.RunningMode.IMAGE,
        )
        self._detector = mp_vision.HandLandmarker.create_from_options(options)
        self._history: Deque[str] = deque(maxlen=history_length)
        self._history_length: int = history_length
        self.confirm_threshold: int = confirm_threshold

    # ------------------------------------------------------------------ #
    # Finger-state extraction
    # ------------------------------------------------------------------ #
    @staticmethod
    def _get_fingers(lm) -> Tuple[int, int, int, int, int]:
        """Return a 5-tuple of 0/1 for [Thumb, Index, Middle, Ring, Pinky]."""
        thumb = int(lm[4].x < lm[3].x)
        tips = (8, 12, 16, 20)
        pips = (6, 10, 14, 18)
        others = tuple(int(lm[t].y < lm[p].y) for t, p in zip(tips, pips))
        return (thumb,) + others

    @staticmethod
    def _classify(fingers: Tuple[int, int, int, int, int]) -> Optional[str]:
        return GESTURE_FINGER_MAP.get(fingers)

    # ------------------------------------------------------------------ #
    # Core inference
    # ------------------------------------------------------------------ #
    def detect(self, frame_bgr: np.ndarray) -> DetectionResult:
        """Run landmark inference + gesture classification on one frame."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._detector.detect(mp_image)

        if not result.hand_landmarks:
            self._history.clear()
            return DetectionResult(None, None, 0.0, None)

        lm = result.hand_landmarks[0]
        h, w = frame_bgr.shape[:2]
        pixel_points = [(int(p.x * w), int(p.y * h)) for p in lm]

        gesture = self._classify(self._get_fingers(lm))

        stable: Optional[str] = None
        confidence: float = 0.0
        if gesture is not None:
            self._history.append(gesture)
            count = self._history.count(gesture)
            confidence = count / self._history_length
            # Strictly greater-than matches the original demo's behaviour:
            # threshold=3 means 4 confirming frames are needed before firing.
            if count > self.confirm_threshold:
                stable = gesture
        else:
            self._history.clear()

        return DetectionResult(gesture, stable, confidence, pixel_points)

    # ------------------------------------------------------------------ #
    def clear_history(self) -> None:
        """Forget the smoothing history (e.g. after firing an action)."""
        self._history.clear()

    def close(self) -> None:
        """Release the underlying MediaPipe resources."""
        try:
            self._detector.close()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Drawing helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def draw_landmarks(
        frame: np.ndarray,
        points: List[Tuple[int, int]],
        color_point: Tuple[int, int, int] = (110, 231, 249),  # cyan
        color_line: Tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        """Render the 21-point hand skeleton on a frame in-place."""
        for a, b in HAND_CONNECTIONS:
            if a < len(points) and b < len(points):
                cv2.line(frame, points[a], points[b], color_line, 2, cv2.LINE_AA)
        for (x, y) in points:
            cv2.circle(frame, (x, y), 4, color_point, -1, cv2.LINE_AA)
