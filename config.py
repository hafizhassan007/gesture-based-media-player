"""
config.py
---------
Configuration and modern dark theme for the application.
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Dict, Tuple

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(PROJECT_ROOT, "hand_landmarker.task")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

# Camera
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FLIP_HORIZONTAL = True

# Detection settings
HISTORY_LENGTH = 8
CONFIRM_THRESHOLD = 3
COOLDOWN_DEFAULT = 0.60
COOLDOWN_FAST = 0.15
FAST_GESTURES: Tuple[str, ...] = ("VOL_UP", "VOL_DOWN")

# Gesture mappings
GESTURE_FINGER_MAP: Dict[Tuple[int, int, int, int, int], str] = {
    (1, 0, 0, 0, 0): "PLAY_PAUSE",
    (1, 1, 1, 1, 0): "STOP",
    (0, 0, 0, 0, 0): "MUTE",
    (1, 1, 1, 1, 1): "FULLSCREEN",
    (0, 1, 0, 0, 0): "VOL_UP",
    (0, 0, 0, 0, 1): "VOL_DOWN",
    (0, 1, 1, 0, 0): "FORWARD",
    (0, 0, 1, 1, 1): "BACKWARD",
    (0, 1, 1, 1, 0): "NEXT",
    (0, 1, 1, 1, 1): "PREVIOUS",
    (1, 1, 1, 0, 0): "SPEED_UP",
    (1, 1, 0, 0, 0): "SPEED_DOWN",
}

MEDIA_MODE_ACTIONS: Dict[str, str] = {
    "PLAY_PAUSE": "space",
    "STOP": "s",
    "MUTE": "m",
    "FULLSCREEN": "f",
    "VOL_UP": "up",
    "VOL_DOWN": "down",
    "FORWARD": "right",
    "BACKWARD": "left",
    "NEXT": "n",
    "PREVIOUS": "p",
    "SPEED_UP": "]",
    "SPEED_DOWN": "[",
}

GESTURE_LABELS: Dict[str, str] = {
    "PLAY_PAUSE": "Play / Pause",
    "STOP": "Stop",
    "MUTE": "Mute",
    "FULLSCREEN": "Fullscreen",
    "VOL_UP": "Volume Up",
    "VOL_DOWN": "Volume Down",
    "FORWARD": "Forward",
    "BACKWARD": "Backward",
    "NEXT": "Next",
    "PREVIOUS": "Previous",
    "SPEED_UP": "Speed Up",
    "SPEED_DOWN": "Speed Down",
}


@dataclass
class RuntimeSettings:
    mode: str = "Media Mode"
    cooldown: float = COOLDOWN_DEFAULT
    fast_cooldown: float = COOLDOWN_FAST
    confirm_threshold: int = CONFIRM_THRESHOLD
    detection_enabled: bool = False
    show_landmarks: bool = True

    def key_for(self, gesture: str) -> str:
        return MEDIA_MODE_ACTIONS.get(gesture, "")


# ==================== MODERN DARK THEME ====================
APP_STYLESHEET = """
* {
    font-family: "Segoe UI", "Inter", sans-serif;
}

QWidget {
    font-size: 9pt;
    color: #e8eaee;
}

QMainWindow {
    background-color: #14161a;
}

QFrame#Card {
    background-color: #1d2025;
    border: 1px solid #2c3038;
    border-radius: 8px;
}

QLabel#CardTitle {
    font-size: 8pt;
    font-weight: 700;
    color: #8a8f99;
    letter-spacing: 1px;
    background: transparent;
    border: none;
}

QLabel#FieldLabel {
    font-size: 8pt;
    color: #8a8f99;
    background: transparent;
    border: none;
}

QLabel#VideoLabel {
    background: #0d0f12;
    border: 1px solid #2c3038;
    border-radius: 8px;
}

QLabel#GestureValue {
    font-size: 14pt;
    font-weight: 600;
    color: #ffffff;
    background: transparent;
    border: none;
}

QLabel#ActionValue {
    font-size: 9.5pt;
    color: #c4c8d0;
    background: transparent;
    border: none;
}

QLabel#Metric {
    font-size: 9.5pt;
    font-weight: 600;
    color: #ffffff;
    background: transparent;
    border: none;
}

QLabel#MutedSmall {
    font-size: 8pt;
    color: #8a8f99;
    background: transparent;
    border: none;
}

QPushButton {
    background-color: #2a2e36;
    border: 1px solid #3a3f48;
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 8.5pt;
    font-weight: 500;
    color: #e8eaee;
}

QPushButton:hover {
    background-color: #333842;
    border-color: #4a505a;
}

QPushButton:pressed {
    background-color: #23262d;
}

QPushButton:disabled {
    background-color: #1d2025;
    border-color: #2c3038;
    color: #5a5f68;
}

QPushButton#Primary {
    background-color: #4f8cff;
    border: 1px solid #4f8cff;
    color: white;
}

QPushButton#Primary:hover {
    background-color: #5e98ff;
    border-color: #5e98ff;
}

QPushButton#Primary:pressed {
    background-color: #4480f0;
}

QPushButton#Primary:disabled {
    background-color: #2a3a5a;
    border-color: #2a3a5a;
    color: #7a8aa0;
}

QSlider::groove:horizontal {
    background: #2c3038;
    height: 5px;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #4f8cff;
}

QSlider::handle:horizontal {
    background: white;
    width: 13px;
    height: 13px;
    margin: -4px 0;
    border-radius: 7px;
}

QListWidget#LogList {
    background-color: #16181c;
    border: 1px solid #2c3038;
    border-radius: 6px;
    font-size: 8pt;
    color: #b3b7c0;
}

QProgressBar {
    background: #2c3038;
    border-radius: 3px;
    height: 6px;
}

QProgressBar::chunk {
    background-color: #4f8cff;
}

QStatusBar {
    background: #14161a;
    color: #8a8f99;
}
"""