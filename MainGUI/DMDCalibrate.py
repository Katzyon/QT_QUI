# performing calibration of DMD
# Mouse click projection test


import numpy as np
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import cv2
# import Qwidget
# from PySide6.QtWidgets import QApplication, QWidget, QLabel
# from PySide6.QtGui import QPixmap, QImage
from scipy.ndimage import zoom
import time
from PIL import Image
import os
import ctypes
from PySide6.QtWidgets import QMessageBox


def generate_padded_checkerboard(rows, cols, square_size, target_width, target_height):
        """
        Generate a checkerboard image with the specified number of rows, columns, and square size.
        Pad the checkerboard so that it's centered within the target dimensions.
        """
        # Generate checkerboard
        pattern = np.zeros((rows * square_size, cols * square_size), dtype=np.uint8)
        for i in range(rows):
                for j in range(cols):
                        if (i + j) % 2 == 0:
                                pattern[i*square_size:(i+1)*square_size, j*square_size:(j+1)*square_size] = 255

        # Pad checkerboard
        height_padding = (target_height - pattern.shape[0]) // 2
        width_padding = (target_width - pattern.shape[1]) // 2

        pad_top = height_padding
        pad_bottom = target_height - pattern.shape[0] - pad_top
        pad_left = width_padding
        pad_right = target_width - pattern.shape[1] - pad_left

        return np.pad(pattern, ((pad_top, pad_bottom), (pad_left, pad_right)), mode='constant')

