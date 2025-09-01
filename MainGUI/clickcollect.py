import sys
from PySide6.QtWidgets import QWidget, QLabel, QStatusBar, QVBoxLayout
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPainter, QPen, QPixmap, QImage
import numpy as np
import cv2
import time
import Display_image as di
import os

class ImageLabel(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.current_point = None
        self.parent_widget = parent
        self.setMouseTracking(True)

    def set_current_point(self, point):
        self.current_point = point
        self.update()

    def paintEvent(self, event): # override paintEvent to draw the mouse click point
        super().paintEvent(event)
        if self.current_point:
            with QPainter(self) as painter:
                pen = QPen(Qt.red, 6)
                painter.setPen(pen)
                painter.drawPoint(self.current_point[0], self.current_point[1])

    def mouseMoveEvent(self, event):
        x_pixel = event.x()
        y_pixel = event.y()
        if 0 <= x_pixel < self.width() and 0 <= y_pixel < self.height():
            x_micron, y_micron = self.parent_widget.pixel_to_micron(x_pixel, y_pixel)
            if x_micron is not None:
                msg = f"Mouse at pixel: ({x_pixel:.2f}, {y_pixel:.2f}) → Micron: ({x_micron:.2f}, {y_micron:.2f})"
            else:
                msg = f"Mouse at pixel: ({x_pixel:.2f}, {y_pixel:.2f}) → Micron: [Transform not available]"
            if hasattr(self.parent_widget, 'status_bar'):
                self.parent_widget.status_bar.showMessage(msg)

    def mousePressEvent(self, event):
        # Always deliver clicks in *label pixel* coordinates
        self.parent_widget.handle_click(event.pos().x(), event.pos().y())

class ClickCollector(QWidget):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.arduino = gui.arduino
        self.arduino_comm = gui.arduino_comm
        self.light_click_ms_time = gui.light_click_ms_time

        self.pixel_to_stage_affine = gui.pixel_to_stage_affine
        self.flip_x_display = True  # fliplr the input image for display

        self.raw_h, self.raw_w = gui.frame.shape  # RAW camera shape (H,W)
        base_image = self.camImage_to_QImage(gui.frame)
        self.image_height, self.image_width = gui.frame.shape
        self.current_point = (0, 0)

        self.background_image = QPixmap(base_image)
        self.panel = ImageLabel(self)
        self.panel.setPixmap(self.background_image)
        self.panel.resize(self.background_image.size())

        self.status_bar = QStatusBar(self)
        self.status_bar.setFixedHeight(20)

        layout = QVBoxLayout(self)
        layout.addWidget(self.panel)
        layout.addWidget(self.status_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Click Collector')
        self.move(50, 50)
        self.setMouseTracking(True)

    def pixel_to_micron(self, x_disp, y_disp): ## updated
        # if hasattr(self, 'pixel_to_stage_affine') and self.pixel_to_stage_affine is not None:
        #     pt = np.array([x, y, 1], dtype=np.float32)
        #     result = self.pixel_to_stage_affine @ pt
        #     return result[0], result[1]
        # return None, None

    
        x_raw, y_raw = self.display_to_raw(x_disp, y_disp)
        if getattr(self, "pixel_to_stage_affine", None) is None:
            return None, None
        pt = np.array([x_raw, y_raw, 1], dtype=np.float32)
        out = self.pixel_to_stage_affine @ pt
        return float(out[0]), float(out[1])
    

    def handle_click(self, x_disp, y_disp):
        # 1) Bounds check in DISPLAY/image coords
        if not (0 <= x_disp < self.disp_w and 0 <= y_disp < self.disp_h):
            print(f"Click ignored: outside image bounds at ({x_disp}, {y_disp})")
            return

        core = self.gui.core
        dmd = core.get_slm_device()
        slm_w = core.get_slm_width(dmd)
        slm_h = core.get_slm_height(dmd)

        # 2) Show display marker
        self.panel.set_current_point((x_disp, y_disp))

        # 3) Map display→RAW (X inversion only, per your updated affine)
        x_raw, y_raw = self.display_to_raw(x_disp, y_disp)

        # 4) Micron readout (uses display coords; converts inside)
        x_um, y_um = self.pixel_to_micron(x_disp, y_disp)
        print(f"Disp=({x_disp:.1f},{y_disp:.1f}) → Raw=({x_raw},{y_raw}) → Micron=({x_um},{y_um})"
              if x_um is not None else
              f"Disp=({x_disp:.1f},{y_disp:.1f}) → Raw=({x_raw},{y_raw}) → Micron=[NA]")

        # 5) Build RAW camera mask, warp to SLM
        mask = self.mouse_click_image(x_raw, y_raw)
        slm_img = cv2.warpAffine(mask, self.gui.affine_transform, (slm_w, slm_h))

        # 6) Push to SLM (non-blocking; see §2 below)
        core.set_slm_image(dmd, slm_img)
        core.display_slm_image(dmd)

        # 7) Optional capture (see §2 below before leaving as-is)
        core.snap_image()
        t = core.get_tagged_image()
        cam = np.reshape(t.pix, (t.tags['Height'], t.tags['Width']))

        # 8) Clear SLM with correct shape order (H, W)
        core.set_slm_image(dmd, np.zeros((slm_h, slm_w), dtype=np.uint8))
        core.display_slm_image(dmd)

        # 9) Display response image (this can block; see §3)
        di.display_image(cam, "cam_image")



    def mouse_click_image(self, x, y):
        cam_w = self.gui.core.get_image_width()
        cam_h = self.gui.core.get_image_height()

        img = np.zeros((cam_h, cam_w), dtype=np.uint8)  # (H, W)

        r = int(self.gui.light_click_pixels)
        x = int(round(x)); y = int(round(y))

        x0 = max(x - r, 0); x1 = min(x + r, cam_w)
        y0 = max(y - r, 0); y1 = min(y + r, cam_h)

        img[y0:y1, x0:x1] = 255   # rows(y), cols(x)
        return img
    

    def closeEvent(self, event):
        # 1) Clear any SLM/polygon pattern
        self.clear_slm()

        # 2) Clear UI overlay(s)
        # if you draw a point:
        self.panel.set_current_point(None)



    def camImage_to_QImage(self, frame):
        # Fix tilt-left: rotate 90° CW, then keep your horizontal flip convention
        img = np.rot90(frame, k=1)   
        img = np.clip(img, 0, 255).astype(np.uint8, copy=False)
        img = np.ascontiguousarray(img)

        # DISPLAY dimensions (after rotation)
        self.disp_h, self.disp_w = img.shape

        bpl = img.strides[0]
        self._qbuf = img  # keep buffer alive
        return QImage(self._qbuf.data, self.disp_w, self.disp_h, bpl, QImage.Format_Grayscale8)
        
    
    def display_to_raw(self, x_disp, y_disp):
    # inverse of np.rot90(frame, k=1)
        x_raw = self.raw_w - 1 - int(round(y_disp))   # uses RAW width
        y_raw = int(round(x_disp))

        # clamp to RAW image bounds
        x_raw = max(0, min(self.raw_w - 1, x_raw))
        y_raw = max(0, min(self.raw_h - 1, y_raw))
        return x_raw, y_raw

    def clear_slm(self):
        try:
            core = self.gui.core
            dmd_name = core.get_slm_device()
            slm_w = core.get_slm_width(dmd_name)
            slm_h = core.get_slm_height(dmd_name)
            core.set_slm_image(dmd_name, np.zeros((slm_h, slm_w), dtype=np.uint8))
            core.display_slm_image(dmd_name)
        except Exception as e:
            print(f"[ClickCollector] clear_slm failed: {e}")
