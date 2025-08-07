import sys
import cv2
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QTimer, Qt


class ImagePanel(QLabel):
    def __init__(self):
        super().__init__()
        self.setScaledContents(True)
        self.setAlignment(Qt.AlignCenter)
        self.current_point = None

    def set_image(self, frame):
        height, width = frame.shape
        q_img = QImage(frame.data, width, height, width, QImage.Format_Grayscale8)
        self.setPixmap(QPixmap(q_img))

    def mousePressEvent(self, event):
        if self.parent().collecting:
            x = event.x()
            y = event.y()
            self.parent().record_click(x, y)


class AffineGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Affine Calibration GUI")
        self.camera = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(100)

        self.panel = ImagePanel()
        self.collecting = False
        self.pixel_points = []

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.panel)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Calibration")
        self.start_btn.clicked.connect(self.start_collection)
        btn_layout.addWidget(self.start_btn)

        self.quit_btn = QPushButton("Quit")
        self.quit_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.quit_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def update_frame(self):
        ret, frame = self.camera.read()
        if ret:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self.panel.set_image(gray)

    def start_collection(self):
        self.pixel_points = []
        self.collecting = True
        QMessageBox.information(self, "Start", "Click on 3 points in the image")

    def record_click(self, x, y):
        self.pixel_points.append([x, y])
        QMessageBox.information(self, "Point Recorded", f"Point {len(self.pixel_points)}: ({x}, {y})")
        if len(self.pixel_points) == 3:
            self.collecting = False
            QMessageBox.information(self, "Done", f"Collected points: {self.pixel_points}")

    def closeEvent(self, event):
        self.camera.release()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = AffineGui()
    gui.resize(800, 700)
    gui.show()
    sys.exit(app.exec())
    