import numpy as np
import matplotlib.pyplot as plt

figure_references = {}

def display_image(img_data, caller_id=None):
    if caller_id is None:
        caller_id = id(img_data)

    # Match ClickCollector orientation: rotate 90° CCW
    if caller_id == "cam_image":
        img_data = np.rot90(img_data, k=1)   # 90° counter-clockwise

    if caller_id not in figure_references:
        figure_references[caller_id] = plt.figure()
        figure_references[caller_id].canvas.manager.window.move(800, 50)
    else:
        plt.figure(figure_references[caller_id].number)

    plt.clf()
    plt.imshow(img_data, cmap='gray', origin='upper')
    plt.axis('off')
    plt.show()
