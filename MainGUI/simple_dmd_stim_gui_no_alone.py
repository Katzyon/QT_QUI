"""
Simple DMD Stim GUI (embedded)

Purpose
-------
A lightweight PySide6 window for:
1) snapping a camera image (via a Core/Camera *provided by MainGui*),
2) selecting a rectangular ROI on the image,
3) turning that ROI into a DMD mask (optionally via an affine warp),
4) applying the mask to the DMD, and driving stimulation pulses via an Arduino.

Hard constraint
---------------
This window does *not* create or connect its own Micro-Manager/PycroManager Core.
It must be launched from MainGui and receive shared `core` and `camera` handles.

Notes
-----
• Display orientation matches MainGui: images are shown as np.fliplr(raw).
• ROI coordinates are interpreted in the displayed coordinate system.
• If `affine` (2x3) is supplied/loaded, the ROI mask is warped to DMD size via cv2.warpAffine.
  If no affine is available, the ROI mask is resized to DMD size as an approximation.
"""

from __future__ import annotations

import os
import math
import threading
from typing import Any, Optional, Tuple

import cv2
import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from arduino_comm import ArduinoComm


class StimWorker(QThread):
    """Drive a pulse train through ArduinoComm without blocking the UI thread."""
    progress = Signal(int)           # total pulses delivered so far
    finished = Signal(bool, str)     # ok, message

    def __init__(
        self,
        arduino_comm: ArduinoComm,
        period_ms: int,
        on_time_ms: int,
        total_pulses: int,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.arduino = arduino_comm
        self.period_ms = int(period_ms)
        self.on_time_ms = int(on_time_ms)
        self.total = max(0, int(total_pulses))
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def _max_indices_for_message(self) -> int:
        # Heuristic: keep serial line under Arduino firmware buffer limits.
        overhead = len(f"[],{self.period_ms},{self.on_time_ms}\n")
        bytes_per_index = 2  # "1,"
        max_bytes = 58
        return max(1, (max_bytes - overhead) // bytes_per_index)

    def run(self) -> None:
        if self.arduino is None:
            self.finished.emit(False, "Arduino not connected.")
            return

        max_indices = self._max_indices_for_message()
        sent = 0

        try:
            while sent < self.total and not self._stop_event.is_set():
                n = min(max_indices, self.total - sent)
                indices = [1] * n  # firmware expects a list; content doesn't matter for a single mask

                ok = self.arduino.send_message(indices, self.period_ms, self.on_time_ms)
                if not ok:
                    self.finished.emit(False, "Arduino did not acknowledge (timeout).")
                    return

                resp = self.arduino.wait_for_sequence_end_blocking(self._stop_event)
                if resp is None:
                    self.finished.emit(False, "Stopped." if self._stop_event.is_set() else "No 'Sequence finished' from Arduino.")
                    return

                sent += n
                self.progress.emit(sent)

            self.finished.emit(True, f"Delivered {sent} pulses.")
        except Exception as e:
            self.finished.emit(False, f"Error: {e}")


class SimpleStimWindow(QMainWindow):
    """ROI → DMD mask tool (embedded in MainGui)."""

    maskSaved = Signal(str)  # absolute file path to saved DMD mask (BMP)

    def __init__(
        self,
        host_gui: Any,
        save_dir: str,
        core: Any,
        camera: Any,
        arduino_comm: Optional[ArduinoComm] = None,
        affine: Optional[np.ndarray] = None,
    ):
        super().__init__()
        self.setWindowTitle("Simple DMD Stim (ROI mask)")
        self.resize(1320, 800)

        # Requirement: inherit Core/Camera (no standalone Core init)
        if core is None or camera is None:
            raise ValueError(
                "SimpleStimWindow must be launched from MainGui with shared Core/Camera. "
                "Standalone Core initialization is intentionally disabled."
            )

        self.host_gui = host_gui
        self.core = core
        self.camera = camera
        self.save_dir = save_dir
        self.arduino_comm = arduino_comm
        self.affine = affine.astype(np.float32) if affine is not None else None

        self.last_raw_frame: Optional[np.ndarray] = None
        self._display_shape: Optional[Tuple[int, int]] = None  # (H, W) of displayed image

        self.slm_name: Optional[str] = None
        self.slm_w: Optional[int] = None
        self.slm_h: Optional[int] = None
        self.slm_mask: Optional[np.ndarray] = None

        self.worker: Optional[StimWorker] = None

        self._discover_slm()
        self._build_ui()
        self._connect_signals()
        self._apply_embedding_constraints()

    # ---------------------------- Init helpers ----------------------------

    def _discover_slm(self) -> None:
        try:
            self.slm_name = self.core.get_slm_device()
            self.slm_w = int(self.core.get_slm_width(self.slm_name))
            self.slm_h = int(self.core.get_slm_height(self.slm_name))
        except Exception as e:
            QMessageBox.critical(self, "Core Error", f"Failed to query SLM/DMD from shared Core.\n\nDetails: {e}")
            self.slm_name = None
            self.slm_w = None
            self.slm_h = None

    def _apply_embedding_constraints(self) -> None:
        try:
            os.makedirs(self.save_dir, exist_ok=True)
        except Exception:
            pass

        if self.arduino_comm is not None:
            self.port_edit.setDisabled(True)
            self.connect_btn.setDisabled(True)
            self.connect_btn.setText("Arduino (shared)")

        if self.slm_name and self.slm_w and self.slm_h:
            self.statusBar().showMessage(f"Using shared Core: SLM='{self.slm_name}' ({self.slm_w}x{self.slm_h}).", 5000)
        else:
            self.statusBar().showMessage("Warning: SLM parameters unavailable.", 5000)

    # ---------------------------- UI ----------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        self.imageview = pg.ImageView()
        try:
            self.imageview.ui.roiBtn.hide()
            self.imageview.ui.menuBtn.hide()
            self.imageview.ui.histogram.show()
        except Exception:
            pass

        image_box = QGroupBox("Camera image / ROI")
        img_layout = QVBoxLayout(image_box)
        img_layout.addWidget(self.imageview)

        ctl_box = QGroupBox("Controls")
        grid = QGridLayout(ctl_box)

        # Row 0: Capture & affine
        self.snap_btn = QPushButton("Snap Image")
        self.load_affine_btn = QPushButton("Load Affine (2x3 .npy)")
        self.load_old_affine_btn = QPushButton("Load Old Affine")
        grid.addWidget(self.snap_btn, 0, 0)
        grid.addWidget(self.load_affine_btn, 0, 1)
        grid.addWidget(self.load_old_affine_btn, 0, 2)

        # Row 1: ROI
        self.make_mask_btn = QPushButton("Make DMD Mask from ROI")
        self.current_rect_label = QLabel("ROI: -")
        self.reset_roi_btn = QPushButton("Reset ROI")
        grid.addWidget(self.make_mask_btn, 1, 0)
        grid.addWidget(self.current_rect_label, 1, 1, 1, 3)
        grid.addWidget(self.reset_roi_btn, 1, 4)

        # Row 2: DMD
        self.apply_mask_btn = QPushButton("Apply Mask to DMD")
        self.clear_dmd_btn = QPushButton("Clear DMD")
        grid.addWidget(self.apply_mask_btn, 2, 0, 1, 2)
        grid.addWidget(self.clear_dmd_btn, 2, 2, 1, 2)

        # Row 3: Run / Manual
        self.manual_btn = QPushButton("Manual Stim (1 pulse)")
        self.run_btn = QPushButton("Run Stim Train")
        self.stop_btn = QPushButton("Stop")
        grid.addWidget(self.manual_btn, 3, 0, 1, 2)
        grid.addWidget(self.run_btn, 3, 2, 1, 2)
        grid.addWidget(self.stop_btn, 3, 4, 1, 2)

        # Row 4: Stim params
        self.freq_hz = QDoubleSpinBox()
        self.freq_hz.setRange(0.1, 1000.0)
        self.freq_hz.setDecimals(2)
        self.freq_hz.setValue(5.0)

        self.on_time_ms = QSpinBox()
        self.on_time_ms.setRange(1, 1000)
        self.on_time_ms.setValue(10)

        self.duration_s = QDoubleSpinBox()
        self.duration_s.setRange(0.1, 3600.0)
        self.duration_s.setDecimals(1)
        self.duration_s.setValue(5.0)

        grid.addWidget(QLabel("Freq (Hz):"), 4, 0)
        grid.addWidget(self.freq_hz, 4, 1)
        grid.addWidget(QLabel("On-time (ms):"), 4, 2)
        grid.addWidget(self.on_time_ms, 4, 3)
        grid.addWidget(QLabel("Duration (s):"), 4, 4)
        grid.addWidget(self.duration_s, 4, 5)

        # Row 5: Activity indicator + progress
        self.active_led = QLabel()
        self.active_lbl = QLabel("Stim ACTIVE")
        self.stim_progress = QProgressBar()
        self.stim_progress.setMinimum(0)
        self.stim_progress.setMaximum(1)
        self.stim_progress.setValue(0)

        grid.addWidget(self.active_led, 5, 0)
        grid.addWidget(self.active_lbl, 5, 1)
        grid.addWidget(self.stim_progress, 5, 2, 1, 4)

        # Row 6: Status
        self.status_lbl = QLabel("")
        grid.addWidget(self.status_lbl, 6, 0, 1, 6)

        # Row 7: Arduino
        self.port_edit = QLineEdit("COM13")
        self.connect_btn = QPushButton("Connect Arduino")
        grid.addWidget(QLabel("Arduino Port:"), 7, 0)
        grid.addWidget(self.port_edit, 7, 1)
        grid.addWidget(self.connect_btn, 7, 2)

        main = QHBoxLayout(central)
        main.addWidget(image_box, 4)
        main.addWidget(ctl_box, 1)

        self._setup_roi()
        self.setStatusBar(QStatusBar(self))

        exit_act = QAction("&Exit", self)
        exit_act.triggered.connect(self.close)
        self.menuBar().addMenu("&File").addAction(exit_act)

        self._set_active(False)
        self.stop_btn.setEnabled(False)

    def _connect_signals(self) -> None:
        self.snap_btn.clicked.connect(self.on_snap)
        self.load_affine_btn.clicked.connect(self.on_load_affine_generic)
        self.load_old_affine_btn.clicked.connect(self.load_old_affine)
        self.make_mask_btn.clicked.connect(self.on_make_mask)
        self.reset_roi_btn.clicked.connect(self.on_reset_roi)
        self.apply_mask_btn.clicked.connect(self.on_apply_mask)
        self.clear_dmd_btn.clicked.connect(self.on_clear_dmd)
        self.connect_btn.clicked.connect(self.on_connect_arduino)
        self.manual_btn.clicked.connect(self.on_manual)
        self.run_btn.clicked.connect(self.on_run)
        self.stop_btn.clicked.connect(self.on_stop)

    # ---------------------------- ROI handling ----------------------------

    def _setup_roi(self) -> None:
        vb = self.imageview.getView()
        vb.setAspectLocked(True)

        self.roi_rect = pg.RectROI([10, 10], [50, 50], pen=pg.mkPen("y", width=2))
        self.roi_rect.setZValue(10)
        vb.addItem(self.roi_rect)

        try:
            self.roi_rect.sigRegionChanged.connect(self._on_roi_changed)
        except Exception:
            pass

        self._on_roi_changed()

    def _get_roi_rect_display(self) -> Tuple[int, int, int, int]:
        pos = self.roi_rect.pos()
        size = self.roi_rect.size()
        return (int(pos.x()), int(pos.y()), int(size.x()), int(size.y()))

    def _on_roi_changed(self) -> None:
        x, y, w, h = self._get_roi_rect_display()
        self.current_rect_label.setText(f"ROI: x={x}, y={y}, w={w}, h={h}" if w > 0 and h > 0 else "ROI: -")

    @Slot()
    def on_reset_roi(self) -> None:
        self.roi_rect.setPos((10, 10))
        self.roi_rect.setSize((50, 50))
        self._on_roi_changed()
        self.status_lbl.setText("ROI reset.")

    # ---------------------------- Affine loading ----------------------------

    @Slot()
    def on_load_affine_generic(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load affine (2x3 .npy)", "", "NumPy arrays (*.npy)")
        if not path:
            return
        try:
            A = np.load(path)
            if A.shape != (2, 3):
                raise ValueError(f"Affine must be 2x3, got {A.shape}")
            self.affine = A.astype(np.float32)
            QMessageBox.information(self, "Affine", f"Loaded affine from:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Affine Error", f"Failed to load affine: {e}")

    @Slot()
    def load_old_affine(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Old affine transform")
        box.setText("Load old affine transform?")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        if box.exec() != QMessageBox.Yes:
            QMessageBox.information(self, "DMD Calibration", "Press your calibration flow to create a new affine.")
            return

        default_path = r"G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Images\affine_transform.npy"
        path = default_path if os.path.exists(default_path) else ""
        if not path:
            alt, _ = QFileDialog.getOpenFileName(self, "Select affine_transform.npy", "", "NumPy arrays (*.npy)")
            path = alt
        if not path:
            QMessageBox.information(self, "Affine", "No file selected.")
            return

        try:
            A = np.load(path)
            if A.shape != (2, 3):
                raise ValueError(f"Expected 2x3 matrix, got {A.shape}")
            self.affine = A.astype(np.float32)
            self.statusBar().showMessage(f"Loaded old affine from: {path}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Affine Error", f"Failed to load affine: {e}")

    # ---------------------------- Core actions ----------------------------

    @Slot()
    def on_snap(self) -> None:
        try:
            raw = self.camera.snap_image(self.core)
            self.last_raw_frame = raw.copy()

            frame_disp = np.ascontiguousarray(np.fliplr(self.last_raw_frame).copy())
            self._display_shape = frame_disp.shape
            self.imageview.setImage(frame_disp, autoLevels=True)
            self.statusBar().showMessage("Image snapped (displayed as fliplr).", 2000)
        except Exception as e:
            QMessageBox.critical(self, "Snap Error", f"Failed to snap image: {e}")

    def _compute_mask_from_roi(self) -> Optional[np.ndarray]:
        if self.last_raw_frame is None or self._display_shape is None:
            QMessageBox.warning(self, "ROI", "Snap an image first.")
            return None
        if self.slm_w is None or self.slm_h is None:
            QMessageBox.warning(self, "DMD", "SLM/DMD size is unknown.")
            return None

        x, y, w, h = self._get_roi_rect_display()
        if w <= 0 or h <= 0:
            QMessageBox.warning(self, "ROI", "ROI has zero area.")
            return None

        H_disp, W_disp = self._display_shape
        x0 = int(max(0, min(W_disp, x)))
        y0 = int(max(0, min(H_disp, y)))
        x1 = int(max(0, min(W_disp, x + w)))
        y1 = int(max(0, min(H_disp, y + h)))
        if x1 <= x0 or y1 <= y0:
            QMessageBox.warning(self, "ROI", "ROI is outside the image.")
            return None

        cam_mask = np.zeros((H_disp, W_disp), dtype=np.uint8)
        cam_mask[y0:y1, x0:x1] = 255

        if self.affine is not None:
            try:
                slm_img = cv2.warpAffine(cam_mask, self.affine, (self.slm_w, self.slm_h))
                return np.ascontiguousarray(np.clip(slm_img, 0, 255).astype(np.uint8))
            except Exception as e:
                QMessageBox.critical(self, "Affine Warp Error", f"Warp failed: {e}")
                return None

        QMessageBox.information(self, "No Affine", "Affine not loaded. ROI mask will be resized to DMD size (approximate).")
        return cv2.resize(cam_mask, (self.slm_w, self.slm_h), interpolation=cv2.INTER_NEAREST)

    def _persist_roi_mask(self) -> Optional[str]:
        if self.slm_mask is None:
            return None
        if not self.save_dir:
            return None

        try:
            os.makedirs(self.save_dir, exist_ok=True)
            bmp_path = os.path.abspath(os.path.join(self.save_dir, "roi_mask.bmp"))
            ok = cv2.imwrite(bmp_path, self.slm_mask)
            if not ok:
                raise IOError("cv2.imwrite returned False")

            meta_path = os.path.abspath(os.path.join(self.save_dir, "roi_mask_meta.npz"))
            x, y, w, h = self._get_roi_rect_display()
            np.savez(
                meta_path,
                rect=np.array([x, y, w, h], dtype=np.int32),
                display_flip_x=True,
                affine=(self.affine if self.affine is not None else np.zeros((2, 3), dtype=np.float32)),
                has_affine=bool(self.affine is not None),
            )

            self.maskSaved.emit(bmp_path)
            return bmp_path
        except Exception as e:
            self.statusBar().showMessage(f"Warning: failed to save ROI mask: {e}", 6000)
            return None

    @Slot()
    def on_make_mask(self) -> None:
        slm_mask = self._compute_mask_from_roi()
        if slm_mask is None:
            return

        self.slm_mask = slm_mask
        saved_path = self._persist_roi_mask()

        if saved_path:
            self.status_lbl.setText(f"Mask ready ({self.slm_w}x{self.slm_h}). Saved: {os.path.basename(saved_path)}")
        else:
            self.status_lbl.setText(f"Mask ready ({self.slm_w}x{self.slm_h}).")

        # Best-effort: keep MainGui in sync
        try:
            self.host_gui.roi_dmd_mask = self.slm_mask
            if saved_path:
                self.host_gui.roi_dmd_mask_path = saved_path
        except Exception:
            pass

    @Slot()
    def on_apply_mask(self) -> None:
        if self.slm_mask is None:
            QMessageBox.warning(self, "DMD", "No mask prepared. Click 'Make DMD Mask from ROI' first.")
            return
        if self.slm_name is None:
            QMessageBox.warning(self, "DMD", "SLM/DMD not available from Core.")
            return
        try:
            self.core.set_slm_image(self.slm_name, self.slm_mask)
            self.core.display_slm_image(self.slm_name)
            self.statusBar().showMessage("Mask applied to DMD.", 2000)
        except Exception as e:
            QMessageBox.critical(self, "DMD Error", f"Failed to send mask to DMD: {e}")

    @Slot()
    def on_clear_dmd(self) -> None:
        if self.slm_name is None or self.slm_w is None or self.slm_h is None:
            return
        try:
            blank = np.zeros((self.slm_h, self.slm_w), dtype=np.uint8)
            self.core.set_slm_image(self.slm_name, blank)
            self.core.display_slm_image(self.slm_name)
            self.statusBar().showMessage("DMD cleared.", 2000)
        except Exception as e:
            QMessageBox.critical(self, "DMD Error", f"Failed to clear DMD: {e}")

    # ---------------------------- Arduino ----------------------------

    @Slot()
    def on_connect_arduino(self) -> None:
        # If MainGui passed a connected ArduinoComm, do not re-open the port.
        if self.arduino_comm is not None:
            self.statusBar().showMessage("Arduino already connected (shared from MainGui).", 3000)
            return

        port = self.port_edit.text().strip() or "COM13"
        try:
            self.arduino_comm = ArduinoComm.connect(port=port, baudrate=19200, timeout=2)
            if self.arduino_comm is None:
                QMessageBox.critical(self, "Arduino", f"Failed to connect on {port}. See console for details.")
            else:
                self.statusBar().showMessage(f"Arduino connected on {port}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Arduino", f"Error: {e}")

    # ---------------------------- Stimulation ----------------------------

    def _ensure_ready_for_stim(self) -> bool:
        if self.slm_name is None:
            QMessageBox.warning(self, "DMD", "SLM/DMD not available from Core.")
            return False

        if self.slm_mask is None:
            slm_mask = self._compute_mask_from_roi()
            if slm_mask is None:
                QMessageBox.warning(self, "Mask", "No DMD mask is prepared. Create it first.")
                return False
            self.slm_mask = slm_mask

        if self.arduino_comm is None:
            QMessageBox.warning(self, "Arduino", "Connect Arduino first.")
            return False

        return True

    def _set_controls_enabled(self, enabled: bool) -> None:
        for w in [
            self.freq_hz,
            self.on_time_ms,
            self.duration_s,
            self.apply_mask_btn,
            self.clear_dmd_btn,
            self.make_mask_btn,
            self.reset_roi_btn,
            self.snap_btn,
            self.load_affine_btn,
            self.load_old_affine_btn,
            self.connect_btn,
            self.port_edit,
            self.manual_btn,
            self.run_btn,
        ]:
            w.setEnabled(enabled)
        self.stop_btn.setEnabled(not enabled)

    def _set_active(self, active: bool) -> None:
        size = 14
        self.active_led.setFixedSize(size, size)
        color = "#D11" if active else "#666"
        self.active_led.setStyleSheet(f"background-color: {color}; border-radius: {size//2}px; border: 1px solid #333;")
        self.active_lbl.setStyleSheet("color: #D11;" if active else "color: #666;")

    def _start_activity(self, total_pulses: int) -> None:
        self._set_active(True)
        self.stim_progress.setMaximum(max(1, total_pulses))
        self.stim_progress.setValue(0)
        self._set_controls_enabled(False)

    def _finish_activity(self) -> None:
        self._set_active(False)
        self._set_controls_enabled(True)

    @Slot()
    def on_manual(self) -> None:
        if not self._ensure_ready_for_stim():
            return

        try:
            self.core.set_slm_image(self.slm_name, self.slm_mask)
            self.core.display_slm_image(self.slm_name)
        except Exception as e:
            QMessageBox.critical(self, "DMD Error", f"Failed to display mask: {e}")
            return

        f = max(0.1, float(self.freq_hz.value()))
        period_ms = max(1, int(round(1000.0 / f)))
        on_ms = int(self.on_time_ms.value())
        if on_ms >= period_ms:
            on_ms = max(1, period_ms - 1)
            self.statusBar().showMessage(f"On-time clamped to {on_ms} ms (< period {period_ms} ms).", 4000)

        ok = self.arduino_comm.send_message([1], period_ms, on_ms)
        if ok:
            self.statusBar().showMessage("Manual pulse sent.", 2000)
        else:
            QMessageBox.critical(self, "Arduino", "No ACK from Arduino (manual pulse).")

    @Slot()
    def on_run(self) -> None:
        if not self._ensure_ready_for_stim():
            return
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "Stim", "A stimulation run is already active.")
            return

        try:
            self.core.set_slm_image(self.slm_name, self.slm_mask)
            self.core.display_slm_image(self.slm_name)
        except Exception as e:
            QMessageBox.critical(self, "DMD Error", f"Failed to display mask: {e}")
            return

        f = max(0.1, float(self.freq_hz.value()))
        T = max(0.1, float(self.duration_s.value()))
        period_ms = max(1, int(round(1000.0 / f)))
        on_ms = int(self.on_time_ms.value())
        if on_ms >= period_ms:
            on_ms = max(1, period_ms - 1)
            self.statusBar().showMessage(f"On-time clamped to {on_ms} ms (< period {period_ms} ms).", 4000)

        total_pulses = max(1, int(math.floor(f * T)))  # floor to match earlier behavior

        self.worker = StimWorker(self.arduino_comm, period_ms, on_ms, total_pulses, self)
        self.worker.progress.connect(self._on_worker_progress)
        self.worker.finished.connect(self._on_worker_finished)

        self.status_lbl.setText(f"Running: {total_pulses} pulses @ {f:.2f} Hz (period {period_ms} ms, on {on_ms} ms)")
        self._start_activity(total_pulses)
        self.worker.start()

    @Slot()
    def on_stop(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
        self.status_lbl.setText("Stopped.")
        self._finish_activity()

    @Slot(int)
    def _on_worker_progress(self, sent: int) -> None:
        self.stim_progress.setValue(sent)
        self.status_lbl.setText(f"Delivered {sent} pulses...")

    @Slot(bool, str)
    def _on_worker_finished(self, ok: bool, msg: str) -> None:
        self._finish_activity()
        self.status_lbl.setText(f"Finished: {msg}")
        if not ok:
            QMessageBox.critical(self, "Stim", msg)

    def closeEvent(self, event) -> None:
        try:
            if self.worker is not None and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait(1500)
        except Exception:
            pass

        try:
            if self.slm_name and self.slm_w and self.slm_h:
                blank = np.zeros((self.slm_h, self.slm_w), dtype=np.uint8)
                self.core.set_slm_image(self.slm_name, blank)
                self.core.display_slm_image(self.slm_name)
        except Exception:
            pass

        super().closeEvent(event)
