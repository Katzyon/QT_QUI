"""
Mosaic acquisition GUI (independent of maingui.py)
- Snake by rows, Right & Down
- Connects to a running Micro-Manager 2.0 instance via pycromanager.Core (Bridge is NOT used).
- Lets you define Left/Right/Top/Bottom bounds from the current stage position.
- Computes a tiled XY grid using camera FOV (image size * pixel size) and user-specified overlap.
- Acquires one snap per position and saves tiles to disk (TIFF), plus a CSV of stage positions.

Requirements:
  pip install pycromanager PySide6 tifffile numpy

Usage:
  1) Start Micro-Manager and load your hardware config.
  2) Run: python mosaic_gui_updated.py
"""
import sys
from pathlib import Path

# Add QT_GUI/MainGUI to Python path (so we can import Camera.py and stage_controller.py)
THIS_DIR = Path(__file__).resolve().parent
MAINGUI_DIR = THIS_DIR.parent / "MainGUI"
sys.path.insert(0, str(MAINGUI_DIR))

import os
import csv
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np
import tifffile as tiff
from PySide6 import QtCore, QtWidgets

# Local project modules (no changes to maingui.py required)
from stage_controller import StageController
from Camera import getImage


@dataclass
class Bounds:
    left_x: Optional[float] = None
    right_x: Optional[float] = None
    top_y: Optional[float] = None
    bottom_y: Optional[float] = None

    def is_complete(self) -> bool:
        return None not in (self.left_x, self.right_x, self.top_y, self.bottom_y)

    def normalized(self) -> "Bounds":
        if not self.is_complete():
            return self
        left = min(self.left_x, self.right_x)
        right = max(self.left_x, self.right_x)
        top = min(self.top_y, self.bottom_y)
        bottom = max(self.top_y, self.bottom_y)
        return Bounds(left, right, top, bottom)


