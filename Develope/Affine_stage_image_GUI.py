import sys
import traceback
import numpy as np
import cv2
import pyqtgraph as pg
from pyqtgraph import SignalProxy, ColorMap
from PySide6 import QtWidgets, QtCore, QtGui
from pycromanager import Core
import os
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'MainGUI')))
from stage_controller import StageController
import Camera


class ATCalibration(QtWidgets.QWidget):
    def __init__(self, core, camera, stage_controller, imageview):
        super().__init__()
        self.core = core
        self.camera = camera
        self.stage = stage_controller
        self.imageview = imageview
        self.pixel_points = []
        self.stage_points = []
        self.awaiting_click = False
        self.affine_matrix = None

        # UI Buttons
        self.btn_start = QtWidgets.QPushButton("Start Calibration")
        self.btn_save = QtWidgets.QPushButton("Save Transform")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_save)
        self.setLayout(layout)

        # Signals
        self.btn_start.clicked.connect(self.start_calibration)
        self.btn_save.clicked.connect(self.save_transform)

        self.proxy = SignalProxy(
            self.imageview.view.scene().sigMouseClicked,
            rateLimit=60,
            slot=self.pixel_clicked
        )

    def start_calibration(self):
        self.pixel_points.clear()
        self.stage_points.clear()
        self.awaiting_click = True
        self.snap_and_show()
        print("Calibration started. Click a feature in the image.")

    def move_to_next_position(self):
        """Move stage to a new random absolute position within ±150 µm from (0, 0)."""
        dx = random.uniform(-150, 150)
        dy = random.uniform(-150, 150)

        print(f"Moving stage to random position ({dx:.2f}, {dy:.2f}) µm from origin (0,0)")
        self.core.set_xy_position(self.stage.xy_stage, dx, dy)
        self.core.wait_for_device(self.stage.xy_stage)

        self.snap_and_show()
        self.awaiting_click = True
        print("Stage moved. Click the same feature again.")

    def snap_and_show(self):
        frame = self.camera.snap_image(self.core)

        print("frame dtype:", frame.dtype)
        print("frame min:", np.min(frame))
        print("frame max:", np.max(frame))
        print("frame shape:", frame.shape)

        self.imageview.setImage(frame, autoLevels=False)
        self.imageview.setLevels(0, 255)

        cmap = ColorMap(pos=[0.0, 1.0], color=[(0, 0, 0), (255, 255, 255)])
        lut = cmap.getLookupTable(0.0, 1.0, 256)
        self.imageview.getImageItem().setLookupTable(lut)

    def pixel_clicked(self, evt):
        if not self.awaiting_click:
            return
        scene_pos = evt[0].scenePos()
        view_pos = self.imageview.view.mapSceneToView(scene_pos)
        px, py = view_pos.x(), view_pos.y()
        sx, sy = self.stage.get_position()
        self.pixel_points.append((px, py))
        self.stage_points.append((sx, sy))
        print(f"Point {len(self.pixel_points)}: Pixel=({px:.2f},{py:.2f}) ↔ Stage=({sx:.2f},{sy:.2f})")

        self.awaiting_click = False

        if len(self.pixel_points) < 3:
            QtCore.QTimer.singleShot(100, self.move_to_next_position)
        else:
            print("Collected 3 points. Computing affine matrix and saving transform...")
            self.compute_affine()
            self.save_transform(autosave=True)


    def compute_affine(self):
        if len(self.pixel_points) < 3 or len(self.stage_points) < 3:
            print("Need at least 3 point pairs to compute affine transform.")
            return
        src = np.array(self.pixel_points[-3:], dtype=np.float32)
        dst = np.array(self.stage_points[-3:], dtype=np.float32)
        self.affine_matrix = cv2.getAffineTransform(src, dst)
        print("Affine matrix computed using last 3 points:\n", self.affine_matrix)

    def save_transform(self, autosave=False):
        if self.affine_matrix is None:
            print("No affine matrix to save.")
            return

        if autosave:
            filename = os.path.join(os.getcwd(), "affine_matrix.npy")
            np.save(filename, self.affine_matrix)
            print(f"Affine matrix auto-saved to {filename}")
        else:
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Affine Matrix", "", "NumPy files (*.npy)"
            )
            if filename:
                np.save(filename, self.affine_matrix)
                print(f"Affine matrix saved to {filename}")


    def apply_affine(self, x_pix, y_pix):
        if self.affine_matrix is None:
            return None
        pt = np.array([x_pix, y_pix, 1], dtype=np.float32)
        stage_coords = self.affine_matrix @ pt
        return stage_coords[0], stage_coords[1]


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Affine Calibration with Micro-Manager")
        self.resize(1000, 700)

        self.imageview = pg.ImageView()
        self.setCentralWidget(self.imageview)

        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)

        self.core = None
        self.camera = None
        self.xy_stage_device = None
        self.xy_stage = None

        self.stage_position = None
        self.initialize_core()

        if self.core is None:
            return

        self.at_calibrator = ATCalibration(self.core, self.camera, self.xy_stage, self.imageview)
        dock = QtWidgets.QDockWidget("Affine Calibration")
        dock.setWidget(self.at_calibrator)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        self.mouse_proxy = SignalProxy(
            self.imageview.view.scene().sigMouseMoved,
            rateLimit=60,
            slot=self.mouse_moved
        )

    def initialize_core(self):
        try:
            self.core = Core(convert_camel_case=True)
            self.camera = Camera.getImage(self.core)
            self.xy_stage_device = self.core.get_xy_stage_device()
            self.xy_stage = StageController(self.core, self.xy_stage_device, self.stage_position)

            devices = [
                self.core.get_loaded_devices().get(i)
                for i in range(self.core.get_loaded_devices().size())
            ]
            print(f"PycroManager connected. Devices: {devices}")
            self.update_stage_pos()
        except Exception as e:
            print("Failed to connect to Micro-Manager via PycroManager.")
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(
                self,
                "Core Error",
                "Failed to connect to Micro-Manager.\n"
                "Is another process (e.g. Jupyter) using Core?\n\nDetails:\n" + str(e)
            )
            self.core = None

    def update_stage_pos(self):
        if self.xy_stage and self.stage_position:
            x, y = self.xy_stage.get_position()
            self.stage_position.setText(f"{x:.2f}, {y:.2f}")

    def mouse_moved(self, evt):
        pos = QtCore.QPointF(*evt)
        if self.imageview.view.sceneBoundingRect().contains(pos):
            mp = self.imageview.view.mapSceneToView(pos)
            x, y = mp.x(), mp.y()

            message = ""

            if self.at_calibrator.affine_matrix is not None:
                result = self.at_calibrator.apply_affine(x, y)
                if result:
                    sx, sy = result
                    message += f"Stage (µm): x={sx:.2f}, y={sy:.2f} | "

            message += f"Pixel: x={x:.2f}, y={y:.2f}"

            img = self.imageview.getImageItem().image
            xi, yi = int(x), int(y)
            if img is not None and 0 <= xi < img.shape[1] and 0 <= yi < img.shape[0]:
                val = img[yi, xi]
                message += f" | Intensity: {val}"

            self.status.showMessage(message)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
