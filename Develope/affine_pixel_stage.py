
import numpy as np
import cv2  # For affine transform
from PySide6 import QtWidgets, QtCore
from pyqtgraph import SignalProxy


class ATCalibration(QtWidgets.QWidget):
    """
    Affine Transformation calibration tool:
    - Collects 3 points from the image and corresponding stage coordinates
    - Calculates affine matrix to convert image pixels to stage microns
    """

    def __init__(self, core, camera, stage_controller, imageview):
        super().__init__()

        self.core = core
        self.camera = camera
        self.stage = stage_controller
        self.imageview = imageview

        # Calibration point pairs
        self.pixel_points = []  # [(x_pix, y_pix), ...]
        self.stage_points = []  # [(x_stage, y_stage), ...]

        # State
        self.awaiting_click = False
        self.affine_matrix = None

        # Buttons
        self.btn_start = QtWidgets.QPushButton("Start Calibration")
        self.btn_next = QtWidgets.QPushButton("Next Point (Move Stage)")
        self.btn_finish = QtWidgets.QPushButton("Finish Calibration")
        self.btn_save = QtWidgets.QPushButton("Save Transform")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.btn_finish)
        layout.addWidget(self.btn_save)
        self.setLayout(layout)

        # Connect buttons
        self.btn_start.clicked.connect(self.start_calibration)
        self.btn_next.clicked.connect(self.capture_and_move_stage)
        self.btn_finish.clicked.connect(self.compute_affine)
        self.btn_save.clicked.connect(self.save_transform)

        # Connect mouse click on image
        self.proxy = SignalProxy(
            self.imageview.view.scene().sigMouseClicked,
            rateLimit=60,
            slot=self.pixel_clicked
        )

    def start_calibration(self):
        """Begin calibration: clear data, snap first image, wait for first click."""
        self.pixel_points.clear()
        self.stage_points.clear()
        self.awaiting_click = True
        self.snap_and_show()
        print("Calibration started. Click a feature in the image.")

    def capture_and_move_stage(self):
        """After each click, move stage by +100 µm and ask for another click."""
        self.awaiting_click = True
        x, y = self.stage.get_position()
        print(f"Moving stage from ({x:.2f}, {y:.2f}) → ({x + 100:.2f}, {y + 100:.2f})")
        self.core.set_xy_position(self.stage.xy_stage, x + 100, y + 100)
        self.core.wait_for_device(self.stage.xy_stage)
        self.snap_and_show()
        print("Stage moved. Click the same feature again.")

    def snap_and_show(self):
        """Take and display an image using the camera."""
        frame = self.camera.snap_image(self.core)
        self.imageview.setImage(frame)

    def pixel_clicked(self, evt):
        """Handler for mouse clicks on the image view."""
        if not self.awaiting_click:
            return
        scene_pos = evt[0].scenePos()
        view_pos = self.imageview.view.mapSceneToView(scene_pos)
        px, py = view_pos.x(), view_pos.y()

        sx, sy = self.stage.get_position()

        self.pixel_points.append((px, py))
        self.stage_points.append((sx, sy))
        print(f"Point {len(self.pixel_points)} captured:")
        print(f"  Pixel: ({px:.2f}, {py:.2f})")
        print(f"  Stage: ({sx:.2f}, {sy:.2f})")

        self.awaiting_click = False

    def compute_affine(self):
        """Compute the affine transformation matrix from collected points."""
        if len(self.pixel_points) != 3 or len(self.stage_points) != 3:
            print("Need exactly 3 point pairs to compute affine transform.")
            return

        src = np.array(self.pixel_points, dtype=np.float32)
        dst = np.array(self.stage_points, dtype=np.float32)

        self.affine_matrix = cv2.getAffineTransform(src, dst)

        print("Affine matrix computed:")
        print(self.affine_matrix)

    def save_transform(self):
        """Save the computed affine matrix to a .npy file."""
        if self.affine_matrix is None:
            print("No affine matrix to save.")
            return

        file_dialog = QtWidgets.QFileDialog(self)
        filename, _ = file_dialog.getSaveFileName(
            self, "Save Affine Matrix", "", "NumPy files (*.npy)"
        )
        if filename:
            np.save(filename, self.affine_matrix)
            print(f"Affine matrix saved to {filename}")

    def apply_affine(self, x_pix, y_pix):
        """Convert pixel coordinates to stage coordinates using the affine matrix."""
        if self.affine_matrix is None:
            return None

        pt = np.array([x_pix, y_pix, 1], dtype=np.float32)
        stage_coords = self.affine_matrix @ pt
        return stage_coords[0], stage_coords[1]
