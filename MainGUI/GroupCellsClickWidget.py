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
        layout.addWidget(canvas)

    def closeEvent(self, event):
        # Handle any cleanup or signals before the widget is closed
        self.cell_picker.groups_ready.emit(self.cell_picker.groups)
        super().closeEvent(event)


class CellPicker(QObject): # 

    groups_ready = Signal(list) # Signal to emit groups when they are updated in the GUI

    def __init__(self, image, parent=None):
        super(CellPicker, self).__init__(parent)
        assert len(image.shape) == 2, "Image should be a 2D array."

        self.flip_x_display = True              # <<< match your other viewers (fliplr)
        self.H, self.W = image.shape            # <<< keep dimensions for mapping

        self.original_image = image
        self.image_scaled = ((image - image.min()) * (255 / (image.max() - image.min()))).astype(np.uint8)
        self.image_rgb = np.stack((self.image_scaled,)*3, axis=-1)

        self.selected_cells = set()
        self.groups = []
        self.current_group_id = 0

        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        self.button_ax = self.fig.add_axes([0.8, 0.05, 0.1, 0.075])

        self.button = Button(self.button_ax, 'Group Cells')
        self.button.on_clicked(self.group_cells)
        self.canvas = FigureCanvas(self.fig)
        self.cid = self.fig.canvas.mpl_connect('button_press_event', self)

        # draw FLIPPED view for the user; keep data in RAW orientation
        self.im = self.ax.imshow(self._to_display(self.image_rgb), interpolation='nearest')
        

    # def __init__(self, image, parent=None):
    #     super(CellPicker, self).__init__(parent)
    #     assert len(image.shape) == 2, "Image should be a 2D array."

    #     self.original_image = image
    #     self.image_scaled = ((image - image.min()) * (255 / (image.max() - image.min()))).astype(np.uint8)
    #     self.image_rgb = np.stack((self.image_scaled,)*3, axis=-1)
    #     self.selected_cells = set()
    #     self.groups = []  # Updated to store groups as objects
    #     self.current_group_id = 0

    #     #self.fig, self.ax = plt.subplots()
    #     self.fig = Figure()
    #     self.ax = self.fig.add_subplot(111)
    #     self.button_ax = self.fig.add_axes([0.8, 0.05, 0.1, 0.075])
        
    #     self.button = Button(self.button_ax, 'Group Cells')
    #     self.button.on_clicked(self.group_cells)
    #     self.canvas = FigureCanvas(self.fig)
    #     self.cid = self.fig.canvas.mpl_connect('button_press_event', self)
    #     self.ax.imshow(self.image_rgb)
    #     #plt.show()
        
    def _to_display(self, arr):
        # flip horizontally ONLY for display
        return np.fliplr(arr) if self.flip_x_display else arr

    def _disp_to_raw(self, x_disp, y_disp):
        # map display coords back to RAW (invert X only)
        x = int(round(x_disp)); y = int(round(y_disp))
        if self.flip_x_display:
            x = self.W - 1 - x
        return x, y

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


    # # This method is called whenever the user clicks on the image
    # def __call__(self, event):
    #     if event.inaxes is not None:
    #         row, col = int(event.ydata), int(event.xdata)
    #         cell_value = self.original_image[row, col] # cell value is the index of the cell in the image

    #         if cell_value == 0 or any(cell_value in group['cells'] for group in self.groups):
    #             return

    #         self.selected_cells.add(cell_value)
    #         unique_color = np.random.randint(0, 256, 3)
    #         mask = self.original_image == cell_value
    #         self.image_rgb[mask] = unique_color

    #         self.ax.clear()
    #         self.ax.imshow(self.image_rgb)
    #         self.fig.canvas.draw()

    def group_cells(self, event):
        group_color = np.random.randint(0, 256, 3)
        # Update the image to show one group color for all selected cells
        for cell_value in self.selected_cells:
            mask = self.original_image == cell_value
            self.image_rgb[mask] = group_color

        # Create a new group object with separate attributes for cells and color
        # print("self.current_group_id", self.current_group_id)
        # print("group type", type(self.groups))
        # print("type of self.current_group_id", type(self.current_group_id))
        # print("self.groups", self.groups)
        # self.groups[self.current_group_id] = {
        #     'cells': list(self.selected_cells),
        #     'color': tuple(group_color)  # Save color as a tuple to ensure immutability
        # }
        self.groups.append({
            'cells': list(self.selected_cells),
            'color': tuple(group_color)  # Save color as a tuple to ensure immutability
        })

        # Optional: Print group info
        print(f"Group {self.current_group_id}: Cells {self.groups[self.current_group_id]['cells']}, Color {self.groups[self.current_group_id]['color']}")

        self.current_group_id += 1
        self.selected_cells.clear()

        self.ax.clear()
        self.im.set_data(self._to_display(self.image_rgb))
        self.fig.canvas.draw_idle()

        # self.ax.imshow(self.image_rgb)
        # self.fig.canvas.draw()


