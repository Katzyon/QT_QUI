# Randomly group n cells bodies in a single image within a selected area for DMD stimulation


import numpy as np
import random
from PIL import Image
import matplotlib.pyplot as plt
from collections import defaultdict


def load_tif_image(path):
    """ Load a .tif image and return it as a numpy array """
    with Image.open(path) as img:
        return np.array(img)

def identify_cells(image):
    """ Identify unique cells in the image, excluding background (value 0) """
    unique_cells = np.unique(image) # np.array of the unique numbers in the image Is it normalized?
    print(type(unique_cells))
    return unique_cells[unique_cells != 0]  # Exclude background

def randomly_group_cells(cells, group_size):
    """ Randomly group cell's numbers into groups of a specified size """
    random.shuffle(cells)
    return [cells[i:i + group_size] for i in range(0, len(cells), group_size)]

def color_groups(image, groups):
    """ Color each group of cells in the image with a unique color """
    colored_image = np.zeros_like(image)
    for group_id, group in enumerate(groups, start=1):
        for cell_id in group:
            colored_image[image == cell_id] = group_id # color all pixels with the cell ID with the group ID
    return colored_image

def group_cells_in_image(self):
    """ Group cells in an image and return the new image and the group list """
    
    cells = self.unique_cells # list of indexed cells in the image
    groups = randomly_group_cells(cells, self.rand_group_size) # create groups of size self.rand_group_size
    colored_image = color_groups(self.masks , groups)

    # Create a mapping of cell ID to group ID
    self.group_sums = {}
    cell_group_mapping = defaultdict(list)
    for group_id, group in enumerate(groups, start=1):
        for cell_id in group:
            cell_group_mapping[cell_id].append(group_id) # create a dictionary with cell_id as key and group_id as value
            cell_image = self.binary_images[cell_id - 1] # cell_image is the binary image of the cell with cell_id-1
            # add the image to the group_sums dictionary
            if group_id in self.group_sums:
                self.group_sums[group_id] += cell_image
            else:
                self.group_sums[group_id] = cell_image.copy()


    # plot all the groups
    fig, axes = plt.subplots(1, len(self.group_sums), figsize=(20, 20))
    for i, (group_id, image) in enumerate(self.group_sums.items()):
        axes[i].imshow(image, cmap='gray')
        axes[i].set_title(f"Group {group_id}")
    plt.show()
        





# handle external call 
# if __name__ == "__main__":

#     # Example usage
#     image_path = r"D:\DATA\Patterns\Patt_2023-11-14\Images\mask_output.tif"  # Replace with the actual image path
#     group_size = 4
#     colored_image, cell_group_mapping = group_cells_in_image(self)

#     # Since we cannot execute this without the actual image, we'll just display the structure of cell_group_mapping
#     print("Cell Group Mapping (Example):", dict(list(cell_group_mapping.items())[:12]))  # Display first 5 for example

#     # We would also save the colored image and the mapping to files, but this is left as an exercise
#     # due to lack of the actual image and environment setup.
#     fig, ax = plt.subplots()
#     ax.imshow(colored_image)
#     plt.show()



# Main function
# def main():
#     image_path =  r"D:\DATA\Patterns\Patt_2023-11-14\Images\mask_output.tif"


#     image = tifffile.imread(image_path) # cell mask image
#     image_scaled = ((image - image.min()) * (255 / (image.max() - image.min()))).astype(np.uint8) # normalize image to 0-255
# # change the background to white
#     image_rgb = np.stack((image_scaled,)*3, axis=-1) # convert to rgb
#     image_rgb[image_rgb == 0] = 255
