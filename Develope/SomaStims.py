
from pycromanager import Core
import os
from time import sleep
import cv2
import numpy as np

# create the stims class
class Stims:
    def __init__(self, DMD_dir):
        self.core = Core(convert_camel_case=False)
        sleep(2)
        self.DMD_dir = DMD_dir


    def AllSomaStim(self):
        # get the micromanager core

        dmd_name = self.core.getSLMDevice()
        print("dmd_name:", dmd_name)
        sleep(2)
        # slm_width = core.getSLMWidth(dmd_name)
        # slm_height = core.getSLMHeight(dmd_name)

        # load all the images from the DMD_dir
        DMD_dir = self.DMD_dir
        DMD_images = []

        for file in os.listdir(DMD_dir):
            if file.endswith(".bmp"):
                # read the image and append
                image = cv2.imread(os.path.join(DMD_dir, file), cv2.IMREAD_GRAYSCALE)
                DMD_images.append(image)
                self.core.setSLMImage(dmd_name, image)
                self.core.displaySLMImage(dmd_name)
                print("image shape:", image.shape)
                print(file)
                sleep(0.5)


        # loop through all the images and display them on the DMD
        # for idx, image in enumerate(DMD_images):

        #     if idx < 10:
        #         # print("image shape:", image.shape)
        #         print(idx)
        #         print(image.dtype)
        #         print(image.size)
        #         self.core.setSLMImage(dmd_name, image)
        #         sleep(0.1)
        #         self.core.displaySLMImage(dmd_name)
        #         sleep(0.3)

        print("clear the last image")
        slm_width = self.core.getSLMWidth(dmd_name)
        slm_height = self.core.getSLMHeight(dmd_name)
        self.core.setSLMImage(dmd_name, np.zeros((slm_width, slm_height), dtype=np.uint8))
        self.core.displaySLMImage(dmd_name)

        print("Done projecting all the images")
        #self.core.unloadAllDevices()

# create the main
if __name__ == "__main__":
    # create the stims class
    # DMD_dir = r"D:\DATA\Patterns\Patt_2023-11-02\DMD"
    DMD_dir = r"D:\DATA\Patterns\Patt_2023-11-02\RectMov"
    stims = Stims(DMD_dir)
    
    stims.AllSomaStim()
    print("Done with the function")


