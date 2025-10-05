# load cell masks and group cells by mouse clicking on them

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import tifffile
from matplotlib.widgets import Button
from matplotlib.figure import Figure
from PySide6.QtCore import QObject, Signal

class CellPickerWidget(QWidget):
    def __init__(self, image):
        super().__init__()
        self.cell_picker = CellPicker(image)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        #canvas = FigureCanvas(self.cell_picker.fig)
        canvas = self.cell_picker.canvas
        self.cell_picker.request_close.connect(self.close)
        layout.addWidget(canvas)

    def closeEvent(self, event):
        # Handle any cleanup or signals before the widget is closed
        self.cell_picker.groups_ready.emit(self.cell_picker.groups)
        import matplotlib.pyplot as plt
        try:
            plt.close(self.cell_picker.fig)
        except Exception:
            pass
        super().closeEvent(event)


class CellPicker(QObject): # 
    request_close = Signal()
    groups_ready = Signal(list) # Signal to emit groups when they are updated in the GUI

    def __init__(self, image, parent=None):
        super(CellPicker, self).__init__(parent)
        assert len(image.shape) == 2, "Image should be a 2D array."

        self.flip_x_display = True              # <<< match your other viewers (fliplr)
        self.rotate_k = 3                     # <<< match your other viewers (0,1,2,3 = 0°,90°,180°,270°)
        self.H, self.W = image.shape            # <<< keep dimensions for mapping

        self.original_image = image
        self.image_scaled = ((image - image.min()) * (255 / (image.max() - image.min()))).astype(np.uint8)
        self.image_rgb = np.stack((self.image_scaled,)*3, axis=-1)

        self.selected_cells = set()
        self.groups = []
        self.current_group_id = 0

        self.fig = Figure()
        self.fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.2)
        self.ax = self.fig.add_subplot(111) 
        self.button_ax = self.fig.add_axes([0.35, 0.05, 0.2, 0.075])

        self.button = Button(self.button_ax, 'Group Cells')
        self.button.on_clicked(self.group_cells)

        self.close_ax = self.fig.add_axes([0.70, 0.05, 0.2, 0.075])
        self.close_button = Button(self.close_ax, 'Close')
        self.close_button.on_clicked(self.close_figure)

        self.canvas = FigureCanvas(self.fig)
        self.cid = self.fig.canvas.mpl_connect('button_press_event', self)

        # draw FLIPPED view for the user; keep data in RAW orientation
        self.im = self.ax.imshow(self._to_display(self.image_rgb), interpolation='nearest')
        

        
    def _to_display(self, arr):
        """Rotate CCW by rotate_k, then optionally flip horizontally for display."""
        out = np.rot90(arr, k=self.rotate_k)
        return np.fliplr(out) if self.flip_x_display else out

    def _disp_to_raw(self, x_disp, y_disp):
        """
        Map display (imshow) coords back to raw image coords.
        Invert flip first, then invert rotation, for any rotate_k in {0,1,2,3}.
        """
        x = int(round(x_disp))
        y = int(round(y_disp))

        # width of the displayed image after rotation
        disp_W = self.W if (self.rotate_k % 2 == 0) else self.H

        # undo optional horizontal flip on the displayed image
        if self.flip_x_display:
            x = disp_W - 1 - x

        # undo rotation (inverse mapping of np.rot90(arr, k=self.rotate_k))
        if self.rotate_k == 0:        # 0°
            x_raw, y_raw = x, y
        elif self.rotate_k == 1:      # 90° CCW
            x_raw = self.W - 1 - y
            y_raw = x
        elif self.rotate_k == 2:      # 180°
            x_raw = self.W - 1 - x
            y_raw = self.H - 1 - y
        elif self.rotate_k == 3:      # 270° CCW
            x_raw = y
            y_raw = self.H - 1 - x
        else:
            raise ValueError("rotate_k must be in {0,1,2,3}")

        return x_raw, y_raw




    def __call__(self, event):
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            return

        # display coords from matplotlib → raw coords for data
        x_raw, y_raw = self._disp_to_raw(event.xdata, event.ydata)

        # bounds check
        if not (0 <= x_raw < self.W and 0 <= y_raw < self.H):
            return

        # look up label in RAW mask
        cell_value = self.original_image[y_raw, x_raw]
        if cell_value == 0 or any(cell_value in group['cells'] for group in self.groups):
            return

        self.selected_cells.add(cell_value)
        unique_color = np.random.randint(0, 256, 3)
        mask = (self.original_image == cell_value)   # mask in RAW
        self.image_rgb[mask] = unique_color          # recolor RAW data

        # redraw FLIPPED view
        self.im.set_data(self._to_display(self.image_rgb))
        self.fig.canvas.draw_idle()



    def group_cells(self, event):

        if not self.selected_cells:
            print("No cells selected; nothing to group.")
            return
        
        group_color = np.random.randint(0, 256, 3)
        # Update the image to show one group color for all selected cells
        for cell_value in self.selected_cells: # set same color for all cells in the group
            mask = self.original_image == cell_value
            self.image_rgb[mask] = group_color

        self.groups.append({
            'cells': list(self.selected_cells),
            'color': tuple(group_color)  # Save color as a tuple to ensure immutability
        })

        # Optional: Print group info
        print(f"Group {self.current_group_id}: Cells {self.groups[self.current_group_id]['cells']}, Color {self.groups[self.current_group_id]['color']}")

        self.current_group_id += 1
        self.selected_cells.clear()

        #self.ax.clear()
        self.im.set_data(self._to_display(self.image_rgb))
        self.fig.canvas.draw_idle()

        # self.ax.imshow(self.image_rgb)
        # self.fig.canvas.draw()

    def close_figure(self, event=None):
            self.request_close.emit()   # ask the hosting widget to close