def safe_float(v: str, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


def get_pixel_size_um(core) -> Optional[float]:
    """Reads the currently active Micro-Manager Pixel Size Calibration (µm/pixel)."""
    for name in ("get_pixel_size_um", "get_pixel_size_um_by_name"):
        if hasattr(core, name):
            try:
                if name == "get_pixel_size_um":
                    val = getattr(core, name)()
                    if val and val > 0:
                        return float(val)
                else:
                    if hasattr(core, "get_pixel_size_config"):
                        cfg = core.get_pixel_size_config()
                        if cfg:
                            val = getattr(core, name)(cfg)
                            if val and val > 0:
                                return float(val)
            except Exception:
                pass
    return None


def compute_grid(
    bounds: Bounds,
    fov_x: float,
    fov_y: float,
    overlap_x: float,
    overlap_y: float,
    snake: bool = True
) -> List[Tuple[float, float, int, int]]:
    """
    Returns a list of (x_um, y_um, col, row) target stage positions.

    IMPORTANT:
    - These are absolute stage coordinates in µm as reported by StageController.get_position().
    - StageController handles any inversion semantics internally (relative move commands).
    """
    b = bounds.normalized()

    step_x = max(1e-6, fov_x - overlap_x)
    step_y = max(1e-6, fov_y - overlap_y)

    width = b.right_x - b.left_x
    height = b.bottom_y - b.top_y

    ncols = int(np.floor(width / step_x)) + 1
    nrows = int(np.floor(height / step_y)) + 1

    positions = []
    for r in range(nrows):
        y = b.top_y + r * step_y
        cols = list(range(ncols))
        if snake and (r % 2 == 1):
            cols = list(reversed(cols))
        for c in cols:
            x = b.left_x + c * step_x
            positions.append((x, y, c, r))
    return positions


class MosaicWorker(QtCore.QThread):
    progress = QtCore.Signal(int, int)     # done, total
    status = QtCore.Signal(str)
    finished_ok = QtCore.Signal(str)       # output_dir
    failed = QtCore.Signal(str)

    def __init__(
        self,
        core,
        stage: StageController,
        output_dir: str,
        positions: List[Tuple[float, float, int, int]],
        camera_wrapper: getImage,
        settle_ms: int = 50
    ):
        super().__init__()
        self.core = core
        self.stage = stage
        self.output_dir = output_dir
        self.positions = positions
        self.camera = camera_wrapper
        self.settle_ms = int(settle_ms)
        self._stop = False

    def request_stop(self):
        self._stop = True

    def run(self):
        try:
            os.makedirs(self.output_dir, exist_ok=True)

            manifest_path = os.path.join(self.output_dir, "tiles_manifest.csv")
            with open(manifest_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["index", "row", "col", "x_um", "y_um", "filename"])

                total = len(self.positions)
                for i, (x, y, c, r) in enumerate(self.positions):
                    if self._stop:
                        self.status.emit("Stopped by user.")
                        self.finished_ok.emit(self.output_dir)
                        return

                    self.status.emit(f"Moving to tile {i+1}/{total} (row={r}, col={c})")
                    # Critical change: use StageController (relative moves + waits) instead of core.set_xy_position
                    self.stage.move_to(float(x), float(y))

                    if self.settle_ms > 0:
                        time.sleep(self.settle_ms / 1000.0)

                    self.status.emit(f"Snapping tile {i+1}/{total}")
                    img = self.camera.snap_image(self.core)
                    if img is None:
                        raise RuntimeError("Camera returned None image")

                    fname = f"tile_r{r:03d}_c{c:03d}_i{i:04d}.tif"
                    out_path = os.path.join(self.output_dir, fname)
                    tiff.imwrite(out_path, img, photometric="minisblack")

                    w.writerow([i, r, c, float(x), float(y), fname])
                    self.progress.emit(i + 1, total)

            self.status.emit("Acquisition complete.")
            self.finished_ok.emit(self.output_dir)

        except Exception as e:
            self.failed.emit(str(e))


class MosaicGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mosaic Acquisition (Core-only)")

        self.core = None
        self.xy_stage_device = None
        self.camera = None
        self.stage = None

        self.bounds = Bounds()
        self.positions = []

        self._worker = None

        self._build_ui()

    def _build_ui(self):
        w = QtWidgets.QWidget()
        self.setCentralWidget(w)
        layout = QtWidgets.QVBoxLayout(w)

        # 1) Connection
        conn_box = QtWidgets.QGroupBox("1) Connection")
        conn_l = QtWidgets.QGridLayout(conn_box)
        self.btn_connect = QtWidgets.QPushButton("Connect to Micro-Manager")
        self.btn_disconnect = QtWidgets.QPushButton("Disconnect")
        self.btn_disconnect.setEnabled(False)
        self.lbl_devices = QtWidgets.QLabel("Not connected.")
        conn_l.addWidget(self.btn_connect, 0, 0)
        conn_l.addWidget(self.btn_disconnect, 0, 1)
        conn_l.addWidget(self.lbl_devices, 1, 0, 1, 2)
        layout.addWidget(conn_box)

        # 2) Bounds
        b_box = QtWidgets.QGroupBox("2) Define Bounds from Current Stage Position")
        b_l = QtWidgets.QGridLayout(b_box)

        self.btn_set_left = QtWidgets.QPushButton("Set LEFT (X)")
        self.btn_set_right = QtWidgets.QPushButton("Set RIGHT (X)")
        self.btn_set_top = QtWidgets.QPushButton("Set TOP (Y)")
        self.btn_set_bottom = QtWidgets.QPushButton("Set BOTTOM (Y)")
        for b in (self.btn_set_left, self.btn_set_right, self.btn_set_top, self.btn_set_bottom):
            b.setEnabled(False)

        self.lbl_bounds = QtWidgets.QLabel("Bounds: not set")

        b_l.addWidget(self.btn_set_left, 0, 0)
        b_l.addWidget(self.btn_set_right, 0, 1)
        b_l.addWidget(self.btn_set_top, 1, 0)
        b_l.addWidget(self.btn_set_bottom, 1, 1)
        b_l.addWidget(self.lbl_bounds, 2, 0, 1, 2)
        layout.addWidget(b_box)

        # 3) Grid parameters
        g_box = QtWidgets.QGroupBox("3) Grid Parameters")
        g_l = QtWidgets.QGridLayout(g_box)

        self.ed_overlap_um = QtWidgets.QLineEdit("60")
        self.ed_settle_ms = QtWidgets.QLineEdit("50")
        self.chk_snake = QtWidgets.QCheckBox("Snake pattern (recommended)")
        self.chk_snake.setChecked(True)

        self.lbl_fov = QtWidgets.QLabel("FOV: unknown (connect first)")
        self.btn_compute = QtWidgets.QPushButton("Compute Grid")
        self.btn_compute.setEnabled(False)
        self.lbl_grid = QtWidgets.QLabel("Grid: not computed")

        g_l.addWidget(QtWidgets.QLabel("Overlap (µm):"), 0, 0)
        g_l.addWidget(self.ed_overlap_um, 0, 1)
        g_l.addWidget(QtWidgets.QLabel("Settle after move (ms):"), 1, 0)
        g_l.addWidget(self.ed_settle_ms, 1, 1)
        g_l.addWidget(self.chk_snake, 2, 0, 1, 2)
        g_l.addWidget(self.lbl_fov, 3, 0, 1, 2)
        g_l.addWidget(self.btn_compute, 4, 0)
        g_l.addWidget(self.lbl_grid, 4, 1)
        layout.addWidget(g_box)

        # 4) Output and run
        r_box = QtWidgets.QGroupBox("4) Acquire Mosaic")
        r_l = QtWidgets.QGridLayout(r_box)

        self.ed_outdir = QtWidgets.QLineEdit(os.path.abspath("./mosaic_output"))
        self.btn_browse = QtWidgets.QPushButton("Browse…")
        self.btn_run = QtWidgets.QPushButton("Run Acquisition")
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.prog = QtWidgets.QProgressBar()
        self.lbl_status = QtWidgets.QLabel("Idle.")

        r_l.addWidget(QtWidgets.QLabel("Output directory:"), 0, 0)
        r_l.addWidget(self.ed_outdir, 0, 1)
        r_l.addWidget(self.btn_browse, 0, 2)
        r_l.addWidget(self.btn_run, 1, 1)
        r_l.addWidget(self.btn_stop, 1, 2)
        r_l.addWidget(self.prog, 2, 0, 1, 3)
        r_l.addWidget(self.lbl_status, 3, 0, 1, 3)
        layout.addWidget(r_box)

        # Wiring
        self.btn_connect.clicked.connect(self.on_connect)
        self.btn_disconnect.clicked.connect(self.on_disconnect)

        self.btn_set_left.clicked.connect(lambda: self.set_bound("left"))
        self.btn_set_right.clicked.connect(lambda: self.set_bound("right"))
        self.btn_set_top.clicked.connect(lambda: self.set_bound("top"))
        self.btn_set_bottom.clicked.connect(lambda: self.set_bound("bottom"))

        self.btn_compute.clicked.connect(self.on_compute_grid)

        self.btn_browse.clicked.connect(self.on_browse)
        self.btn_run.clicked.connect(self.on_run)
        self.btn_stop.clicked.connect(self.on_stop)

    def _refresh_bounds_label(self):
        b = self.bounds
        self.lbl_bounds.setText(
            f"Bounds (user coords): left_x={b.left_x}, right_x={b.right_x}, top_y={b.top_y}, bottom_y={b.bottom_y}"
        )

    def on_connect(self):
        try:
            from pycromanager import Core  # local import so GUI opens even if missing
            # Use the same style as your existing project (helps with method signature translation)
            self.core = Core(convert_camel_case=True)

            cam_dev = self.core.get_camera_device()
            xy_dev = self.core.get_xy_stage_device()

            if not cam_dev:
                raise RuntimeError("No camera device reported by Micro-Manager (core.get_camera_device()).")
            if not xy_dev:
                raise RuntimeError("No XY stage device reported by Micro-Manager (core.get_xy_stage_device()).")

            self.xy_stage_device = xy_dev

            # Wrap using your existing project classes
            self.camera = getImage(self.core)
            self.stage = StageController(self.core, self.xy_stage_device, stage_position_label=None)

            w_px = int(self.core.get_image_width())
            h_px = int(self.core.get_image_height())
            pix_um = get_pixel_size_um(self.core)

            if pix_um is None:
                self.lbl_fov.setText(f"FOV: {w_px}x{h_px} px; pixel size unknown in MM (set Pixel Size Calibration)")
            else:
                fov_x = w_px * pix_um
                fov_y = h_px * pix_um
                self.lbl_fov.setText(f"FOV: {w_px}x{h_px} px; {pix_um:.4f} µm/px; ~{fov_x:.1f}×{fov_y:.1f} µm")

            self.lbl_devices.setText(f"Connected. Camera={cam_dev} | XYStage={xy_dev}")
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)

            for b in (self.btn_set_left, self.btn_set_right, self.btn_set_top, self.btn_set_bottom):
                b.setEnabled(True)
            self.btn_compute.setEnabled(True)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Connect failed", str(e))

    def on_disconnect(self):
        try:
            self.core = None
            self.xy_stage_device = None
            self.camera = None
            self.stage = None
            self.positions = []
            self.bounds = Bounds()

            self.lbl_devices.setText("Not connected.")
            self.lbl_fov.setText("FOV: unknown (connect first)")
            self.lbl_grid.setText("Grid: not computed")
            self._refresh_bounds_label()

            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
            for b in (self.btn_set_left, self.btn_set_right, self.btn_set_top, self.btn_set_bottom):
                b.setEnabled(False)
            self.btn_compute.setEnabled(False)
            self.btn_run.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.prog.setValue(0)
            self.lbl_status.setText("Idle.")
        except Exception:
            pass

    def _get_stage_xy(self) -> Tuple[float, float]:
        """Return stage position in the SAME coordinate system expected by StageController.move_to().

        StageController.get_position() returns the *physical* adapter coordinates (as reported by Core).
        StageController.move_to(x_target, y_target) expects the *GUI/user* coordinates:
            sx = Mx * x_physical,  sy = My * y_physical
        where Mx/My depend on invert_x/invert_y. If we store bounds in physical coordinates,
        then move_to() will apply inversion a second time and the stage will go to the wrong place.
        """
        x_phys, y_phys = self.stage.get_position()
        mx = -1.0 if getattr(self.stage, 'invert_x', False) else 1.0
        my = -1.0 if getattr(self.stage, 'invert_y', False) else 1.0
        return mx * x_phys, my * y_phys

    def set_bound(self, which: str):
        if not self.core or not self.stage:
            return
        x, y = self._get_stage_xy()
        if which == "left":
            self.bounds.left_x = x
        elif which == "right":
            self.bounds.right_x = x
        elif which == "top":
            self.bounds.top_y = y
        elif which == "bottom":
            self.bounds.bottom_y = y
        self._refresh_bounds_label()

    def on_compute_grid(self):
        if not self.core:
            return
        if not self.bounds.is_complete():
            QtWidgets.QMessageBox.warning(self, "Bounds incomplete", "Set LEFT, RIGHT, TOP, and BOTTOM first.")
            return

        w_px = int(self.core.get_image_width())
        h_px = int(self.core.get_image_height())
        pix_um = get_pixel_size_um(self.core)
        if pix_um is None:
            QtWidgets.QMessageBox.critical(
                self,
                "Pixel size missing",
                "Micro-Manager pixel size is not set.\n\n"
                "Fix in Micro-Manager: Devices → Pixel Size Calibration, select the active pixel size.\n"
                "Then reconnect and compute the grid again."
            )
            return

        overlap = safe_float(self.ed_overlap_um.text().strip(), 60.0)
        fov_x = w_px * pix_um
        fov_y = h_px * pix_um

        self.positions = compute_grid(
            self.bounds,
            fov_x=fov_x,
            fov_y=fov_y,
            overlap_x=overlap,
            overlap_y=overlap,
            snake=self.chk_snake.isChecked(),
        )

        max_c = max(p[2] for p in self.positions) if self.positions else 0
        max_r = max(p[3] for p in self.positions) if self.positions else 0
        self.lbl_grid.setText(f"{len(self.positions)} tiles (~{max_c+1}×{max_r+1})")
        self.btn_run.setEnabled(len(self.positions) > 0)
        self.prog.setValue(0)

    def on_browse(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select output directory", self.ed_outdir.text().strip()
        )
        if d:
            self.ed_outdir.setText(d)

    def on_run(self):
        if not self.core or not self.positions or not self.stage or not self.camera:
            return

        outdir = self.ed_outdir.text().strip()
        if not outdir:
            QtWidgets.QMessageBox.warning(self, "Output missing", "Please choose an output directory.")
            return

        settle_ms = int(safe_float(self.ed_settle_ms.text().strip(), 50))

        self._worker = MosaicWorker(
            core=self.core,
            stage=self.stage,
            output_dir=outdir,
            positions=self.positions,
            camera_wrapper=self.camera,
            settle_ms=settle_ms
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)

        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_status.setText("Starting…")
        self.prog.setMaximum(len(self.positions))
        self.prog.setValue(0)

        self._worker.start()

    def on_stop(self):
        if self._worker:
            self._worker.request_stop()
            self.btn_stop.setEnabled(False)

    def _on_progress(self, done: int, total: int):
        self.prog.setMaximum(total)
        self.prog.setValue(done)

    def _on_status(self, msg: str):
        self.lbl_status.setText(msg)

    def _on_finished(self, outdir: str):
        self.btn_stop.setEnabled(False)
        self.btn_run.setEnabled(True)
        self.lbl_status.setText(f"Done. Saved to: {outdir}")
        QtWidgets.QMessageBox.information(
            self,
            "Acquisition complete",
            f"Acquisition complete.\n\nTiles + manifest saved to:\n{outdir}\n\n"
            "Next (Fiji): Plugins → Stitching → Grid/Collection stitching.\n"
            "Use the tile naming order or manifest CSV."
        )

    def _on_failed(self, err: str):
        self.btn_stop.setEnabled(False)
        self.btn_run.setEnabled(True)
        self.lbl_status.setText("Failed.")
        QtWidgets.QMessageBox.critical(self, "Acquisition failed", err)


def main():
    app = QtWidgets.QApplication([])
    win = MosaicGUI()
    win.resize(820, 520)
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
