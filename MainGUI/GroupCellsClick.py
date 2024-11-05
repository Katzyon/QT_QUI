# load cell masks and group cells by mouse clicking on them

import tifffile
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

class CellPicker:
    def __init__(self, image):
        assert len(image.shape) == 2, "Image should be a 2D array."

        self.original_image = image
        self.image_scaled = ((image - image.min()) * (255 / (image.max() - image.min()))).astype(np.uint8)
        self.image_rgb = np.stack((self.image_scaled,)*3, axis=-1)
        self.selected_cells = set()
        self.groups = []  # Updated to store groups as objects
        self.current_group_id = 0

        self.fig, self.ax = plt.subplots()
        self.button_ax = self.fig.add_axes([0.8, 0.05, 0.1, 0.075])
        self.button = Button(self.button_ax, 'Group Cells')
        self.button.on_clicked(self.group_cells)

        self.cid = self.fig.canvas.mpl_connect('button_press_event', self)
        self.ax.imshow(self.image_rgb)
        plt.show()

    # This method is called whenever the user clicks on the image
    def __call__(self, event):
        if event.inaxes is not None:
            row, col = int(event.ydata), int(event.xdata)
            cell_value = self.original_image[row, col] # cell value is the index of the cell in the image

            if cell_value == 0 or any(cell_value in group['cells'] for group in self.groups):
                return

            self.selected_cells.add(cell_value)
            unique_color = np.random.randint(0, 256, 3)
            mask = self.original_image == cell_value
            self.image_rgb[mask] = unique_color

            self.ax.clear()
            self.ax.imshow(self.image_rgb)
            self.fig.canvas.draw()

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
        self.ax.imshow(self.image_rgb)
        self.fig.canvas.draw()

# # Replace 'your_image_path' with the path to your actual np.uint8 image file
# image_path = r"D:\DATA\Patterns\Patt_2023-11-06\Images\mask_output.tif"
# read_mask_image = tifffile.imread(image_path)
# cell_picker = CellPicker(read_mask_image)
