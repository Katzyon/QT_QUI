"""
Simple DMD Stim GUI — Help

What this app does
------------------
A lightweight PySide6 GUI for: 
1) snapping a camera image of the neuronal culture (via Micro-Manager / PycroManager),
2) selecting rectangular ROIs on the image that become a DMD/SLM stimulation mask,
3) stimulating either once (manual) or as a timed train (frequency + duration) through an Arduino.

Key behaviors & assumptions
---------------------------
• Display orientation matches MainGUI: the live image shown is horizontally flipped (np.fliplr).
  ROI coordinates are mapped back to the RAW camera frame internally before building the mask.
• ROI → DMD mapping:
  - If a 2×3 camera→DMD affine transform is loaded, the mask is warped with cv2.warpAffine.
  - If not, the ROI is resized to the SLM resolution (approximate).
• Arduino timing:
  - Each chunk is sent as: "[indices],period_ms,on_ms\\n" and waits for "Message received".
  - The GUI then BLOCKS until the Arduino prints "Sequence finished" for that chunk,
    and only then sends the next chunk. This prevents overlap/compression.
  - If on_time_ms ≥ period_ms, the GUI clamps on_time_ms to period_ms - 1 and warns.
  - Total pulses for trains use floor(freq * duration) to match prior behavior.
• While a train runs: a red “ACTIVE” indicator + progress bar are shown and most controls are disabled.

Requirements
------------
• Python packages: PySide6, numpy, opencv-python, pycromanager
• Micro-Manager running with your camera and SLM/DMD configured
• Local modules available on PYTHONPATH: Camera.py, arduino_comm.py
• Arduino serial default: COM13 (editable in the GUI)

Quick start
-----------
1) Launch Micro-Manager with your config; start this app.
2) The app auto-connects to COM13 if present (you can connect manually too).
3) Click “Load Old Affine” to restore your 2×3 affine (or “Load Affine (.npy)” to select a file).
4) Click “Snap Image”. Draw one or more ROIs (click-drag; release to finalize). Use “Delete ROI” or “Clear ROIs” to reset.
5) Click “Make DMD Mask from ROIs”, then “Apply Mask to DMD”.
6) Choose Freq (Hz), On-time (ms), Duration (s). 
   - “Manual Stim (1 pulse)” for a single pulse.
   - “Run Stim Train” for a timed train. Use “Stop” to abort early.

Troubleshooting
---------------
• “Core/Camera not initialized” → Make sure Micro-Manager is running and the device adapter names match.
• “No ACK from Arduino” → Check port/baud; confirm the firmware prints "Message received".
• Train stalls between chunks → Confirm the firmware prints "Sequence finished" when a chunk completes.
• ROI looks mirrored on the mask → Ensure the correct affine is loaded; the display flip is intentional.
• Deprecation warnings about QMouseEvent.pos() → The code uses event.position().toPoint() (Qt6-safe).

Notes
-----
• The DMD mask is static during stimulation; the Arduino drives pulses via TTL.
• If you want external-triggered sequence stepping instead of a static mask, add a toggle and use
  the Micro-Manager SLM sequence API (`load_slm_sequence` / `start_slm_sequence`) with your TTL routing.
"""



import sys, os, math, threading
import time
import numpy as np
import pyqtgraph as pg
import cv2
from typing import Optional

from PySide6.QtCore import Qt, QRect, QSize, QPoint, QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSizePolicy, QWidget, QLabel, QPushButton, QFileDialog,
    QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox, QLineEdit, QSpinBox,
    QDoubleSpinBox, QMessageBox, QStatusBar, QRubberBand, QProgressBar,
    QCheckBox, QComboBox
)

from pycromanager import Core


import Camera
from arduino_comm import ArduinoComm, build_stdp_message_payload

def np_to_qimage_u8gray(arr: np.ndarray) -> QImage:
    arr = np.ascontiguousarray(arr)
    h, w = arr.shape
    return QImage(arr.data, w, h, arr.strides[0], QImage.Format_Grayscale8)

class ROIImageLabel(QLabel):
    rectChanged = Signal(QRect)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setMouseTracking(True)
        self._rubber = QRubberBand(QRubberBand.Rectangle, self)
        self._origin = QPoint()
        self._has_image = False
        self._qimg_copy = None
        self._current_rect = None
        self._dragging = False

    def set_numpy_image(self, arr_u8):
        # Qt's QImage does not support NumPy arrays with negative/odd strides
        # (e.g., np.fliplr views). Force a contiguous, positive-stride buffer.
        arr_u8 = np.ascontiguousarray(arr_u8)
        qimg = np_to_qimage_u8gray(arr_u8)
        self._qimg_copy = qimg.copy()
        self.setPixmap(QPixmap.fromImage(self._qimg_copy))
        self.setFixedSize(self.pixmap().size())
        self._has_image = True

    def current_rect(self) -> QRect:
        return QRect(self._current_rect) if self._current_rect is not None else QRect()

    def clear_roi(self):
        self._current_rect = None
        self._dragging = False
        if self._rubber.isVisible():
            self._rubber.hide()
        self.rectChanged.emit(QRect())

    def mousePressEvent(self, event):
        if not self._has_image or event.button() != Qt.LeftButton:
            return
        self._dragging = True
        self._origin = event.position().toPoint()
        self._rubber.setGeometry(QRect(self._origin, QSize()))
        if not self._rubber.isVisible():
            self._rubber.show()

    def mouseMoveEvent(self, event):
        if not (self._has_image and self._dragging and (event.buttons() & Qt.LeftButton)):
            return
        rect = QRect(self._origin, event.position().toPoint()).normalized()
        rect = rect.intersected(self.rect())
        self._rubber.setGeometry(rect)
        self.rectChanged.emit(rect)

    def mouseReleaseEvent(self, event):
        if not self._has_image or event.button() != Qt.LeftButton:
            return
        rect = self._rubber.geometry().intersected(self.rect())
        self._current_rect = QRect(rect) if rect.isValid() else None
        self._dragging = False
        self.rectChanged.emit(self.current_rect() if self._current_rect is not None else QRect())

