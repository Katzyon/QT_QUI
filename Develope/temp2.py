import cv2

image_path = r"D:\DATA\Patterns\Patt_2023-11-13\Images\mask_output.tif"

# Read the image
img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

# Check if the image was loaded properly
if img is not None:
    # Normalize the image to 0 to max 255
    img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)

    # Show the image
    cv2.imshow('Normalized Image', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print("Error: Image cannot be read. Check the file path or file format.")
