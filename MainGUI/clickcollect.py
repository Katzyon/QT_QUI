import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QPixmap, QImage
import numpy as np
import cv2
import time
import Display_image as di

# ImageLabel class is used to display the user clicks on the image and produce corresponding DMD images
class ImageLabel(QLabel):
    """A QLabel that can display a the user click on the image
    It produces corresponding image to light stimulate the selected point ."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_point = None
        #self.move(50, 50)
    
    def set_current_point(self, point):
        self.current_point = point
        self.update()  # Ask the label to redraw itself
        
    def paintEvent(self, event):
        super().paintEvent(event)  # Let QLabel handle its default rendering
        
        if self.current_point:
            with QPainter(self) as painter:
                pen = QPen(Qt.red, 6)
                painter.setPen(pen)
                painter.drawPoint(self.current_point[0], self.current_point[1])

class ClickCollector(QWidget):
    def __init__(self, gui):
        super().__init__()

        self.gui = gui
        # get the camera image and convert it to QImage
        base_image = self.camImage_to_QImage(gui.frame)
        self.current_point = (0,0)

        self.background_image = QPixmap(base_image)
        # create panel in the window
        self.panel = ImageLabel(self)
        
        # set the background image in the left panel
        self.panel.setPixmap(self.background_image)
        #self.right_image_label.setPixmap(self.background_image)
        
        # resize the left panel to the background image size
        self.panel.resize(self.background_image.size())
        #self.right_image_label.resize(self.background_image.size())
        
        # set the ImageLabel to be the central widget
        #self.setCentralWidget(self.left_image_label)


        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Click Collector')
        self.move(50, 50)
        
        
    def mousePressEvent(self, event):
        # Only handle clicks within the left QLabel
        
        core = self.gui.core
        dmd_name = core.getSLMDevice()
        slm_width = core.getSLMWidth(dmd_name)
        slm_height = core.getSLMHeight(dmd_name)
        
        
        self.gui.affine_transform = self.gui.affine_trans_old

        self.panel.set_current_point((event.x(), event.y()))
        #print(f"Mouse clicked on left figure at: {x}, {y}")

        # build an image with the clicked pixels
        new_image = self.mouse_click_image(event.y(), event.x()) # x and y are switched because the image is rotated (?)
        # Transform the image to DMD coordinates using the affine transformation matrix - self.affine_transform
        transformed_img = cv2.warpAffine(new_image, self.gui.affine_transform, (slm_width, slm_height))
        
        # set the image at the DMD
        #print(transformed_img.shape)
        core.setSLMImage(dmd_name, transformed_img)
        core.displaySLMImage(dmd_name)

        # take a picture with the camera
        core.snapImage()
        tagged_image = core.getTaggedImage()
        pixels = np.reshape(tagged_image.pix,
                    newshape=[tagged_image.tags['Height'], tagged_image.tags['Width']])
        # turn off the SLM pixels
        time.sleep(0.1)
        core.setSLMImage(dmd_name, np.zeros((slm_width, slm_height), dtype=np.uint8))
        core.displaySLMImage(dmd_name)
        time.sleep(0.2)

        # display the camera image using Display_image.py
        di.display_image(pixels,"cam_image") # display the image in a new window the second argument is the figure identifier


        # update the right figure with the camera image
        #self.right_image_label.setPixmap(QPixmap.fromImage(self.camImage_to_QImage(pixels)))


    # black image with white pixels where the user clicked
    def mouse_click_image(self, xdata, ydata):
        # build an image with the clicked pixels
        camera_width = self.gui.core.getImageWidth()
        camera_height = self.gui.core.getImageHeight()
        new_image = np.zeros((camera_width, camera_height), dtype=np.uint8)
        new_image[int(xdata)-5:int(xdata)+5, int(ydata)-5:int(ydata)+5] = 255
        print("Clicked at: ", xdata, ydata)
        return new_image

    # convert camera image to QImage    
    def camImage_to_QImage(self, frame):
        height, width = frame.shape
        bytes_per_line = width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        return q_img

    
