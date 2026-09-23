"""
main.py
-------
Application entry point.

Run with:
    python main.py
"""

from __future__ import annotations

import os
import sys

from config import MODEL_PATH


def _check_files() -> None:
    """Fail loudly if the MediaPipe model file is missing."""
    if not os.path.isfile(MODEL_PATH):
        sys.stderr.write(
            f"[fatal] Model file not found: {MODEL_PATH}\n"
            "Download 'hand_landmarker.task' from the MediaPipe model zoo\n"
            "and place it next to main.py.\n"
        )
        sys.exit(2)


def main() -> int:
    _check_files()

    try:
        # Lazy import to avoid heavy startup cost
        from ui import run_app
    except SyntaxError as e:
        sys.stderr.write(
            "\n[fatal] Syntax error in ui.py\n"
            f"{e}\n"
            "Fix the error in ui.py and try again.\n"
        )
        return 1
    except Exception as e:
        sys.stderr.write(
            "\n[fatal] Failed to import UI module\n"
            f"{e}\n"
        )
        return 1

    return run_app()


if __name__ == "__main__":
    sys.exit(main())