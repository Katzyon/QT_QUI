import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.widgets import PolygonSelector, Button

class SelectFromImage:
    def __init__(self, fig, ax, img):
        self.fig = fig
        self.ax = ax
        self.canvas = ax.figure.canvas
        self.img = img
        self.selector = PolygonSelector(ax, self.onselect, useblit=True, props=dict(color='r', linestyle='-', linewidth=2, alpha=0.5))
        self.add_explanation_text()
        self.add_clear_button()

    def add_explanation_text(self):
        # Add explanatory text to the figure
        self.fig.text(0.5, 0.97, 'Draw a polygon to select an area',
                      ha='center', fontsize=8, bbox=dict(boxstyle='round,pad=0.1', edgecolor='green', facecolor='white', alpha=0.4))
        self.fig.text(0.5, 0.94, 'Double click to finish the selection',
                      ha='center', fontsize=8, bbox=dict(boxstyle='round,pad=0.1', edgecolor='green', facecolor='white', alpha=0.4))
        self.fig.text(0.5, 0.90, 'Press Esc to start a new selection',
                      ha='center', fontsize=8, bbox=dict(boxstyle='round,pad=0.1', edgecolor='red', facecolor='white', alpha=0.4))

    def add_clear_button(self):
        # Add a button to clear all selected areas
        ax_clear = plt.axes([0.81, 0.05, 0.1, 0.075])
        self.btn_clear = Button(ax_clear, 'Clear')
        self.btn_clear.on_clicked(self.clear_and_reset)

    def onselect(self, verts):
        path = Path(verts)
        mask = np.zeros(self.img.shape, dtype=bool)

        for i in range(self.img.shape[0]):
            for j in range(self.img.shape[1]):
                mask[i, j] = path.contains_point((j, i))

        selected_area = self.img[mask]
        unique_cells = np.unique(selected_area)
        unique_cells = unique_cells[unique_cells != 0]  # Exclude background (0 value)

        print(f"Unique cell values in the selected area: {unique_cells}")
        self.disconnect()

    def disconnect(self):
        self.selector.disconnect_events()
        self.canvas.draw_idle()
        # Clear the polygon selector from the plot to start a new selection
        self.selector = PolygonSelector(self.ax, self.onselect, useblit=True, props=dict(color='r', linestyle='-', linewidth=2, alpha=0.5))

    def clear_and_reset(self, event):
        # Clear the entire axes and re-plot the image
        self.ax.clear()
        self.ax.imshow(self.img, cmap='gray')
        self.add_explanation_text()
        self.selector = PolygonSelector(self.ax, self.onselect, useblit=True, props=dict(color='r', linestyle='-', linewidth=2, alpha=0.5))
        self.canvas.draw_idle()

# Load the image and convert it to a numpy array
path = "D:/DATA/Patterns/Patt_2024-07-14/Images/mask_output.tif"
with Image.open(path) as img:
    img_array = np.array(img)

fig, ax = plt.subplots()
ax.imshow(img_array, cmap='gray')

selector = SelectFromImage(fig, ax, img_array)
plt.show()
