"""
controller.py
-------------
Translates a confirmed gesture into an OS-level keyboard event.

Uses pyautogui so it works with VLC, PowerPoint, browsers, etc.
A per-gesture cooldown prevents the same action from firing on every
frame while the hand is still held in the trigger pose.
"""

from __future__ import annotations

import time
from typing import Optional

import pyautogui

from config import FAST_GESTURES, RuntimeSettings


# pyautogui safety: disable the fail-safe corner so a user accidentally
# moving the mouse to (0,0) does not crash the app mid-demo.
pyautogui.FAILSAFE = False


class GestureController:
    """Maps confirmed gestures to keyboard shortcuts with a cooldown."""

    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self._last_action_time: float = 0.0
        self._last_gesture: Optional[str] = None

    # ------------------------------------------------------------------ #
    def _cooldown_for(self, gesture: str) -> float:
        if gesture in FAST_GESTURES:
            return self.settings.fast_cooldown
        return self.settings.cooldown

    # ------------------------------------------------------------------ #
    def trigger(self, gesture: str) -> Optional[str]:
        """
        Fire the keyboard shortcut bound to *gesture*.

        Returns the key that was pressed (for logging), or None if the
        gesture was suppressed by the cooldown / has no binding.
        """
        now = time.time()
        if now - self._last_action_time < self._cooldown_for(gesture):
            return None

        key = self.settings.key_for(gesture)
        if not key:
            return None

        try:
            pyautogui.press(key)
        except Exception as exc:  # pragma: no cover  - hardware/OS variance
            print(f"[controller] key press failed: {exc}")
            return None

        self._last_action_time = now
        self._last_gesture = gesture
        return key

    # ------------------------------------------------------------------ #
    def reset(self) -> None:
        self._last_action_time = 0.0
        self._last_gesture = None
