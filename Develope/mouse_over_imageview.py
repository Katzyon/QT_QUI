import sys
import numpy as np
import pyqtgraph as pg
from PySide6 import QtWidgets, QtCore

class ImageViewerWithStatusBar(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Create the ImageView widget
        self.image_view = pg.ImageView()
        self.setCentralWidget(self.image_view)

        # Create and set the status bar
        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)

        # Load a sample image
        self.data = np.random.normal(size=(100, 100))
        self.image_view.setImage(self.data)

        # Connect mouse movement to handler
        self.proxy = pg.SignalProxy(
            self.image_view.view.scene().sigMouseMoved,
            rateLimit=60,
            slot=self.mouse_moved
        )

    def mouse_moved(self, evt):
        pos = QtCore.QPointF(*evt)
        if self.imageview.view.sceneBoundingRect().contains(pos):
            mp = self.imageview.view.mapSceneToView(pos)
            x, y = mp.x(), mp.y()

            if self.at_calibrator.affine_matrix is not None:
                sx, sy = self.at_calibrator.apply_affine(x, y)
                self.statusBar().showMessage(f"Stage: ({sx:.2f}, {sy:.2f}) µm")
            else:
                self.statusBar().showMessage(f"Pixel: ({x:.1f}, {y:.1f})")



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    viewer = ImageViewerWithStatusBar()
    viewer.setWindowTitle("Image Viewer with Mouse Coordinates")
    viewer.resize(800, 600)
    viewer.show()
    sys.exit(app.exec())
