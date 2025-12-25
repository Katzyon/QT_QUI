"""
Simple DMD Stim GUI — Help

What this app does
------------------
A lightweight PySide6 GUI for: 
1) snapping a camera image of the neuronal culture (via Micro-Manager / PycroManager),
2) selecting a rectangular ROI on the image that becomes a DMD/SLM stimulation mask,
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
4) Click “Snap Image”. Draw an ROI (click-drag; release to finalize). “Clear ROI” to reset.
5) Click “Make DMD Mask from ROI”, then “Apply Mask to DMD”.
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
import numpy as np
import cv2

from PySide6.QtCore import Qt, QRect, QSize, QPoint, QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
    QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox, QLineEdit, QSpinBox,
    QDoubleSpinBox, QMessageBox, QStatusBar, QRubberBand, QProgressBar
)

from pycromanager import Core
import Camera
from arduino_comm import ArduinoComm

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

    def __init__(self, arduino_comm: ArduinoComm, period_ms: int, on_time_ms: int, total_pulses: int, parent=None):
        super().__init__(parent)
        self.arduino = arduino_comm
        self.period_ms = int(period_ms)
        self.on_time_ms = int(on_time_ms)
        self.total = max(0, int(total_pulses))
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple DMD Stim (PySide6)")
        self.resize(1320, 800)
        self.core = None
        self.camera=None
        self.last_raw_frame=None
        self.display_flip_x = True
        self.affine=None
        self.slm_name=None
        self.slm_w=None
        self.slm_h=None
        self.slm_mask=None
        self.arduino_comm=None
        self.worker=None
        self._build_ui()
        self._connect_signals()
        self._init_core_and_camera()
        self._auto_connect_arduino(port="COM13")
        self.load_old_affine()

    def _build_ui(self):
        central = QWidget(self); self.setCentralWidget(central)
        self.image_label = ROIImageLabel()
        image_box = QGroupBox("Camera image / ROI")
        v=QVBoxLayout(image_box); v.addWidget(self.image_label, alignment=Qt.AlignTop|Qt.AlignLeft)

        ctl_box = QGroupBox("Controls"); grid=QGridLayout(ctl_box)

        # Row 0: Arduino
        self.port_edit=QLineEdit("COM13"); self.connect_btn=QPushButton("Connect Arduino")
        grid.addWidget(QLabel("Arduino Port:"),0,0); grid.addWidget(self.port_edit,0,1); grid.addWidget(self.connect_btn,0,2)

        # Row 1: Capture & affine
        self.snap_btn=QPushButton("Snap Image"); self.load_affine_btn=QPushButton("Load Affine (2x3 .npy)"); self.load_old_affine_btn=QPushButton("Load Old Affine")
        grid.addWidget(self.snap_btn,1,0); grid.addWidget(self.load_affine_btn,1,1); grid.addWidget(self.load_old_affine_btn,1,2)

        # Row 2: ROI
        self.current_rect_label=QLabel("ROI: -"); self.make_mask_btn=QPushButton("Make DMD Mask from ROI"); self.clear_roi_btn=QPushButton("Clear ROI")
        grid.addWidget(self.current_rect_label,2,0,1,2); grid.addWidget(self.make_mask_btn,2,2); grid.addWidget(self.clear_roi_btn,2,3)

        # Row 3: Stim params
        self.freq_hz=QDoubleSpinBox(); self.freq_hz.setRange(0.1,1000.0); self.freq_hz.setDecimals(2); self.freq_hz.setValue(5.0)
        self.on_time_ms=QSpinBox(); self.on_time_ms.setRange(1,1000); self.on_time_ms.setValue(10)
        self.duration_s=QDoubleSpinBox(); self.duration_s.setRange(0.1,3600.0); self.duration_s.setDecimals(1); self.duration_s.setValue(5.0)
        grid.addWidget(QLabel("Freq (Hz):"),3,0); grid.addWidget(self.freq_hz,3,1); grid.addWidget(QLabel("On-time (ms):"),3,2); grid.addWidget(self.on_time_ms,3,3)
        grid.addWidget(QLabel("Duration (s):"),3,4); grid.addWidget(self.duration_s,3,5)

        # Row 4: DMD
        self.apply_mask_btn=QPushButton("Apply Mask to DMD"); self.clear_dmd_btn=QPushButton("Clear DMD")
        grid.addWidget(self.apply_mask_btn,4,0,1,2); grid.addWidget(self.clear_dmd_btn,4,2,1,2)

        # Row 5: Run / Manual
        self.manual_btn=QPushButton("Manual Stim (1 pulse)"); self.run_btn=QPushButton("Run Stim Train"); self.stop_btn=QPushButton("Stop")
        grid.addWidget(self.manual_btn,5,0,1,2); grid.addWidget(self.run_btn,5,2,1,2); grid.addWidget(self.stop_btn,5,4,1,2)

        # Row 6: Activity indicator + progress
        self.active_led = QLabel(); self._set_active_led(False)
        self.active_lbl = QLabel("Stim ACTIVE")
        self.stim_progress = QProgressBar(); self.stim_progress.setMinimum(0); self.stim_progress.setMaximum(1); self.stim_progress.setValue(0)
        grid.addWidget(self.active_led, 6, 0); grid.addWidget(self.active_lbl, 6, 1); grid.addWidget(self.stim_progress, 6, 2, 1, 4)

        # Row 7: Status
        self.status_lbl=QLabel(""); grid.addWidget(self.status_lbl,7,0,1,6)

        main=QHBoxLayout(central); main.addWidget(image_box,2); main.addWidget(ctl_box,3)
        self.setStatusBar(QStatusBar(self)); exit_act=QAction("&Exit",self); exit_act.triggered.connect(self.close); self.menuBar().addMenu("&File").addAction(exit_act)

    def _set_active_led(self, active: bool):
            size = 14
            if getattr(self, "active_led", None) is not None:
                self.active_led.setFixedSize(size, size)
                color = "#D11" if active else "#666"
                self.active_led.setStyleSheet(f"background-color: {color}; border-radius: {size//2}px; border: 1px solid #333;")
            if getattr(self, "active_lbl", None) is not None:
                self.active_lbl.setStyleSheet("color: #D11;" if active else "color: #666;")
    def _connect_signals(self):
            self.snap_btn.clicked.connect(self.on_snap)
            self.load_affine_btn.clicked.connect(self.on_load_affine_generic)
            self.load_old_affine_btn.clicked.connect(self.load_old_affine)
            self.image_label.rectChanged.connect(self.on_rect_changed)
            self.make_mask_btn.clicked.connect(self.on_make_mask)
            self.clear_roi_btn.clicked.connect(self.on_clear_roi)
            self.apply_mask_btn.clicked.connect(self.on_apply_mask)
            self.clear_dmd_btn.clicked.connect(self.on_clear_dmd)
            self.connect_btn.clicked.connect(self.on_connect_arduino)
            self.manual_btn.clicked.connect(self.on_manual)
            self.run_btn.clicked.connect(self.on_run)
            self.stop_btn.clicked.connect(self.on_stop)

    def _init_core_and_camera(self):
        try:
            self.core = Core(convert_camel_case=True)
            self.camera = Camera.getImage(self.core)
            self.slm_name = self.core.get_slm_device()
            self.slm_w = self.core.get_slm_width(self.slm_name); self.slm_h = self.core.get_slm_height(self.slm_name)
            self.statusBar().showMessage(f"Connected: SLM='{self.slm_name}' ({self.slm_w}x{self.slm_h})", 5000)
        except Exception as e:
            QMessageBox.critical(self,"Core Error","Failed to connect to Micro-Manager via Pycromanager.\n\n"+f"Details: {e}")
            self.core=None; self.camera=None

    def _auto_connect_arduino(self, port="COM13"):
        try:
            self.arduino_comm = ArduinoComm.connect(port=port, baudrate=19200, timeout=2)
            if self.arduino_comm is not None:
                self.statusBar().showMessage(f"Arduino auto-connected on {port}", 4000)
        except Exception: pass

    @Slot()
    def on_connect_arduino(self):
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
            QMessageBox.warning(self,"Camera","Core/Camera not initialized."); return
        try:
            raw=self.camera.snap_image(self.core); self.last_raw_frame=raw.copy()
            frame_disp=np.fliplr(self.last_raw_frame.copy()); self.image_label.set_numpy_image(frame_disp)
            self.statusBar().showMessage("Image snapped (displayed as fliplr).",2000)
        except Exception as e:
            QMessageBox.critical(self,"Snap Error",f"Failed to snap image: {e}")

    @Slot(QRect)
    def on_rect_changed(self, rect: QRect):
        if rect.isValid() and rect.width()>0 and rect.height()>0:
            self.current_rect_label.setText(f"ROI: x={rect.x()}, y={rect.y()}, w={rect.width()}, h={rect.height()}")
        else:
            self.current_rect_label.setText("ROI: -")

    @Slot()
    def on_clear_roi(self):
        self.image_label.clear_roi(); self.status_lbl.setText("ROI cleared.")

    def _compute_mask_from_current_roi(self):
        rect=self.image_label.current_rect()
        if rect.width()<=0 or rect.height()<=0:
            QMessageBox.warning(self,"ROI","Draw a rectangular ROI on the image first."); return None
        H,W=self.last_raw_frame.shape
        xd0,yd0=rect.x(),rect.y(); xd1,yd1=xd0+rect.width(),yd0+rect.height()
        if self.display_flip_x:
            xr0=max(0,min(W,W-xd1)); xr1=max(0,min(W,W-xd0))
        else:
            xr0=max(0,min(W,xd0)); xr1=max(0,min(W,xd1))
        yr0=max(0,min(H,yd0)); yr1=max(0,min(H,yd1))
        x0,x1=sorted((xr0,xr1)); y0,y1=sorted((yr0,yr1))
        cam_mask=np.zeros((H,W),dtype=np.uint8)
        if x1>x0 and y1>y0: cam_mask[int(y0):int(y1), int(x0):int(x1)]=255
        if self.affine is not None and self.core is not None:
            try:
                slm_w,slm_h=self.slm_w,self.slm_h
                slm_img=cv2.warpAffine(cam_mask,self.affine,(slm_w,slm_h))
                return np.ascontiguousarray(np.clip(slm_img,0,255).astype(np.uint8))
            except Exception as e:
                QMessageBox.critical(self,"Affine Warp Error",f"Warp failed: {e}"); return None
        else:
            if self.core is None:
                QMessageBox.warning(self,"Warning","Core not initialized; cannot query DMD size."); return None
            slm_w,slm_h=self.slm_w,self.slm_h
            QMessageBox.information(self,"No Affine","Affine not loaded. ROI was resized to SLM dimensions (approximate).")
            return cv2.resize(cam_mask,(slm_w,slm_h),interpolation=cv2.INTER_NEAREST)

    @Slot()
    def on_make_mask(self):
        if self.last_raw_frame is None:
            QMessageBox.warning(self,"ROI","Snap an image first."); return
        slm_mask = self._compute_mask_from_current_roi()
        if slm_mask is None: return
        self.slm_mask = slm_mask
        self.status_lbl.setText(f"Mask ready ({self.slm_mask.shape[1]}x{self.slm_mask.shape[0]}). Click 'Apply Mask to DMD' to show it.")

    @Slot()
    def on_apply_mask(self):
        if self.slm_mask is None:
            QMessageBox.warning(self,"DMD","No mask prepared. Click 'Make DMD Mask from ROI' first."); return
        if self.core is None:
            QMessageBox.warning(self,"DMD","Core not initialized."); return
        try:
            self.core.set_slm_image(self.slm_name,self.slm_mask); self.core.display_slm_image(self.slm_name)
            self.statusBar().showMessage("Mask applied to DMD.",2000)
        except Exception as e:
            QMessageBox.critical(self,"DMD Error",f"Failed to send mask to DMD: {e}")

    @Slot()
    def on_clear_dmd(self):
        if self.core is None: return
        try:
            blank=np.zeros((self.slm_h,self.slm_w),dtype=np.uint8)
            self.core.set_slm_image(self.slm_name,blank); self.core.display_slm_image(self.slm_name)
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
                  self.snap_btn, self.load_affine_btn, self.load_old_affine_btn,
                  self.connect_btn, self.port_edit]:
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
        try:
            self.core.set_slm_image(self.slm_name,self.slm_mask); self.core.display_slm_image(self.slm_name)
        except Exception as e:
            QMessageBox.critical(self,"DMD Error",f"Failed to display mask: {e}"); return
        f=max(0.1,float(self.freq_hz.value()))
        period_ms=max(1,int(round(1000.0/f)))
        on_ms=int(self.on_time_ms.value())
        if on_ms>=period_ms:
            on_ms=max(1,period_ms-1)
            self.statusBar().showMessage(f"On-time clamped to {on_ms} ms (< period {period_ms} ms).", 4000)
        ok=self.arduino_comm.send_message([1],period_ms,on_ms)
        if ok: self.statusBar().showMessage("Manual pulse sent.",2000)
        else: QMessageBox.critical(self,"Arduino","No ACK from Arduino (manual pulse).")

    @Slot()
    def on_run(self):
        if not self._ensure_mask_and_core(): return
        if self.arduino_comm is None: QMessageBox.warning(self,"Arduino","Connect Arduino first."); return
        try:
            self.core.set_slm_image(self.slm_name,self.slm_mask); self.core.display_slm_image(self.slm_name)
        except Exception as e:
            QMessageBox.critical(self,"DMD Error",f"Failed to display mask: {e}"); return

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

        self.worker=StimWorker(self.arduino_comm,period_ms,on_ms,total_pulses,self)
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
        try:
            if self.worker and self.worker.isRunning():
                self.worker.stop(); self.worker.wait(1500)
        except Exception: pass
        try:
            if self.core is not None:
                blank=np.zeros((self.slm_h,self.slm_w),dtype=np.uint8)
                self.core.set_slm_image(self.slm_name,blank); self.core.display_slm_image(self.slm_name)
        except Exception: pass
        super().closeEvent(event)

if __name__=="__main__":
    app=QApplication(sys.argv); win=SimpleStimWindow(); win.show(); sys.exit(app.exec())
