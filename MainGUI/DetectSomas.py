import numpy as np
from cellpose import models
import matplotlib.pyplot as plt

def detect_somas(img_array, diameter=8):
    """
    Detect somas in a numpy array using cellpose.
    
    Parameters:
    - img_array: 2D numpy array representing the image.
    - diameter: approximate diameter of the soma. Default is 30 pixels.

    Returns:
    - mask: numpy array where each pixel in a soma has a unique integer label.
    """
    
    # Ensure the image is in uint8 format
    img_array = (img_array - np.min(img_array)) / np.ptp(img_array) * 255
    img_array = img_array.astype(np.uint8)

    # Initialize the cellpose model for cyto (soma) detection
    model = models.Cellpose(gpu=False, model_type='cyto')

    # Run the model on the image
    masks, flows, styles, diams = model.eval(img_array, diameter=diameter, channels=[0,0])
    plt.imshow(masks)
    plt.title("Detected Somas with Cellpose_DetectSomas.py")
    plt.show()

    return masks

if __name__ == '__main__':
    # Example: Generate a synthetic numpy array representing an image with random noise
    # Replace this with your numpy array data
    np.random.seed(0)
    img_array = np.random.rand(512, 512)
    
    detected_somas = detect_somas(img_array)

    # Display detected somas using matplotlib
    plt.imshow(detected_somas)
    plt.title("Detected Somas with Cellpose")
    plt.show()
