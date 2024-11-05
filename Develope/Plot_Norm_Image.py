
import tifffile
import numpy as np
import matplotlib.pyplot as plt

#image_dir = r"C:\Users\jtsch\Documents\GitHub\QT_GUI\Develope\test_images"
image_dir = r"D:\DATA\Patterns\Patt_2023-11-14\Images"
image_path = image_dir + r"\mask_output.tif"
image = tifffile.imread(image_path) # cell mask image

image_scaled = ((image - image.min()) * (255 / (image.max() - image.min()))).astype(np.uint8) # normalize image to 0-255
# change the background to white
image_rgb = np.stack((image_scaled,)*3, axis=-1) # convert to rgb
image_rgb[image_rgb == 0] = 255


fig, ax = plt.subplots()
ax.imshow(image_rgb)
plt.show()
