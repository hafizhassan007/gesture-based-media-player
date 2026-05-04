# Hand Gesture Media Controller — Final Year Project

A real-time hand-gesture recognition system that controls **VLC media player**
(and PowerPoint, in *Presentation Mode*) using only a webcam. Built with
**MediaPipe**, **OpenCV**, and a **PyQt5** dashboard.

---

## Project Structure

```
gbmcp/
├── main.py                 # Entry point
├── config.py               # All settings, gesture maps, theme
├── camera.py               # Webcam capture (OpenCV wrapper)
├── gesture_detector.py     # MediaPipe HandLandmarker + classification
├── controller.py           # pyautogui keyboard actions + cooldown
├── ui.py                   # PyQt5 dashboard, worker thread, dialogs
├── utils.py                # FPS meter, log exporters, helpers
├── hand_landmarker.task    # MediaPipe model file
├── requirements.txt
└── README.md
```

Each module has a single responsibility — the project is laid out the way a
real software product would be, not as a single demo script.

---

## Gestures

Finger order is `[Thumb, Index, Middle, Ring, Pinky]` (1 = up, 0 = down).

| Fingers           | Gesture        | Media Mode (VLC) | Presentation Mode |
|-------------------|----------------|------------------|-------------------|
| `1 0 0 0 0`       | Play / Pause   | `space`          | `f5`              |
| `1 1 1 1 0`       | Stop           | `s`              | `escape`          |
| `0 0 0 0 0`       | Mute           | `m`              | `b` (blank)       |
| `1 1 1 1 1`       | Fullscreen     | `f`              | `f5`              |
| `0 1 0 0 0`       | Volume Up      | `up`             | `up`              |
| `0 0 0 0 1`       | Volume Down    | `down`           | `down`            |
| `0 1 1 0 0`       | Forward        | `right`          | `right` (next)    |
| `0 1 0 0 1`       | Backward       | `left`           | `left` (prev)     |
| `0 1 1 1 0`       | Next track     | `n`              | `right`           |
| `0 1 1 1 1`       | Previous track | `p`              | `left`            |
| `1 1 1 0 0`       | Speed Up       | `]`              | `pageup`          |
| `1 1 0 0 0`       | Speed Down     | `[`              | `pagedown`        |

All bindings can be customised by editing `config.py`.

---

## Features

- Modular, OOP-based architecture (one responsibility per file)
- Clean PyQt5 dashboard
- Live camera feed with hand-skeleton overlay
- Gesture display + last-action status
- **FPS counter**
- **Confidence indicator** (live progress bar)
- **Sensitivity slider** that tunes the cooldown in real time
- **Mode selector** — Media Mode / Presentation Mode
- **Activity log** with **CSV / TXT export**
- Smoothing buffer + per-gesture cooldown to eliminate flicker
- Camera + inference run on a `QThread` so the UI never freezes

---

## Setup

1. **Python 3.9 – 3.11** is recommended (MediaPipe wheels).
2. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate            # Windows
   # source .venv/bin/activate       # macOS / Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Make sure `hand_landmarker.task` sits next to `main.py`. If missing,
   download it from the MediaPipe model zoo
   (`hand_landmarker.task`, *Hand Landmarker*).

---

## Run

```bash
python main.py
```

1. The dashboard opens with the camera in *idle* mode.
2. Click **▶ Start Detection**.
3. Choose **Media Mode** (default) or **Presentation Mode**.
4. Open VLC (or PowerPoint) and keep that window focused — `pyautogui` sends
   key presses to whichever window currently has focus.
5. Hold a gesture for ~½ second; the action fires once and is logged.

Use the **Export** button to save the session log as CSV / TXT, and the
**Sensitivity** slider to tune how quickly repeated gestures retrigger.

---

## Notes for the Viva Demo

- Open VLC, queue a video, and keep VLC focused while the dashboard runs.
- Demonstrate Volume Up / Down first — they use a shorter cooldown so the
  effect is visible immediately.
- Switch the **Mode** combo to *Presentation Mode* and open PowerPoint to
  show that the same gestures map to slide controls.
- Show the **Activity Log** filling up and use **Export** to save a CSV.
