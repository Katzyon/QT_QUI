#tiling of a 2D array with sqaure tiles
import numpy as np
import cv2
import os
# Define the directory to save the square tiles
Squares = r"D:\DATA\Patterns\Squares_114px"
if not os.path.exists(Squares):
    os.makedirs(Squares)


dmd_shape = (1140, 912)  # height, width
square_size = 114  # size of the square in pixels
rows = dmd_shape[0] // square_size
cols = dmd_shape[1] // square_size
frame_idx = 0

for r in range(rows):
            for c in range(cols):
                image = np.zeros(dmd_shape, dtype=np.uint8)
                y_start = r * square_size
                x_start = c * square_size
                image[y_start:y_start + square_size, x_start:x_start + square_size] = 255

                filename = os.path.join(Squares, f"frame_{frame_idx:04d}.bmp")
                cv2.imwrite(filename, image)
                frame_idx += 1

