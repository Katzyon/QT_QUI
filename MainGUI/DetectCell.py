import numpy as np
import cv2
import matplotlib.pyplot as plt

def detect_particles(img_array, min_area, max_area):
    # Convert numpy array to an 8-bit format for OpenCV processing
    img_array = (img_array - np.min(img_array)) / np.ptp(img_array)
    img_array = (img_array * 255).astype(np.uint8)
    
    # Apply GaussianBlur to reduce noise and enhance particle detection
    blurred = cv2.GaussianBlur(img_array, (5, 5), 0)

    # Thresholding to segment potential particles
    _, thresholded = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Detect contours representing potential particles
    contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter out particles based on the area
    contours = [cnt for cnt in contours if min_area <= cv2.contourArea(cnt) <= max_area]

    # Draw the detected particles on a copy of the original array
    output_img = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
    cv2.drawContours(output_img, contours, -1, (0, 255, 0), 2)

    return output_img

if __name__ == '__main__':
    # Example: Generate a synthetic numpy array representing an image with random noise
    np.random.seed(0)
    img_array = np.random.rand(512, 512)
    
    min_area = 80
    max_area = 200  # Adjust these values based on your requirements

    output = detect_particles(img_array, min_area, max_area)

    # Display using matplotlib
    plt.imshow(output, cmap='gray')
    plt.title("Detected Particles")
    plt.show()
