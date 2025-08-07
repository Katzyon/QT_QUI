import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QHBoxLayout, QStatusBar
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

    def paintEvent(self, event):
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

class ClickCollector(QWidget):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.arduino = gui.arduino
        self.arduino_comm = gui.arduino_comm
        self.light_click_ms_time = gui.light_click_ms_time

        self.pixel_to_stage_affine = gui.pixel_to_stage_affine

        base_image = self.camImage_to_QImage(gui.frame)
        self.image_height, self.image_width = gui.frame.shape
        self.current_point = (0, 0)

        self.background_image = QPixmap(base_image)
        self.panel = ImageLabel(self)
        self.panel.setPixmap(self.background_image)
        self.panel.resize(self.background_image.size())

        self.status_bar = QStatusBar(self)
        self.status_bar.setFixedHeight(20)

        layout = QHBoxLayout(self)
        layout.addWidget(self.panel)
        layout.addWidget(self.status_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Click Collector')
        self.move(50, 50)
        self.setMouseTracking(True)

    def pixel_to_micron(self, x, y):
        if hasattr(self, 'pixel_to_stage_affine') and self.pixel_to_stage_affine is not None:
            pt = np.array([x, y, 1], dtype=np.float32)
            result = self.pixel_to_stage_affine @ pt
            return result[0], result[1]
        return None, None

    def mousePressEvent(self, event):
        x_pixel = event.x()
        y_pixel = event.y()

        if not (0 <= x_pixel < self.image_width and 0 <= y_pixel < self.image_height):
            print(f"Click ignored: outside image bounds at ({x_pixel}, {y_pixel})")
            return

        core = self.gui.core
        dmd_name = core.get_slm_device()
        slm_width = core.get_slm_width(dmd_name)
        slm_height = core.get_slm_height(dmd_name)

        self.gui.affine_transform = self.gui.affine_trans_old
        self.panel.set_current_point((x_pixel, y_pixel))

        x_micron, y_micron = self.pixel_to_micron(x_pixel, y_pixel)
        if x_micron is not None:
            print(f"Clicked at pixel: ({x_pixel:.2f}, {y_pixel:.2f}) → Micron: ({x_micron:.2f}, {y_micron:.2f})")
        else:
            print(f"Clicked at pixel: ({x_pixel:.2f}, {y_pixel:.2f}) → Micron: [Transform not available]")

        new_image = self.mouse_click_image(y_pixel, x_pixel)
        transformed_img = cv2.warpAffine(new_image, self.gui.affine_transform, (slm_width, slm_height))

        core.set_slm_image(dmd_name, transformed_img)
        time.sleep(0.01)
        core.display_slm_image(dmd_name)
        self.arduino_comm.send_message([1], 100, self.light_click_ms_time)

        core.snap_image()
        tagged_image = core.get_tagged_image()
        pixels = np.reshape(tagged_image.pix,
                            newshape=[tagged_image.tags['Height'], tagged_image.tags['Width']])

        time.sleep(0.1)
        core.set_slm_image(dmd_name, np.zeros((slm_width, slm_height), dtype=np.uint8))
        core.display_slm_image(dmd_name)

        di.display_image(pixels, "cam_image")

    def mouse_click_image(self, xdata, ydata):
        camera_width = self.gui.core.get_image_width()
        camera_height = self.gui.core.get_image_height()
        new_image = np.zeros((camera_width, camera_height), dtype=np.uint8)

        half_point_size = self.gui.light_click_pixels
        print("half_point_size: ", half_point_size)

        new_image[int(xdata) - half_point_size:int(xdata) + half_point_size,
                  int(ydata) - half_point_size:int(ydata) + half_point_size] = 255
        print("Clicked at: ", xdata, ydata)
        return new_image

    def camImage_to_QImage(self, frame):
        height, width = frame.shape
        bytes_per_line = width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        return q_img