# get the core object
def dmd_calibrate(gui):
        
        core = gui.core
        print("DMD_Calibrate pressed")
        dmd_name = core.getSLMDevice() # get_slm_device() #'MightexPolygon1000' 
        print("DMD name: ", dmd_name)
        slm_width = core.getSLMWidth(dmd_name)
        slm_height = core.getSLMHeight(dmd_name)
        print("SLM height: ", slm_height, "SLM width: ", slm_width)
        core.slm_width = slm_width
        core.slm_height = slm_height
        core.camera_width = core.getImageWidth()
        core.camera_height = core.getImageHeight()

        # checkerboard dimensions - number of rectangles
        rows = 6
        cols = 7
        square_size = 50 # square width in pixels

        mask = generate_padded_checkerboard(rows, cols, square_size, slm_width, slm_height) # original "square" mask
        mask = cv2.bitwise_not(mask) # invert the mask
        

        #core.set_slm_image(dmd_name, mask)
        core.setSLMImage(dmd_name, mask) # compensate for the distortion of the projector
        core.displaySLMImage(dmd_name)
        time.sleep(1)

        core.snapImage()
        tagged_image = core.getTaggedImage() # the image is 1D array
        #print("tagged_image shape: ", tagged_image.pix.shape)
        #frame = core.camera.snapImage(self.core)
        pixels = np.reshape(tagged_image.pix,
                                newshape=[tagged_image.tags['Height'], tagged_image.tags['Width']]) # reshape the 1D array to 2D array

        # save the image as .png file
        img = Image.fromarray(pixels)
        # transform pixels using cv2 to image
        
        # change path to save the images in QT_GUI\MainGUI\Images
        #os.chdir("QT_GUI\MainGUI\Images")
        os.chdir("G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Images")
        img.save("camera_image.png")
        cv2.imwrite("dmd_pattern.png", mask) # save the mask as .png file
       
        #print(os.getcwd())

        # clear the SLM image
        core.setSLMImage(dmd_name, np.zeros((slm_width, slm_height), dtype=np.uint8))
        core.displaySLMImage(dmd_name)

        # Display the image
        fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4))
        # set fig1 at top left corner of the screen
        fig1.canvas.manager.window.move(0, 0)

        ax1.imshow(mask, cmap='gray')
        ax1.set_title('Original DMD Pattern')

        ax2.imshow(img, cmap='gray')
        ax2.set_title('Camera Image')
        fig1.show() # show the image!!!!!!!!

        # finds the corners of the checkerboard mask
        pattern_size = (cols-1, rows-1) # number of inner corners in the pattern (cols, rows) 12, 9 
        #print(os.getcwd()) # check the current directory
        dmd = cv2.imread("dmd_pattern.png", cv2.IMREAD_GRAYSCALE)
        ret_dmd, corners_dmd = cv2.findChessboardCorners(dmd, pattern_size)
        if ret_dmd:
                print("Checkerboard corners found in DMD image.", corners_dmd[:3])

        # finds the corners of the checkerboard image from camera
        camimg = cv2.imread("camera_image.png", cv2.IMREAD_GRAYSCALE)
        ret_camera, corners_camera = cv2.findChessboardCorners(camimg, pattern_size)
        if ret_camera:
                print("Checkerboard corners found in camera image.", corners_camera[:3])
        else:
                ctypes.windll.user32.MessageBoxW(0, "Set checkerboard", "Transform error", 1)
                print("NOT found Checkerboard corners in camera image.")

        if ret_dmd and ret_camera:
                corner_dm = corners_dmd[[1,4,10],:,:].squeeze()
                corner_cam = corners_camera[[1,4,10],:,:].squeeze()
                assert corner_dm.shape == (3, 2), "corner_dm does not have the correct shape."
                assert corner_cam.shape == (3, 2), "corner_cam does not have the correct shape."
                assert corner_dm.dtype == np.float32, "corner_dm does not have the correct data type."
                assert corner_cam.dtype == np.float32, "corner_cam does not have the correct data type."
                core.affine_transform = cv2.getAffineTransform(corner_cam, corner_dm) # transform from camera to dmd coordinates
                print("Affine transform: ", core.affine_transform)

                

                


                # Apply the transformation to visualize align image supposedly coming from the DMD
                transformed_image = cv2.warpAffine(camimg, core.affine_transform, (dmd.shape[1], dmd.shape[0]))
        else:
                print("No affine transform - validate focused checkerboard image in microscope view.")

        fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4))
        # set fig2 below fig1
        fig2.canvas.manager.window.move(0, 460)
        plt.subplot(1, 2, 1) # plot at the current figure
        plt.imshow(img, cmap='gray')
        plt.title('source Camera image')

        plt.subplot(1, 2, 2)
        plt.imshow(transformed_image, cmap='gray')
        plt.title('Camera rectangles transformed to DMD image')
        plt.show()

        if hasattr(core, 'affine_transform'):
               # save the affine transform matrix as .npy file upon user request
                reply = QMessageBox.question(gui,'NEW affine transform', 'Save the affine transform?', QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                        np.save("affine_transform.npy", core.affine_transform)
                
                else:
                        # QMessage notifing that the affine transform was not saved
                        ctypes.windll.user32.MessageBoxW(0, "Affine transform was not saved", "Transform neglected", 1)
                        print("Did not save affine transform")
               







def generate_compensated_checkerboard(rows, cols, square_width, square_height, target_width=912, target_height=1140):
        """
        Generate a checkerboard image with the specified number of rows, columns, and square dimensions.
        Pad the checkerboard so that it's centered within the target dimensions.
        """
        # Generate checkerboard
        pattern = np.zeros((rows * square_height, cols * square_width), dtype=np.uint8)
        for i in range(rows):
                for j in range(cols):
                        if (i + j) % 2 == 0:
                                pattern[i*square_height:(i+1)*square_height, j*square_width:(j+1)*square_width] = 255

        # Pad checkerboard
        height_padding = (target_height - pattern.shape[0]) // 2
        width_padding = (target_width - pattern.shape[1]) // 2

        pad_top = height_padding
        pad_bottom = target_height - pattern.shape[0] - pad_top
        pad_left = width_padding
        pad_right = target_width - pattern.shape[1] - pad_left

        return np.pad(pattern, ((pad_top, pad_bottom), (pad_left, pad_right)), mode='constant')        


def mouse_shoot(core):

        import matplotlib
        import matplotlib.pyplot as plt

        matplotlib.use("Qt5Agg")
        #plt.ion()

        class ClickCollector:
                def __init__(self):
                        self.fig, self.ax = plt.subplots()
                        self.fig.canvas.mpl_connect('button_press_event', self.onclick)
                        self.ax.plot([0, 1, 2], [0, 1, 2])

                def onclick(self, event):
                        print(f'x = {event.xdata}, y = {event.ydata}')

        collector = ClickCollector()
        plt.show()



class ClickCollectorsss():
    #matplotlib.use("Qt5Agg")
    plt.ion()  # Turn on interactive mode
#     plt.rcParams["backend"] = "module://ipympl.backend_nbagg"
    
    def __init__(self, core):
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(121)
        self.ax2 = self.fig.add_subplot(122)
        self.last_click = None
        self.last_rectangle = None  # Keep track of the last rectangle plotted
        self.core = core
    
    def mouse_click_image(self, xdata, ydata):
        # build an image with the clicked pixels
        new_image = np.zeros((self.core.camera_width, self.core.camera_height), dtype=np.uint8)
        new_image[int(xdata)-5:int(xdata)+5, int(ydata)-5:int(ydata)+5] = 255
        return new_image

    def onclick(self, event):
        # Record the click coordinates
        self.last_click = (event.xdata, event.ydata)
        print(f"You clicked at coordinates: {self.last_click}")

        # If there's a previous rectangle, remove it
        if self.last_rectangle:
            self.last_rectangle.remove()

        # Add a black rectangle around the click area
        rect = Rectangle((event.xdata - 5, event.ydata - 5), 10, 10, edgecolor='black', facecolor='black')
        self.ax.add_patch(rect)

        # Store this rectangle as the last rectangle
        self.last_rectangle = rect
        
        # Redraw the figure to show the rectangle
        plt.draw()

        # build an image with the clicked pixels
        click_image = self.mouse_click_image(event.ydata, event.xdata)

       # Transform the image to DMD coordinates using the affine transformation matrix
        
        transformed_img = cv2.warpAffine(click_image, self.core.affine_transform, (self.core.slm_width, self.core.slm_height))

        # Display the transformed image on the DMD
        self.core.setSLMImage(self.core.dmd_name, transformed_img)
        self.core.displaySLMImage(self.core.dmd_name)

        # take a picture with the camera
        self.core.snapImage()
        tagged_image = self.core.getTaggedImage()
        pixels = np.reshape(tagged_image.pix,
                    newshape=[tagged_image.tags['Height'], tagged_image.tags['Width']])
        # turn of the SLM pixels
        time.sleep(0.2)
        self.core.setSLMImage(self.core.dmd_name, np.zeros((self.core.slm_width, self.core.slm_height), dtype=np.uint8))
        self.core.displaySLMImage(self.core.dmd_name)
        time.sleep(0.2)
        # Display the image in ax2
        self.ax2.imshow(pixels, cmap='gray')

 

    def extract_data_from_ax(self):
        fig = self.ax.figure

        # Render the figure
        fig.canvas.draw()

        # Get the width and height of the figure in pixels
        w, h = fig.canvas.get_width_height()

        # Extract the RGB data from the figure
        buf = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)

        # Reshape the data into an (h, w, 3) array
        buf = buf.reshape(h, w, 3)

        # Convert RGB to grayscale using a weighted sum of R, G, and B channels
        grayscale = (0.2989 * buf[..., 0] + 0.5870 * buf[..., 1] + 0.1140 * buf[..., 2]).astype(np.uint8)

        return grayscale
    