class StimWorker(QThread):
    progress = Signal(int)           # total pulses delivered so far
    finished = Signal(bool, str)     # ok, message

    def __init__(
        self,
        arduino_comm: ArduinoComm,
        period_ms: int,
        on_time_ms: int,
        total_pulses: int,
        parent=None,
        use_stdp: bool = False,
        stdp_distance_px: float = 100.0,
        duration_s: float = 5.0,
    ):
        super().__init__(parent)
        self.arduino = arduino_comm
        self.period_ms = int(period_ms)
        self.on_time_ms = int(on_time_ms)
        self.total = max(0, int(total_pulses))
        self.use_stdp = bool(use_stdp)
        self.stdp_distance_px = float(stdp_distance_px)
        self.duration_s = float(duration_s)
        self._stop = False
        self._stop_event = threading.Event()

    def stop(self):
        self._stop = True
        self._stop_event.set()

    def _max_indices_for_message(self):
        overhead = len(f"[],{self.period_ms},{self.on_time_ms}\n")
        bytes_per_index = 2  # "1,"
        max_bytes = 58
        return max(1, (max_bytes - overhead) // bytes_per_index)

    def run(self):
        if self.arduino is None:
            self.finished.emit(False, "Arduino not connected")
            return

        if self.use_stdp:
            try:
                # For STDP 4-field mode: [0,1],period_ms,on_time_ms,ISI_ms
                # ISI (inter-stimulus interval) is derived from stdp_distance_px
                isi_ms = int(min(1000, max(1, round(self.stdp_distance_px))))
                period_ms_stdp, on_ms_stdp, isi_ms_stdp = build_stdp_message_payload(
                    self.period_ms,
                    self.on_time_ms,
                    isi_ms
                )
                ok = self.arduino.send_stdp_message(period_ms_stdp, on_ms_stdp, isi_ms_stdp)
                if not ok:
                    self.finished.emit(False, "Arduino did not acknowledge STDP message.")
                    return

                # Wait for Arduino to complete, but respect duration_s timeout
                # Add 2s buffer to allow Arduino time to finish cleanly
                timeout_s = self.duration_s + 2.0
                start_time = time.time()
                
                while time.time() - start_time < timeout_s and not self._stop:
                    resp = self.arduino.wait_for_sequence_end_blocking(self._stop_event)
                    if resp is not None:
                        # Arduino signaled completion before timeout
                        self.progress.emit(self.total)
                        self.finished.emit(True, f"STDP protocol completed ({self.total} pulses equivalent).")
                        return
                
                # Timeout reached or user stopped during desired duration
                self.progress.emit(self.total)
                elapsed = time.time() - start_time
                self.finished.emit(True, f"STDP protocol stopped after {elapsed:.1f}s (duration: {self.duration_s}s).")
            except Exception as e:
                self.finished.emit(False, f"Error: {e}")
            return

        max_indices = self._max_indices_for_message()
        sent = 0
        try:
            while sent < self.total and not self._stop:
                n = min(max_indices, self.total - sent)
                indices = [1] * n

                # 1) Send message and wait for ACK ("Message received")
                ok = self.arduino.send_message(indices, self.period_ms, self.on_time_ms)
                if not ok:
                    self.finished.emit(False, "Arduino did not acknowledge (timeout).")
                    return

                # 2) Block until Arduino signals the sequence finished for this chunk
                resp = self.arduino.wait_for_sequence_end_blocking(self._stop_event)
                if resp is None:
                    if self._stop:
                        self.finished.emit(False, "Stopped.")
                    else:
                        self.finished.emit(False, "No 'Sequence finished' from Arduino.")
                    return

                sent += n
                self.progress.emit(sent)

            self.finished.emit(True, f"Delivered {sent} pulses.")
        except Exception as e:
            self.finished.emit(False, f"Error: {e}")

class SimpleStimWindow(QMainWindow):
    """Standalone or embeddable ROI→DMD stimulation GUI.

    When integrating into a parent GUI (e.g., MainGui), pass shared handles:
      - core: pycromanager Core
      - camera: Camera.getImage(core)
      - arduino_comm: ArduinoComm instance
      - affine: 2x3 camera→DMD affine (np.float32)
      - save_dir: directory where the last ROI mask should be persisted for reuse

    The window will emit `maskSaved` whenever a new ROI-derived DMD mask is saved.
    """

    maskSaved = Signal(str)  # absolute file path to saved DMD mask (BMP)

    def __init__(
        self,
        host_gui=None,
        save_dir: Optional[str] = None,
        core=None,
        camera=None,
        arduino_comm: Optional[ArduinoComm] = None,
        affine: Optional[np.ndarray] = None,
    ):
        super().__init__()
        self.setWindowTitle("Simple DMD Stim v3 (PySide6)")
        self.resize(1520, 800) # Set the GUI size


        # Optional integration points
        self.host_gui = host_gui
        self.save_dir = save_dir

        self.core = core
        self.camera = camera
        self.last_raw_frame = None
        self.display_flip_x = True
        self.affine = affine
        # Core ownership tracking: if we create our own Core() we must release devices on close.
        self._owns_core = False

        self.slm_name = None
        self.slm_w = None
        self.slm_h = None
        self.slm_mask = None
        self.arduino_comm = arduino_comm
        self.worker = None
        self.stdp_enabled = False
        self.stdp_distance_px = 300.0
        self.stdp_roi1 = None
        self.stdp_roi2 = None
        self.stdp_mask_1 = None
        self.stdp_mask_2 = None
        self._stdp_direction = "Right"
        self._stdp_syncing = False
        # self.parent_gui = None

        self._build_ui()
        self._connect_signals()


        # If hosted by MainGUI and an ArduinoComm was injected, prevent accidental re-connect
        if self.host_gui is not None and self.arduino_comm is not None:
            try:
                self.port_edit.setDisabled(True)
                self.connect_btn.setDisabled(True)
                self.connect_btn.setText("Arduino (shared)")
            except Exception:
                pass
        # Initialize hardware only if not injected
        if self.core is None or self.camera is None:
            self._init_core_and_camera()
        else:
            # If core was injected, still discover SLM params
            try:
                self.slm_name = self.core.get_slm_device()
                self.slm_w = self.core.get_slm_width(self.slm_name)
                self.slm_h = self.core.get_slm_height(self.slm_name)
                self.statusBar().showMessage(
                    f"Connected (shared Core): SLM='{self.slm_name}' ({self.slm_w}x{self.slm_h})",
                    5000,
                )
            except Exception as e:
                QMessageBox.critical(self, "Core Error", f"Failed to query SLM from shared Core.\n\nDetails: {e}")
                self.core = None
                self.camera = None

        # Arduino: only auto-connect if not injected
        if self.arduino_comm is None:
            self._auto_connect_arduino(port="COM13")

        # Affine: only prompt-load if not injected
        if self.affine is None:
            self.load_old_affine()

        # Default save location: if hosted by MainGui, prefer its DMD_dir
        if self.save_dir is None and self.host_gui is not None:
            self.save_dir = getattr(self.host_gui, "ROI_dir", None)

    def _persist_roi_mask(self) -> Optional[str]:
        """Persist the currently prepared DMD mask to disk for reuse by a host GUI."""
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

            rects = self._get_all_roi_rects_display()
            rect_vals = self._get_current_roi_rect_display()
            if rect_vals is None:
                rect_vals = (0, 0, 0, 0)
            xd0, yd0, ww, hh = rect_vals
            rect = QRect(int(xd0), int(yd0), int(ww), int(hh))
            rects_arr = np.array(rects, dtype=np.float32) if rects else np.zeros((0, 4), dtype=np.float32)

            stdp_display = self.get_stdp_roi_rects_display()
            stdp_original = self.get_stdp_roi_rects_original()

            def rect_array(rect_value):
                if rect_value is None:
                    return np.array([], dtype=np.float32)
                return np.array(rect_value, dtype=np.float32)

            stdp_roi1_display = rect_array(stdp_display[0] if len(stdp_display) > 0 else None)
            stdp_roi2_display = rect_array(stdp_display[1] if len(stdp_display) > 1 else None)
            stdp_roi1_original = rect_array(stdp_original[0] if len(stdp_original) > 0 else None)
            stdp_roi2_original = rect_array(stdp_original[1] if len(stdp_original) > 1 else None)

            meta_path = os.path.abspath(os.path.join(self.save_dir, "roi_mask_meta.npz"))
            np.savez(
                meta_path,
                rect=np.array([rect.x(), rect.y(), rect.width(), rect.height()], dtype=np.int32),
                rects=rects_arr,
                active_roi_index=np.array([self._active_roi_index()], dtype=np.int32),
                display_flip_x=bool(self.display_flip_x),
                affine=(self.affine if self.affine is not None else np.zeros((2, 3), dtype=np.float32)),
                has_affine=bool(self.affine is not None),
                stdp_enabled=bool(self.stdp_enabled),
                stdp_distance_px=float(self.stdp_distance_px),
                stdp_direction=np.array(self._stdp_direction),
                stdp_roi1_display=stdp_roi1_display,
                stdp_roi2_display=stdp_roi2_display,
                stdp_roi1_original=stdp_roi1_original,
                stdp_roi2_original=stdp_roi2_original,
            )

            if self.stdp_enabled and self.stdp_mask_1 is not None and self.stdp_mask_2 is not None:
                cv2.imwrite(os.path.abspath(os.path.join(self.save_dir, "stdp_roi1_mask.bmp")), self.stdp_mask_1)
                cv2.imwrite(os.path.abspath(os.path.join(self.save_dir, "stdp_roi2_mask.bmp")), self.stdp_mask_2)

            self.maskSaved.emit(bmp_path)
            return bmp_path
        except Exception as e:
            try:
                self.statusBar().showMessage(f"Warning: failed to save last ROI mask: {e}", 6000)
            except Exception:
                pass
            return None

    def _build_ui(self):
        central = QWidget(self); self.setCentralWidget(central)
        # Use pyqtgraph ImageView (same widget family as MainGui) for display
        self.imageview = pg.ImageView()
        try:
            self.imageview.ui.roiBtn.hide()
            self.imageview.ui.menuBtn.hide()
            self.imageview.ui.histogram.show()
        except Exception:
            pass
        self._display_shape = None  # (H, W) of last displayed frame
        # ROI storage: one entry per independent RectROI. `roi_params` is reserved
        # for future per-ROI stimulation settings.
        self.rois = []
        self.roi_params = {}
        self.active_roi = None
        self._roi_pen = pg.mkPen('y', width=2)
        self._active_roi_pen = pg.mkPen('c', width=3)
        self._stdp_roi2_pen = pg.mkPen('#ff4fd8', width=2)
        self._roi_drag_active = False
        self._roi_drag_origin = None
        self._roi_drag_item = None
        self._viewbox_mouse_drag_event = None
        image_box = QGroupBox("Camera image / ROI")
        v = QVBoxLayout(image_box)
        v.addWidget(self.imageview)

        ctl_box = QGroupBox("Controls"); grid=QGridLayout(ctl_box)
        ctl_box.setMinimumWidth(500)
        ctl_box.setMaximumWidth(620)
        ctl_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        image_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)



        # Row 0: Capture & affine
        self.snap_btn=QPushButton("Snap Image"); self.load_affine_btn=QPushButton("Load Affine (2x3 .npy)"); self.load_old_affine_btn=QPushButton("Load Old Affine")
        grid.addWidget(self.snap_btn,0,0); grid.addWidget(self.load_affine_btn,0,1); grid.addWidget(self.load_old_affine_btn,0,2)

        # Row 1: ROI
        self.make_mask_btn=QPushButton("Make DMD Mask from ROIs"); 
        #self.current_rect_label=QLabel("ROIs: -")
        self.delete_roi_btn=QPushButton("Delete ROI"); 
        self.clear_roi_btn=QPushButton("Clear ROIs")
        
        grid.addWidget(self.make_mask_btn,1,0)
        #grid.addWidget(self.current_rect_label,1,1,1,3)
        grid.addWidget(self.delete_roi_btn,1,4)
        grid.addWidget(self.clear_roi_btn,1,5)


        # Row 2: DMD
        self.apply_mask_btn=QPushButton("Apply Mask to DMD"); self.clear_dmd_btn=QPushButton("Clear DMD")
        grid.addWidget(self.apply_mask_btn,2,0,1,2); grid.addWidget(self.clear_dmd_btn,2,2,1,2)

        # Row 3: Run / Manual
        self.manual_btn=QPushButton("Manual Stim (1 pulse)"); self.run_btn=QPushButton("Run Stim Train"); self.stop_btn=QPushButton("Stop")
        grid.addWidget(self.manual_btn,3,0,1,2)
        grid.addWidget(self.run_btn,3,2,1,2)
        grid.addWidget(self.stop_btn,3,4,1,2)

        # Row 4: Stim params
        self.freq_hz=QDoubleSpinBox(); self.freq_hz.setRange(0.1,1000.0); self.freq_hz.setDecimals(2); self.freq_hz.setValue(5.0)
        self.on_time_ms=QSpinBox(); self.on_time_ms.setRange(1,1000); self.on_time_ms.setValue(10)
        self.duration_s=QDoubleSpinBox(); self.duration_s.setRange(0.1,3600.0); self.duration_s.setDecimals(1); self.duration_s.setValue(5.0)
        grid.addWidget(QLabel("Freq (Hz):"),4,0)
        grid.addWidget(self.freq_hz,4,1)
        grid.addWidget(QLabel("On-time (ms):"),4,2)
        grid.addWidget(self.on_time_ms,4,3)
        grid.addWidget(QLabel("Duration (s):"),4,4)
        grid.addWidget(self.duration_s,4,5)

        # Row 5: STDP
        self.stdp_checkbox = QCheckBox("STDP")
        self.stdp_distance = QDoubleSpinBox()
        self.stdp_distance.setRange(1.0, 100000.0)
        self.stdp_distance.setDecimals(1)
        self.stdp_distance.setValue(self.stdp_distance_px)
        self.stdp_direction = QComboBox()
        self.stdp_direction.addItems(["Right", "Left", "Up", "Down"])
        self.stdp_direction.setCurrentText(self._stdp_direction)
        grid.addWidget(self.stdp_checkbox, 5, 0)
        grid.addWidget(QLabel("STDP distance"), 5, 1)
        grid.addWidget(self.stdp_distance, 5, 2)
        grid.addWidget(QLabel("Direction"), 5, 3)
        grid.addWidget(self.stdp_direction, 5, 4)

        # Row 6: Activity indicator + progress
        self.active_led = QLabel(); self._set_active_led(False)
        self.active_lbl = QLabel("Stim ACTIVE")
        self.stim_progress = QProgressBar(); self.stim_progress.setMinimum(0); self.stim_progress.setMaximum(1); self.stim_progress.setValue(0)
        grid.addWidget(self.active_led, 6, 0); grid.addWidget(self.active_lbl, 6, 1); grid.addWidget(self.stim_progress, 6, 2, 1, 4)
        # Row 7: Status
        self.status_lbl=QLabel(""); grid.addWidget(self.status_lbl,7,0,1,6)

        # Row 8: Arduino
        self.port_edit=QLineEdit("COM13"); self.connect_btn=QPushButton("Connect Arduino")
        grid.addWidget(QLabel("Arduino Port:"),8,0)
        grid.addWidget(self.port_edit,8,1)
        grid.addWidget(self.connect_btn,8,2)

        # Row 9: ROI information
        self.roi_info_title = QLabel("ROI information")
        self.roi_info_title.setStyleSheet("font-weight: bold;")

        self.current_rect_label = QLabel("ROIs: -")
        self.current_rect_label.setWordWrap(True)
        self.current_rect_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.current_rect_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # Prevent the label from forcing the controls panel wider.
        self.current_rect_label.setMinimumWidth(0)
        self.current_rect_label.setMaximumWidth(16777215)
        self.current_rect_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Reserve space for several lines so the panel height remains stable.
        self.current_rect_label.setMinimumHeight(65)
        self.current_rect_label.setStyleSheet(
            """
            QLabel {
                border: 1px solid #b8b8b8;
                border-radius: 3px;
                padding: 5px;
                background-color: #f7f7f7;
            }
            """
        )

        grid.addWidget(self.roi_info_title, 9, 0, 1, 6)
        grid.addWidget(self.current_rect_label, 10, 0, 1, 6)

        main = QHBoxLayout(central)
        main.addWidget(image_box, 1)
        main.addWidget(ctl_box, 0)

        self._setup_imageview_roi()
        #self.setStatusBar(QStatusBar(self)); exit_act=QAction("&Exit",self); exit_act.triggered.connect(self.close); self.menuBar().addMenu("&File").addAction(exit_act)

        self.statusBar().setStyleSheet("""
            QStatusBar {
                border-top: 1px solid lightgray;
            }
            QStatusBar QLabel {
                color: red;
                font-weight: bold;
            }
        """)
    
    
    def _connect_signals(self):
            self.snap_btn.clicked.connect(self.on_snap)
            self.load_affine_btn.clicked.connect(self.on_load_affine_generic)
            self.load_old_affine_btn.clicked.connect(self.load_old_affine)
            self.make_mask_btn.clicked.connect(self.on_make_mask)
            self.delete_roi_btn.clicked.connect(self.on_delete_roi)
            self.clear_roi_btn.clicked.connect(self.on_clear_roi)
            # No explicit save button; saving happens automatically on mask creation.
            self.apply_mask_btn.clicked.connect(self.on_apply_mask)
            self.clear_dmd_btn.clicked.connect(self.on_clear_dmd)
            self.connect_btn.clicked.connect(self.on_connect_arduino)
            self.manual_btn.clicked.connect(self.on_manual)
            self.run_btn.clicked.connect(self.on_run)
            self.stop_btn.clicked.connect(self.on_stop)
            self.stdp_checkbox.toggled.connect(self.on_stdp_toggled)
            self.stdp_distance.valueChanged.connect(self.on_stdp_distance_changed)
            self.stdp_direction.currentTextChanged.connect(self.on_stdp_direction_changed)

    def _init_core_and_camera(self):
        """Initialize Core/Camera.

        In current pycromanager versions, `Core()` is the supported public API for controlling a
        running Micro-Manager instance via its ZMQ server (Tools → Options → “Run server on port 4827”).

        This GUI is intended to *share* the same Micro-Manager instance. Therefore:
          • We connect to the Micro-Manager server via `Core(...)`
          • We do **not** attempt to start a separate, independent device-owning backend automatically
            (that is a common cause of SLM/DMD lockouts when Micro-Manager is also open).
        """
        try:
            # Core accepts kwargs in modern pycromanager; fall back gracefully for older versions.
            try:
                self.core = Core(convert_camel_case=True, port=4827, timeout=500, new_socket=False)
            except TypeError:
                self.core = Core(convert_camel_case=True)

            # Never unload devices from a shared Micro-Manager instance
            self._owns_core = False

            self.camera = Camera.getImage(self.core)
            self.slm_name = self.core.get_slm_device()
            self.slm_w = self.core.get_slm_width(self.slm_name)
            self.slm_h = self.core.get_slm_height(self.slm_name)

            self.statusBar().showMessage(
                f"Connected (Micro-Manager server): SLM='{self.slm_name}' ({self.slm_w}x{self.slm_h})",
                7000,
            )
        except Exception as e:
            msg = f"""Failed to connect to Micro-Manager via pycromanager.Core().

Most common causes:
  • Micro-Manager is not running, or
  • Micro-Manager is running but the Pycro-Manager server is not enabled.

Fix:
  1) Open Micro-Manager
  2) Tools → Options → check 'Run server on port 4827'
  3) Restart Micro-Manager if prompted

If you specifically want a standalone backend, do it explicitly with:
  pycromanager.start_headless(...)

Details: {e}
"""
            QMessageBox.critical(self, "Core Error", msg)
            self.core = None
            self.camera = None
            self.slm_name = None
            self.slm_w = None
            self.slm_h = None
            self._owns_core = False

    def _auto_connect_arduino(self, port="COM13"):
        try:
            self.arduino_comm = ArduinoComm.connect(port=port, baudrate=19200, timeout=2)
            if self.arduino_comm is not None:
                self.statusBar().showMessage(f"Arduino auto-connected on {port}", 4000)
        except Exception: pass

    @Slot()
    def on_connect_arduino(self):
        # When embedded in MainGUI, ArduinoComm should be shared; do not open COM13 twice.
        if self.host_gui is not None and self.arduino_comm is not None:
            self.statusBar().showMessage("Arduino already connected (shared from MainGUI)", 3000)
            return
        port=self.port_edit.text().strip() or "COM13"
        try:
            self.arduino_comm = ArduinoComm.connect(port=port, baudrate=19200, timeout=2)
            if self.arduino_comm is None:
                QMessageBox.critical(self,"Arduino",f"Failed to connect on {port}. See console for details.")
            else:
                self.statusBar().showMessage(f"Arduino connected on {port}",3000)
        except Exception as e:
            QMessageBox.critical(self,"Arduino",f"Error: {e}")

    @Slot()
    def on_load_affine_generic(self):
        path,_=QFileDialog.getOpenFileName(self,"Load affine (2x3 .npy)","","NumPy arrays (*.npy)")
        if not path: return
        try:
            A=np.load(path); 
            if A.shape!=(2,3): raise ValueError(f"Affine must be 2x3, got {A.shape}")
            self.affine=A.astype(np.float32); QMessageBox.information(self,"Affine",f"Loaded affine from:\n{path}\n\n{A}")
        except Exception as e:
            QMessageBox.critical(self,"Affine Error",f"Failed to load affine: {e}")

    @Slot()
    def load_old_affine(self):
        box=QMessageBox(self); box.setWindowTitle("Old affine transform"); box.setText("Load old affine transform?")
        box.setStandardButtons(QMessageBox.Yes|QMessageBox.No); box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        reply=box.exec()
        if reply==QMessageBox.Yes:
            default_path=r"G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Images\affine_transform.npy"
            path=default_path if os.path.exists(default_path) else ""
            if not path:
                alt,_=QFileDialog.getOpenFileName(self,"Select affine_transform.npy","","NumPy arrays (*.npy)"); path=alt
            if path:
                try:
                    A=np.load(path); 
                    if A.shape!=(2,3): raise ValueError(f"Expected 2x3 matrix, got {A.shape}")
                    self.affine=A.astype(np.float32); self.statusBar().showMessage(f"Loaded old affine from: {path}",5000)
                except Exception as e:
                    QMessageBox.critical(self,"Affine Error",f"Failed to load affine: {e}")
            else:
                QMessageBox.information(self,"Affine","No file selected.")
        else:
            QMessageBox.information(self,"DMD Calibration","Press your calibration flow to create a new affine.")

    @Slot()
    def on_snap(self):
        if self.camera is None or self.core is None:
            QMessageBox.warning(self, "Camera", "Core/Camera not initialized.")
            return
        try:
            raw = self.camera.snap_image(self.core)
            self.last_raw_frame = raw.copy()

            # Match MainGUI orientation (horizontal flip only)
            frame_disp = np.fliplr(self.last_raw_frame).copy()
            # ImageView expects (row, col) ndarray; ensure contiguous to avoid Qt stride issues
            frame_disp = np.ascontiguousarray(frame_disp)
            self._display_shape = frame_disp.shape
            self.imageview.setImage(frame_disp, autoLevels=True)

            self.statusBar().showMessage(
                "Image snapped (displayed as fliplr).", 2000
            )
        except Exception as e:
            QMessageBox.critical(self, "Snap Error", f"Failed to snap image: {e}")

    @Slot(QRect)
    def on_rect_changed(self, rect: QRect):
        if rect.isValid() and rect.width()>0 and rect.height()>0:
            self.current_rect_label.setText(f"ROI: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")
        else:
            self.current_rect_label.setText("ROI: -")


    def _setup_imageview_roi(self):
        """Configure ImageView display and drag-to-create multi-ROI behavior."""
        # Ensure axes behave like image pixels (0,0 at top-left; y down).
        try:
            vb = self.imageview.getView()
        except Exception:
            vb = None

        if vb is not None:
            vb.setAspectLocked(True)
            # Empty-image left drag creates a new ROI; RectROI keeps its own
            # move/resize behavior once created.
            self._viewbox_mouse_drag_event = vb.mouseDragEvent
            vb.mouseDragEvent = self._on_viewbox_mouse_drag_event

        # Initialize label
        self._on_pg_roi_changed()

    def _active_roi_index(self):
        try:
            return self.rois.index(self.active_roi)
        except Exception:
            return -1

    def _get_viewbox(self):
        try:
            return self.imageview.getView()
        except Exception:
            return None

    def _is_stdp_active(self) -> bool:
        return bool(self.stdp_enabled)

    def _is_stdp_roi(self, roi) -> bool:
        return roi is not None and roi in (self.stdp_roi1, self.stdp_roi2)

    def _get_stdp_direction_delta(self):
        distance = float(self.stdp_distance_px)
        mapping = {
            "Right": (distance, 0.0),
            "Left": (-distance, 0.0),
            "Up": (0.0, -distance),
            "Down": (0.0, distance),
        }
        return mapping.get(self._stdp_direction, (distance, 0.0))

    def _constrain_rect_to_display(self, rect):
        if rect is None:
            return None, False
        x, y, w, h = rect
        w = max(1.0, float(w))
        h = max(1.0, float(h))
        clipped = False
        if self._display_shape is None:
            return (float(x), float(y), w, h), clipped

        H_disp, W_disp = self._display_shape
        max_x = max(0.0, float(W_disp) - w)
        max_y = max(0.0, float(H_disp) - h)
        new_x = min(max(float(x), 0.0), max_x)
        new_y = min(max(float(y), 0.0), max_y)
        clipped = (abs(new_x - float(x)) > 1e-6) or (abs(new_y - float(y)) > 1e-6)
        return (new_x, new_y, w, h), clipped

    def _display_rect_to_original_rect(self, rect):
        bounds = self._display_rect_bounds(rect)
        raw_bounds = self._display_bounds_to_original_bounds(bounds)
        if raw_bounds is None:
            return None
        x0, y0, x1, y1 = raw_bounds
        return (x0, y0, x1 - x0, y1 - y0)

    def _apply_roi_rect(self, roi, rect):
        if roi is None or rect is None:
            return
        x, y, w, h = rect
        old_state = roi.blockSignals(True)
        try:
            roi.setPos((float(x), float(y)))
            roi.setSize((max(1.0, float(w)), max(1.0, float(h))))
        finally:
            roi.blockSignals(old_state)

    def _compute_stdp_roi2_rect(self, roi1_rect):
        if roi1_rect is None:
            return None, False
        x1, y1, w1, h1 = roi1_rect
        dx, dy = self._get_stdp_direction_delta()
        cx2 = float(x1) + (float(w1) / 2.0) + dx
        cy2 = float(y1) + (float(h1) / 2.0) + dy
        rect2 = (cx2 - (float(w1) / 2.0), cy2 - (float(h1) / 2.0), float(w1), float(h1))
        return self._constrain_rect_to_display(rect2)

    def _update_stdp_attrs_from_controls(self):
        self.stdp_enabled = bool(self.stdp_checkbox.isChecked())
        self.stdp_distance_px = float(self.stdp_distance.value())
        self._stdp_direction = self.stdp_direction.currentText() or "Right"

    def _sync_stdp_roi2_from_roi1(self):
        if not self._is_stdp_active() or self.stdp_roi1 is None:
            return
        roi1_rect = self._get_roi_rect_display(self.stdp_roi1)
        if roi1_rect is None:
            return
        if self.stdp_roi2 is None or self.stdp_roi2 not in self.rois:
            rect2, _ = self._compute_stdp_roi2_rect(roi1_rect)
            if rect2 is None:
                return
            self.stdp_roi2 = self._add_roi(*rect2, role="stdp_roi2", pen=self._stdp_roi2_pen)
        rect2, clipped = self._compute_stdp_roi2_rect(roi1_rect)
        if rect2 is None:
            return
        self._stdp_syncing = True
        try:
            self._apply_roi_rect(self.stdp_roi2, rect2)
        finally:
            self._stdp_syncing = False
        if clipped:
            self.statusBar().showMessage("STDP ROI 2 was clipped to stay inside the image.", 4000)

    def _ensure_stdp_pair(self, source_roi=None):
        if not self._is_stdp_active():
            return
        if source_roi is not None and source_roi in self.rois and source_roi is not self.stdp_roi2:
            self.stdp_roi1 = source_roi
        elif self.stdp_roi1 not in self.rois:
            primaries = [roi for roi in self.rois if roi is not self.stdp_roi2]
            self.stdp_roi1 = primaries[0] if primaries else None

        if self.stdp_roi1 is None:
            self.stdp_roi2 = None
            return

        for roi in list(self.rois):
            if roi not in (self.stdp_roi1, self.stdp_roi2):
                self._remove_roi(roi, select_next=False)

        self._sync_stdp_roi2_from_roi1()
        self._set_active_roi(self.stdp_roi1)

    def _disable_stdp_pairing(self):
        roi1 = self.stdp_roi1 if self.stdp_roi1 in self.rois else None
        roi2 = self.stdp_roi2 if self.stdp_roi2 in self.rois else None
        if roi2 is not None:
            self._remove_roi(roi2, select_next=False)
        self.stdp_enabled = False
        self.stdp_roi1 = roi1
        self.stdp_roi2 = None
        self.stdp_mask_1 = None
        self.stdp_mask_2 = None
        self._set_active_roi(roi1 if roi1 in self.rois else self.active_roi)

    @Slot(bool)
    def on_stdp_toggled(self, checked: bool):
        self._update_stdp_attrs_from_controls()

        vb = self._get_viewbox()
        saved_view_rect = None

        if vb is not None:
            try:
                saved_view_rect = vb.viewRect()
                vb.disableAutoRange()
            except Exception:
                pass

        if checked:
            self.statusBar().showMessage(
                "STDP mode enabled. Draw or adjust one ROI to create the paired ROI.",
                4000,
            )
            self._ensure_stdp_pair(self.active_roi)
        else:
            self._disable_stdp_pairing()
            self.statusBar().showMessage(
                "STDP mode disabled. Multi-ROI behavior restored.",
                4000,
            )

        self._on_pg_roi_changed()

        if vb is not None:
            try:
                if saved_view_rect is not None:
                    vb.setRange(saved_view_rect, padding=0)
            finally:
                try:
                    vb.enableAutoRange()
                except Exception:
                    pass

    @Slot(float)
    def on_stdp_distance_changed(self, value: float):
        self.stdp_distance_px = float(value)
        if self._is_stdp_active():
            self._sync_stdp_roi2_from_roi1()
            self._on_pg_roi_changed()

    @Slot(str)
    def on_stdp_direction_changed(self, value: str):
        self._stdp_direction = value or "Right"
        if self._is_stdp_active():
            self._sync_stdp_roi2_from_roi1()
            self._on_pg_roi_changed()

    def get_stdp_roi_rects_display(self):
        if not self._is_stdp_active():
            return []
        rects = []
        for roi in (self.stdp_roi1, self.stdp_roi2):
            rect = self._get_roi_rect_display(roi)
            if rect is not None:
                rects.append(rect)
        return rects

    def get_stdp_roi_rects_original(self):
        rects = []
        for rect in self.get_stdp_roi_rects_display():
            orig = self._display_rect_to_original_rect(rect)
            if orig is not None:
                rects.append(orig)
        return rects

    def _add_roi(self, x, y, w, h, role="generic", pen=None):
        """Add one RectROI and make it active."""
        roi = pg.RectROI([float(x), float(y)], [max(1.0, float(w)), max(1.0, float(h))], pen=pen or self._roi_pen)
        roi.setZValue(10)
        vb = self._get_viewbox()
        if vb is not None:
            vb.addItem(roi)
        self.rois.append(roi)
        self.roi_params[roi] = {"role": role}
        try:
            roi.sigRegionChanged.connect(lambda *args, roi=roi: self._on_roi_region_changed(roi))
            roi.sigClicked.connect(lambda *args, roi=roi: self._on_roi_clicked(roi, args[-1] if args else None))
        except Exception:
            pass
        try:
            roi.sigRegionChangeStarted.connect(lambda *args, roi=roi: self._set_active_roi(roi))
        except Exception:
            pass
        self._set_active_roi(roi)
        return roi

    def _remove_roi(self, roi, select_next=True):
        if roi is None or roi not in self.rois:
            return
        old_index = self.rois.index(roi)
        vb = self._get_viewbox()
        if vb is not None:
            try:
                vb.removeItem(roi)
            except Exception:
                pass
        self.rois.remove(roi)
        self.roi_params.pop(roi, None)
        if roi is self.stdp_roi1:
            self.stdp_roi1 = None
        if roi is self.stdp_roi2:
            self.stdp_roi2 = None
        if self.active_roi is roi:
            next_roi = None
            if select_next and self.rois:
                next_roi = self.rois[min(old_index, len(self.rois) - 1)]
            self.active_roi = None
            self._set_active_roi(next_roi)
        else:
            self._on_pg_roi_changed()

    def _clear_rois(self):
        """Remove every ROI and reset active ROI state."""
        for roi in list(self.rois):
            self._remove_roi(roi, select_next=False)
        self.rois.clear()
        self.roi_params.clear()
        self.active_roi = None
        self.stdp_roi1 = None
        self.stdp_roi2 = None
        self.stdp_mask_1 = None
        self.stdp_mask_2 = None
        self._roi_drag_active = False
        self._roi_drag_origin = None
        self._roi_drag_item = None
        self._on_pg_roi_changed()

    def _set_active_roi(self, roi):
        """Track the single active ROI and update its visual outline."""
        if self._is_stdp_active() and roi is self.stdp_roi2 and self.stdp_roi1 in self.rois:
            roi = self.stdp_roi1
        if roi is not None and roi not in self.rois:
            return
        self.active_roi = roi
        for item in self.rois:
            try:
                if self._is_stdp_active() and item is self.stdp_roi2:
                    item.setPen(self._stdp_roi2_pen)
                else:
                    item.setPen(self._active_roi_pen if item is roi else self._roi_pen)
            except Exception:
                pass
        self._on_pg_roi_changed()

    def _on_roi_clicked(self, roi, ev):
        self._set_active_roi(roi)
        try:
            ev.accept()
        except Exception:
            pass

    def _on_roi_region_changed(self, roi):
        if self._stdp_syncing:
            self._on_pg_roi_changed()
            return
        if self._is_stdp_active():
            if roi is self.stdp_roi2:
                self._sync_stdp_roi2_from_roi1()
            else:
                if self.stdp_roi1 is None or self.stdp_roi1 not in self.rois:
                    self.stdp_roi1 = roi
                self._sync_stdp_roi2_from_roi1()
        self._on_pg_roi_changed()

    def _get_roi_rect_display(self, roi):
        """Return one ROI as (x, y, w, h) in displayed image pixel coordinates."""
        if roi is None:
            return None
        try:
            pos = roi.pos()
            size = roi.size()
            return (float(pos.x()), float(pos.y()), float(size.x()), float(size.y()))
        except Exception:
            return None

    def _get_current_roi_rect_display(self):
        """Return the active ROI rectangle, or the first ROI for legacy callers."""
        if self.active_roi is not None:
            return self._get_roi_rect_display(self.active_roi)
        rects = self._get_all_roi_rects_display()
        return rects[0] if rects else None

    def _get_all_roi_rects_display(self):
        """Return all ROI rectangles in displayed image pixel coordinates."""
        rects = []
        for roi in self.rois:
            rect = self._get_roi_rect_display(roi)
            if rect is not None:
                rects.append(rect)
        return rects

    def _display_rect_bounds(self, rect):
        """Clip a display-space ROI rectangle to the displayed image bounds."""
        if rect is None or self._display_shape is None:
            return None
        xd0, yd0, w, h = rect
        if w <= 0 or h <= 0:
            return None
        H_disp, W_disp = self._display_shape
        x0 = int(max(0, min(W_disp, xd0)))
        y0 = int(max(0, min(H_disp, yd0)))
        x1 = int(max(0, min(W_disp, xd0 + w)))
        y1 = int(max(0, min(H_disp, yd0 + h)))
        if x1 <= x0 or y1 <= y0:
            return None
        return x0, y0, x1, y1

    def _display_bounds_to_original_bounds(self, bounds):
        """Convert clipped display-space bounds to original raw-frame bounds."""
        if bounds is None or self.last_raw_frame is None:
            return None
        x0, y0, x1, y1 = bounds
        H_raw, W_raw = self.last_raw_frame.shape
        if self.display_flip_x:
            xr0 = (W_raw - 1) - (x1 - 1)
            xr1 = (W_raw - 1) - x0
        else:
            xr0, xr1 = x0, x1
        xr0, xr1 = sorted((int(max(0, min(W_raw, xr0))), int(max(0, min(W_raw, xr1)))))
        yr0, yr1 = sorted((int(max(0, min(H_raw, y0))), int(max(0, min(H_raw, y1)))))
        if xr1 <= xr0 or yr1 <= yr0:
            return None
        return xr0, yr0, xr1, yr1

    def _get_all_roi_rects_original(self):
        """Return all ROI rectangles in original/raw camera frame pixel coordinates."""
        rects = []
        for rect in self._get_all_roi_rects_display():
            orig = self._display_rect_to_original_rect(rect)
            if orig is not None:
                rects.append(orig)
        return rects

    def _on_pg_roi_changed(self):
        rects = self._get_all_roi_rects_display()
        if not rects:
            self.current_rect_label.setText("ROIs: -")
            return
        if self._is_stdp_active() and self.stdp_roi1 is not None:
            roi1 = self._get_roi_rect_display(self.stdp_roi1)
            roi2 = self._get_roi_rect_display(self.stdp_roi2)
            if roi1 is not None and roi2 is not None:
                x1, y1, w1, h1 = roi1
                x2, y2, w2, h2 = roi2
                self.current_rect_label.setText(
                    "STDP\n"
                    f"ROI 1: x={int(x1)}, y={int(y1)}, "
                    f"w={int(w1)}, h={int(h1)}\n"
                    f"ROI 2: x={int(x2)}, y={int(y2)}, "
                    f"w={int(w2)}, h={int(h2)}\n"
                    f"Distance: {int(round(self.stdp_distance_px))} px\n"
                    f"Direction: {self._stdp_direction}"
                )
                return
        active_idx = self._active_roi_index()
        if self.active_roi is not None:
            active = self._get_roi_rect_display(self.active_roi)
            if active is not None:
                x, y, w, h = active
                self.current_rect_label.setText(
                    f"ROIs: {len(rects)} | Active #{active_idx + 1}: x={int(x)}, y={int(y)}, w={int(w)}, h={int(h)}"
                )
            else:
                self.current_rect_label.setText(f"ROIs: {len(rects)} | Active: -")
        else:
            self.current_rect_label.setText(f"ROIs: {len(rects)} | Active: -")

    def _event_button_down_scene_pos(self, ev):
        try:
            return ev.buttonDownScenePos(Qt.LeftButton)
        except TypeError:
            return ev.buttonDownScenePos()
        except Exception:
            return ev.scenePos()

    def _scene_pos_is_over_roi(self, scene_pos):
        vb = self._get_viewbox()
        if vb is None:
            return False
        try:
            p = vb.mapSceneToView(scene_pos)
        except Exception:
            return False
        x, y = p.x(), p.y()
        for roi in self.rois:
            rect = self._get_roi_rect_display(roi)
            if rect is None:
                continue
            rx, ry, rw, rh = rect
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return True
        return False

    def _call_original_viewbox_drag(self, ev, axis=None):
        handler = self._viewbox_mouse_drag_event
        if handler is None:
            try:
                ev.ignore()
            except Exception:
                pass
            return
        try:
            return handler(ev, axis=axis)
        except TypeError:
            return handler(ev)

    def _resize_drag_roi(self, scene_pos):
        if self._roi_drag_item is None or self._roi_drag_origin is None:
            return
        vb = self._get_viewbox()
        if vb is None:
            return
        p0 = vb.mapSceneToView(self._roi_drag_origin)
        p1 = vb.mapSceneToView(scene_pos)
        x0, y0 = p0.x(), p0.y()
        x1, y1 = p1.x(), p1.y()
        x = min(x0, x1)
        y = min(y0, y1)
        w = max(1, abs(x1 - x0))
        h = max(1, abs(y1 - y0))
        self._roi_drag_item.setPos((x, y))
        self._roi_drag_item.setSize((w, h))
        self._on_pg_roi_changed()

    def _on_viewbox_mouse_drag_event(self, ev, axis=None):
        try:
            if ev.button() != Qt.LeftButton:
                return self._call_original_viewbox_drag(ev, axis)

            if ev.isStart():
                origin = self._event_button_down_scene_pos(ev)
                if self._scene_pos_is_over_roi(origin):
                    return self._call_original_viewbox_drag(ev, axis)
                self._roi_drag_active = True
                self._roi_drag_origin = origin
                if self._is_stdp_active():
                    self._clear_rois()
                p0 = self._get_viewbox().mapSceneToView(origin)
                role = "stdp_roi1" if self._is_stdp_active() else "generic"
                self._roi_drag_item = self._add_roi(p0.x(), p0.y(), 1, 1, role=role)
                if self._is_stdp_active():
                    self.stdp_roi1 = self._roi_drag_item

            if self._roi_drag_active:
                self._resize_drag_roi(ev.scenePos())
                ev.accept()
                if ev.isFinish():
                    self._roi_drag_active = False
                    self._roi_drag_origin = None
                    self._roi_drag_item = None
                    if self._is_stdp_active():
                        self._ensure_stdp_pair(self.stdp_roi1)
                return
        except Exception:
            return self._call_original_viewbox_drag(ev, axis)

        return self._call_original_viewbox_drag(ev, axis)

    @Slot()
    def on_delete_roi(self):
        if self.active_roi is None:
            return
        if self._is_stdp_active() and self._is_stdp_roi(self.active_roi):
            self._clear_rois()
            self.status_lbl.setText("STDP ROI pair deleted.")
            return
        self._remove_roi(self.active_roi)
        self.status_lbl.setText("Active ROI deleted.")

    @Slot()
    def on_clear_roi(self):
        self._clear_rois()
        self.status_lbl.setText("All ROIs cleared.")

    def _compute_mask_from_display_rects(self, rects, quiet=False):
        if self.last_raw_frame is None:
            if not quiet:
                QMessageBox.warning(self, "ROI", "Snap an image first.")
            return None
        if self._display_shape is None:
            if not quiet:
                QMessageBox.warning(self, "ROI", "No displayed image available.")
            return None
        if not rects:
            if not quiet:
                QMessageBox.warning(self, "ROI", "Create/adjust at least one rectangular ROI first.")
            return None

        H_disp, W_disp = self._display_shape
        used_roi = False
        if getattr(self, "affine_expects_display_coords", True):
            cam_mask = np.zeros((H_disp, W_disp), dtype=np.uint8)
            for rect in rects:
                bounds = self._display_rect_bounds(rect)
                if bounds is None:
                    continue
                x0, y0, x1, y1 = bounds
                cam_mask[y0:y1, x0:x1] = 255
                used_roi = True
        else:
            H_raw, W_raw = self.last_raw_frame.shape
            cam_mask = np.zeros((H_raw, W_raw), dtype=np.uint8)
            for rect in rects:
                bounds = self._display_rect_bounds(rect)
                raw_bounds = self._display_bounds_to_original_bounds(bounds)
                if raw_bounds is None:
                    continue
                xr0, yr0, xr1, yr1 = raw_bounds
                cam_mask[yr0:yr1, xr0:xr1] = 255
                used_roi = True

        if not used_roi:
            if not quiet:
                QMessageBox.warning(self, "ROI", "All ROIs are outside the image or have zero area.")
            return None

        if self.affine is not None and self.core is not None:
            try:
                slm_w, slm_h = self.slm_w, self.slm_h
                cam_mask = np.rot90(cam_mask, -1)
                slm_img = cv2.warpAffine(cam_mask, self.affine, (slm_w, slm_h))
                return np.ascontiguousarray(np.clip(slm_img, 0, 255).astype(np.uint8))
            except Exception as e:
                if not quiet:
                    QMessageBox.critical(self, "Affine Warp Error", f"Warp failed: {e}")
                return None
        else:
            if self.core is None:
                if not quiet:
                    QMessageBox.warning(self, "Warning", "Core not initialized; cannot query DMD size.")
                return None
            slm_w, slm_h = self.slm_w, self.slm_h
            if not quiet:
                QMessageBox.information(self, "No Affine", "Affine not loaded. ROI was resized to SLM dimensions (approximate).")
            return cv2.resize(cam_mask, (slm_w, slm_h), interpolation=cv2.INTER_NEAREST)

    def get_stdp_dmd_masks(self):
        if not self._is_stdp_active():
            return (None, None)
        rects = self.get_stdp_roi_rects_display()
        if len(rects) < 2:
            return (None, None)
        mask1 = self._compute_mask_from_display_rects([rects[0]], quiet=True)
        if mask1 is None:
            return (None, None)
        mask2 = self._compute_mask_from_display_rects([rects[1]], quiet=True)
        if mask2 is None:
            return (None, None)
        self.stdp_mask_1 = mask1
        self.stdp_mask_2 = mask2
        return (mask1, mask2)

    def _compute_mask_from_current_roi(self):
        return self._compute_mask_from_display_rects(self._get_all_roi_rects_display())

    @Slot()
    def on_make_mask(self):
        if self.last_raw_frame is None:
            QMessageBox.warning(self,"ROI","Snap an image first.")
            return
        slm_mask = self._compute_mask_from_current_roi()
        if slm_mask is None:
            return
        self.slm_mask = slm_mask
        if self._is_stdp_active():
            self.stdp_mask_1, self.stdp_mask_2 = self.get_stdp_dmd_masks()
        else:
            self.stdp_mask_1 = None
            self.stdp_mask_2 = None
        saved_path = self._persist_roi_mask()
        if saved_path:
            self.status_lbl.setText(
                f"Mask ready ({self.slm_mask.shape[1]}x{self.slm_mask.shape[0]}). "
                f"Saved: {os.path.basename(saved_path)}"
            )
        else:
            self.status_lbl.setText(
                f"Mask ready ({self.slm_mask.shape[1]}x{self.slm_mask.shape[0]}). "
                "Click 'Apply Mask to DMD' to show it."
            )

        if self.host_gui is not None:
            try:
                setattr(self.host_gui, "roi_dmd_mask", self.slm_mask)
                if saved_path:
                    setattr(self.host_gui, "roi_dmd_mask_path", saved_path)
            except Exception:
                pass

    @Slot()
    def on_apply_mask(self):
        if self.slm_mask is None:
            QMessageBox.warning(self,"DMD","No mask prepared. Click 'Make DMD Mask from ROIs' first."); return
        if self.core is None:
            QMessageBox.warning(self,"DMD","Core not initialized."); return
        try:
            self.core.set_slm_image(self.slm_name,self.slm_mask)
            time.sleep(0.05)
            self.core.display_slm_image(self.slm_name)
            self.statusBar().showMessage("Mask applied to DMD.",1000)
        except Exception as e:
            QMessageBox.critical(self,"DMD Error",f"Failed to send mask to DMD: {e}")

    @Slot()
    def on_clear_dmd(self):
        if self.core is None: return
        try:
            blank=np.zeros((self.slm_h,self.slm_w),dtype=np.uint8)
            self.core.set_slm_image(self.slm_name,blank)
            time.sleep(0.05)
            self.core.display_slm_image(self.slm_name)
            self.statusBar().showMessage("DMD cleared.",2000)
        except Exception as e:
            QMessageBox.critical(self,"DMD Error",f"Failed to clear DMD: {e}")

    def _ensure_mask_and_core(self)->bool:
        if self.core is None: QMessageBox.warning(self,"Core","Core not initialized."); return False
        if self.slm_mask is None:
            if self.last_raw_frame is not None:
                maybe_mask = self._compute_mask_from_current_roi()
                if maybe_mask is not None:
                    self.slm_mask = maybe_mask
                else:
                    QMessageBox.warning(self,"Mask","No DMD mask is prepared. Create and apply it first."); return False
            else:
                QMessageBox.warning(self,"Mask","No DMD mask is prepared. Create and apply it first."); return False
        return True

    def _set_controls_enabled(self, enabled: bool):
        for w in [self.freq_hz, self.on_time_ms, self.duration_s, self.apply_mask_btn,
                  self.clear_dmd_btn, self.make_mask_btn, self.clear_roi_btn,
                  self.delete_roi_btn, self.snap_btn, self.load_affine_btn, self.load_old_affine_btn,
                  self.connect_btn, self.port_edit, self.stdp_checkbox, self.stdp_distance, self.stdp_direction]:
            w.setEnabled(enabled)

    def _start_activity(self, total_pulses:int):
        self._set_active_led(True)
        self.stim_progress.setMaximum(max(1, total_pulses))
        self.stim_progress.setValue(0)
        self._set_controls_enabled(False)
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def _finish_activity(self):
        self._set_active_led(False)
        self._set_controls_enabled(True)
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    @Slot()
    def on_manual(self):
        if not self._ensure_mask_and_core(): return
        if self.arduino_comm is None: QMessageBox.warning(self,"Arduino","Connect Arduino first."); return

        f=max(0.1,float(self.freq_hz.value()))
        period_ms=max(1,int(round(1000.0/f)))
        on_ms=int(self.on_time_ms.value())
        if on_ms>=period_ms:
            on_ms=max(1,period_ms-1)
            self.statusBar().showMessage(f"On-time clamped to {on_ms} ms (< period {period_ms} ms).", 4000)
        if self._is_stdp_active():
            # For STDP 4-field mode: [0,1],period_ms,on_time_ms,ISI_ms
            # ISI (inter-stimulus interval) is derived from stdp_distance_px
            isi_ms = int(min(1000, max(1, round(self.stdp_distance_px))))
            period_ms_stdp, on_ms_stdp, isi_ms_stdp = build_stdp_message_payload(
                period_ms,
                on_ms,
                isi_ms
            )
            #ok = self.arduino_comm.send_stdp_message(period_ms_stdp, period_ms_stdp, isi_ms_stdp)

            ok = self.arduino_comm.send_stdp_message(
                period_ms=period_ms_stdp,
                on_time_ms=period_ms_stdp,
                isi_ms=isi_ms_stdp,
                pair_count=1,
            )

            if ok:
                self.statusBar().showMessage("STDP protocol command sent.", 2000)
            else:
                QMessageBox.critical(self, "Arduino", "No ACK from Arduino (STDP pulse).")
            return

        ok = self.arduino_comm.send_message([1], period_ms, on_ms)
        if ok:
            self.statusBar().showMessage("Manual pulse sent.", 2000)
        else:
            QMessageBox.critical(self, "Arduino", "No ACK from Arduino (manual pulse).")

    @Slot()
    def on_run(self):
        if not self._ensure_mask_and_core(): return
        if self.arduino_comm is None: QMessageBox.warning(self,"Arduino","Connect Arduino first."); return

        f=max(0.1,float(self.freq_hz.value()))
        T=max(0.1,float(self.duration_s.value()))
        period_ms=max(1,int(round(1000.0/f)))
        on_ms=int(self.on_time_ms.value())
        if on_ms>=period_ms:
            on_ms=max(1,period_ms-1)
            self.statusBar().showMessage(f"On-time clamped to {on_ms} ms (< period {period_ms} ms).", 4000)

        total_pulses=max(1,int(math.floor(f*T)))  # use floor to match earlier duration behavior

        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self,"Stim","A stimulation run is already active."); return

        self.worker = StimWorker(
            self.arduino_comm,
            period_ms,
            on_ms,
            total_pulses,
            self,
            use_stdp=self._is_stdp_active(),
            stdp_distance_px=self.stdp_distance_px,
            duration_s=T,
        )
        self.worker.progress.connect(self._on_worker_progress); self.worker.finished.connect(self._on_worker_finished)

        self.status_lbl.setText(f"Running: {total_pulses} pulses @ {f:.2f} Hz (period {period_ms} ms, on {on_ms} ms)")
        self._start_activity(total_pulses)
        self.worker.start()

    @Slot()
    def on_stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop(); self.worker.wait(2000)
        self.status_lbl.setText("Stopped.")
        self._finish_activity()

    @Slot(int)
    def _on_worker_progress(self, sent:int):
        self.stim_progress.setValue(sent)
        self.status_lbl.setText(f"Delivered {sent} pulses...")

    @Slot(bool, str)
    def _on_worker_finished(self, ok:bool, msg:str):
        self._finish_activity()
        self.status_lbl.setText(f"Finished: {msg}")
        if not ok: QMessageBox.critical(self,"Stim",msg)

    def _set_active_led(self, active: bool):
            size = 14
            if getattr(self, "active_led", None) is not None:
                self.active_led.setFixedSize(size, size)
                color = "#D11" if active else "#666"
                self.active_led.setStyleSheet(f"background-color: {color}; border-radius: {size//2}px; border: 1px solid #333;")
            if getattr(self, "active_lbl", None) is not None:
                self.active_lbl.setStyleSheet("color: #D11;" if active else "color: #666;")
    
    def closeEvent(self, event):
        """Ensure the DMD/SLM is left in a safe state and release hardware if we own the Core."""
        # Stop any running stimulation thread cleanly
        try:
            if getattr(self, "worker", None) and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait(1500)
        except Exception:
            pass

        # Blank the SLM/DMD (best effort)
        try:
            if self.core is not None and getattr(self, "slm_name", None):
                blank = np.zeros((self.slm_h, self.slm_w), dtype=np.uint8)
                self.core.set_slm_image(self.slm_name, blank)
                # wait 4 ms for the SLM to settle
                time.sleep(0.04)
                self.core.display_slm_image(self.slm_name)
        except Exception:
            pass

        # Release devices only if this window created a standalone Core()
        try:
            if getattr(self, "_owns_core", False) and self.core is not None:
                try:
                    self.core.unloadAllDevices()
                except Exception:
                    pass
                self.core = None
                self.camera = None
        finally:
            # If we attached via ZMQ server, do not unload devices; just close bridge handle if supported
            try:
                if getattr(self, "bridge", None) is not None:
                    try:
                        self.bridge.close()
                    except Exception:
                        pass
            except Exception:
                pass

        super().closeEvent(event)

if __name__=="__main__":
    app=QApplication(sys.argv); win=SimpleStimWindow(); win.show(); sys.exit(app.exec())
