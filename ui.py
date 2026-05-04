"""
ui.py
-----
Compact, minimal PyQt5 dashboard tuned for 14-inch 1920x1080 laptops at 125% DPI.

Public surface (do NOT rename — main.py imports run_app):
    DetectionWorker  — QThread that owns Camera + GestureDetector + GestureController
    MainWindow       — Top-level window
    run_app()        — Build QApplication, show MainWindow, return exit code
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

import cv2
import numpy as np

from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from camera import Camera
from config import (
    APP_STYLESHEET,
    COOLDOWN_DEFAULT,
    GESTURE_LABELS,
    LOG_DIR,
    RuntimeSettings,
)
from controller import GestureController
from gesture_detector import DetectionResult, GestureDetector
from utils import FPSMeter, export_log_csv, export_log_txt, filename_timestamp, timestamp


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _make_card(title: str) -> Tuple[QFrame, QVBoxLayout]:
    """Return a styled card frame plus its inner layout (title already added)."""
    card = QFrame()
    card.setObjectName("Card")
    card.setFrameShape(QFrame.NoFrame)

    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(6)

    header = QLabel(title.upper())
    header.setObjectName("CardTitle")
    layout.addWidget(header)

    return card, layout


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("FieldLabel")
    return lbl


# --------------------------------------------------------------------------- #
# Background worker
# --------------------------------------------------------------------------- #
class DetectionWorker(QThread):
    """Owns the camera + detector + controller. Emits Qt signals to the UI."""

    frame_ready = pyqtSignal(QImage, float)
    detection = pyqtSignal(object)
    action_fired = pyqtSignal(str, str)
    error = pyqtSignal(str)

    def __init__(self, settings: RuntimeSettings) -> None:
        super().__init__()
        self.settings = settings
        self._running: bool = False
        self._fps = FPSMeter()
        self.camera: Optional[Camera] = None
        self.detector: Optional[GestureDetector] = None
        self.controller: Optional[GestureController] = None

    def stop(self) -> None:
        self._running = False
        self.wait(2000)

    def run(self) -> None:
        self._running = True
        try:
            self.camera = Camera()
            if not self.camera.open():
                self.error.emit("Could not open the webcam.")
                return
            self.detector = GestureDetector(
                confirm_threshold=self.settings.confirm_threshold,
            )
            self.controller = GestureController(self.settings)
        except Exception as exc:
            self.error.emit(f"Initialisation failed: {exc}")
            return

        while self._running:
            ok, frame = self.camera.read()
            if not ok or frame is None:
                continue

            result: DetectionResult = DetectionResult(None, None, 0.0, None)
            if self.settings.detection_enabled:
                result = self.detector.detect(frame)

                if self.settings.show_landmarks and result.landmarks:
                    GestureDetector.draw_landmarks(frame, result.landmarks)

                if result.stable_gesture:
                    key = self.controller.trigger(result.stable_gesture)
                    if key:
                        self.action_fired.emit(result.stable_gesture, key)
                        self.detector.clear_history()

            fps = self._fps.tick()
            self.frame_ready.emit(self._to_qimage(frame), fps)
            self.detection.emit(result)

        if self.detector is not None:
            self.detector.close()
        if self.camera is not None:
            self.camera.release()

    @staticmethod
    def _to_qimage(frame_bgr: np.ndarray) -> QImage:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        return QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()


# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    """Compact dashboard. Layout: video on the left, status / controls / log on the right."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Hand Gesture Media Controller")
        self.resize(1080, 620)
        self.setMinimumSize(960, 560)

        self.settings = RuntimeSettings()
        self._log_rows: List[Tuple[str, str, str, str]] = []

        self._build_ui()

        self.worker = DetectionWorker(self.settings)
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.detection.connect(self._on_detection)
        self.worker.action_fired.connect(self._on_action_fired)
        self.worker.error.connect(self._on_worker_error)
        self.worker.start()

        self._refresh_buttons()

    # ================================================================== #
    # UI construction
    # ================================================================== #
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 8)
        root.setSpacing(10)

        root.addWidget(self._build_video_card(), stretch=3)
        root.addLayout(self._build_side_panel(), stretch=2)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready.")

    # ------------------------------------------------------------------ #
    def _build_video_card(self) -> QFrame:
        card, layout = _make_card("Live Camera Feed")
        layout.setContentsMargins(10, 10, 10, 10)

        self.video_label = QLabel("Camera initializing...")
        self.video_label.setObjectName("VideoLabel")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(520, 380)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(self.video_label, stretch=1)
        return card

    # ------------------------------------------------------------------ #
    def _build_side_panel(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self._build_status_card())
        col.addWidget(self._build_controls_card())
        col.addWidget(self._build_log_card(), stretch=1)
        return col

    # ------------------------------------------------------------------ #
    def _build_status_card(self) -> QFrame:
        card, layout = _make_card("Status")
        layout.setSpacing(4)

        layout.addWidget(_field_label("CURRENT GESTURE"))
        self.lbl_gesture = QLabel("—")
        self.lbl_gesture.setObjectName("GestureValue")
        layout.addWidget(self.lbl_gesture)

        layout.addSpacing(4)
        layout.addWidget(_field_label("LAST ACTION"))
        self.lbl_action = QLabel("—")
        self.lbl_action.setObjectName("ActionValue")
        layout.addWidget(self.lbl_action)

        layout.addSpacing(6)
        conf_row = QHBoxLayout()
        conf_row.addWidget(_field_label("Confidence"))
        conf_row.addStretch()
        self.lbl_conf_pct = QLabel("0%")
        self.lbl_conf_pct.setObjectName("MutedSmall")
        conf_row.addWidget(self.lbl_conf_pct)
        layout.addLayout(conf_row)

        self.bar_conf = QProgressBar()
        self.bar_conf.setRange(0, 100)
        self.bar_conf.setTextVisible(False)
        self.bar_conf.setFixedHeight(6)
        layout.addWidget(self.bar_conf)

        layout.addSpacing(6)
        info = QHBoxLayout()
        info.addWidget(_field_label("FPS"))
        self.lbl_fps = QLabel("—.—")
        self.lbl_fps.setObjectName("Metric")
        info.addWidget(self.lbl_fps)
        info.addStretch()
        info.addWidget(_field_label("STATE"))
        self.lbl_state = QLabel("Idle")
        self.lbl_state.setObjectName("Metric")
        info.addWidget(self.lbl_state)
        layout.addLayout(info)

        return card

    # ------------------------------------------------------------------ #
    def _build_controls_card(self) -> QFrame:
        card, layout = _make_card("Controls")
        layout.setSpacing(6)

        sens_row = QHBoxLayout()
        sens_row.addWidget(_field_label("Sensitivity"))
        sens_row.addStretch()
        self.lbl_sens_val = QLabel(f"{self.settings.cooldown:.2f}s")
        self.lbl_sens_val.setObjectName("MutedSmall")
        sens_row.addWidget(self.lbl_sens_val)
        layout.addLayout(sens_row)

        self.sld_sens = QSlider(Qt.Horizontal)
        self.sld_sens.setRange(10, 100)
        self.sld_sens.setValue(int(COOLDOWN_DEFAULT * 100))
        self.sld_sens.setFixedHeight(18)
        self.sld_sens.valueChanged.connect(self._on_sensitivity_changed)
        layout.addWidget(self.sld_sens)

        layout.addSpacing(2)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_start = QPushButton("Start Detection")
        self.btn_start.setObjectName("Primary")
        self.btn_start.setFixedHeight(28)
        self.btn_stop = QPushButton("Stop Detection")
        self.btn_stop.setFixedHeight(28)
        self.btn_start.clicked.connect(self._on_start_clicked)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        return card

    # ------------------------------------------------------------------ #
    def _build_log_card(self) -> QFrame:
        card, layout = _make_card("Activity Log")
        layout.setSpacing(6)

        self.list_log = QListWidget()
        self.list_log.setObjectName("LogList")
        self.list_log.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.list_log, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.addStretch()
        self.btn_export = QPushButton("Export")
        self.btn_export.setFixedHeight(24)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedHeight(24)
        self.btn_export.clicked.connect(self._on_export_clicked)
        self.btn_clear.clicked.connect(self._on_clear_log_clicked)
        btn_row.addWidget(self.btn_export)
        btn_row.addWidget(self.btn_clear)
        layout.addLayout(btn_row)

        return card

    # ================================================================== #
    # Worker → UI slots
    # ================================================================== #
    @pyqtSlot(QImage, float)
    def _on_frame(self, img: QImage, fps: float) -> None:
        pix = QPixmap.fromImage(img).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.video_label.setPixmap(pix)
        self.lbl_fps.setText(f"{fps:.1f}")

    @pyqtSlot(object)
    def _on_detection(self, result: DetectionResult) -> None:
        if result.stable_gesture:
            name = GESTURE_LABELS.get(result.stable_gesture, result.stable_gesture)
            self.lbl_gesture.setText(name)
        elif result.gesture:
            name = GESTURE_LABELS.get(result.gesture, result.gesture)
            self.lbl_gesture.setText(f"{name} · holding")
        else:
            self.lbl_gesture.setText("—")

        pct = int(result.confidence * 100)
        self.bar_conf.setValue(pct)
        self.lbl_conf_pct.setText(f"{pct}%")

    @pyqtSlot(str, str)
    def _on_action_fired(self, gesture: str, key: str) -> None:
        name = GESTURE_LABELS.get(gesture, gesture)
        ts = timestamp()
        line = f"{ts}  {name:<14} → '{key}'"
        self.list_log.insertItem(0, line)
        if self.list_log.count() > 300:
            self.list_log.takeItem(self.list_log.count() - 1)
        self._log_rows.insert(0, (ts, name, key, self.settings.mode))
        self.lbl_action.setText(f"{name} → '{key}'")

    @pyqtSlot(str)
    def _on_worker_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Error", msg)
        self.statusBar().showMessage(f"Error: {msg}")

    # ================================================================== #
    # User → UI slots
    # ================================================================== #
    def _on_start_clicked(self) -> None:
        self.settings.detection_enabled = True
        self.lbl_state.setText("Active")
        self.statusBar().showMessage("Detection started.")
        self._refresh_buttons()

    def _on_stop_clicked(self) -> None:
        self.settings.detection_enabled = False
        self.lbl_state.setText("Idle")
        self.statusBar().showMessage("Detection paused.")
        self._refresh_buttons()

    def _on_sensitivity_changed(self, value: int) -> None:
        cooldown = round(value / 100.0, 2)
        self.settings.cooldown = cooldown
        self.settings.fast_cooldown = max(round(cooldown / 4.0, 2), 0.08)
        self.lbl_sens_val.setText(f"{cooldown:.2f}s")

    def _on_clear_log_clicked(self) -> None:
        self.list_log.clear()
        self._log_rows.clear()
        self.lbl_action.setText("—")

    def _on_export_clicked(self) -> None:
        if not self._log_rows:
            QMessageBox.information(self, "Nothing to export", "Log is empty.")
            return

        suggested = os.path.join(LOG_DIR, f"gesture_log_{filename_timestamp()}.csv")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Log",
            suggested,
            "CSV (*.csv);;Text (*.txt)",
        )
        if not path:
            return

        try:
            if path.lower().endswith(".txt"):
                lines = [self.list_log.item(i).text() for i in range(self.list_log.count())]
                export_log_txt(lines, path)
            else:
                export_log_csv(self._log_rows, path)
            self.statusBar().showMessage(f"Exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    # ================================================================== #
    def _refresh_buttons(self) -> None:
        running = self.settings.detection_enabled
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def closeEvent(self, event) -> None:
        self.worker.stop()
        super().closeEvent(event)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def run_app() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication.instance() or QApplication([])
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()
    return app.exec_()
