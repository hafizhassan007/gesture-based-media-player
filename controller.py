"""
controller.py
-------------
Translates a confirmed gesture into an OS-level keyboard event.
"""

from __future__ import annotations

import time
from typing import Optional

import pyautogui

from config import FAST_GESTURES, RuntimeSettings

pyautogui.FAILSAFE = False


class GestureController:
    """Maps confirmed gestures to keyboard shortcuts with a cooldown."""

    def __init__(self, settings: RuntimeSettings) -> None:
        self.settings = settings
        self._last_action_time: float = 0.0
        self._last_gesture: Optional[str] = None

    # ------------------------------------------------------------------ #
    def _cooldown_for(self, gesture: str) -> float:
        """Return cooldown depending on gesture type."""
        if gesture in FAST_GESTURES:
            return self.settings.fast_cooldown
        return self.settings.cooldown

    # ------------------------------------------------------------------ #
    def trigger(self, gesture: str) -> Optional[str]:
        """
        Fire the keyboard shortcut bound to *gesture*.

        Returns pressed key or None if suppressed.
        """
        now = time.time()
        cooldown = self._cooldown_for(gesture)

        # 🚀 NEW: prevent repeating same gesture too fast
        if (
            gesture == self._last_gesture
            and now - self._last_action_time < cooldown
        ):
            return None

        key = self.settings.key_for(gesture)
        if not key:
            return None

        try:
            pyautogui.press(key)
        except Exception as exc:  # pragma: no cover
            print(f"[controller] key press failed: {exc}")
            return None

        self._last_action_time = now
        self._last_gesture = gesture
        return key

    # ------------------------------------------------------------------ #
    def reset(self) -> None:
        self._last_action_time = 0.0
        self._last_gesture = None