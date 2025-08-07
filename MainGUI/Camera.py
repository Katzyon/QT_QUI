# return an image from pycromanager Core object
import sys
#print(sys.path)
#from pycromanager import Core # need running Micro-Manager
import numpy as np
from PySide6.QtGui import QPixmap, QImage
from PIL import Image
import os

class getImage:  # called by init_window.py
    """Class to get an image from the camera using pycromanager Core object."""
    def __init__(self, core):
        super().__init__() # inherit from the parent class
    

        self.name = core.get_camera_device()
        self.exposure = core.get_exposure()
        trigmode = core.get_property(self.name, "TriggerMode")
        print(self.name, "Trigger mode: ", trigmode)
        fanspeed = core.get_property(self.name, "FanSpeedSetpoint")  # High, Medium, Low, Off (Liquid Cooled)
        print(self.name, "Fan speed: ", fanspeed)
        core.set_property(self.name, "FanSpeedSetpoint", "Low")
        ccd_temp = core.get_property(self.name, "CCDTemperature")
        print(self.name, "CCD Temperature: ", ccd_temp)
        self.binning = core.get_property(self.name, "Binning")
        core.set_property(self.name, "Binning", "2x2")
        print(self.name, "Binning: ", self.binning)
        core.set_property(self.name, "Exposure", 2)



    # print device properties
    def print_devices(core):
        # https://pycro-manager.readthedocs.io/en/latest/application_notebooks/pycro_manager_imjoy_tutorial.html
        #core = Core()
        devices = core.get_loaded_devices()
        devices = [devices.get(i) for i in range(devices.size())]
        print("getimage.print_device - devices: ", devices)


        exposure = core.get_exposure()
        print("getimage.print_device - Exposure (ms): ", exposure)
        trigmode = core.get_property("Camera-1", "TriggerMode")
        print("getimage.print_device - Trigger mode: ", trigmode)
        #init_devices(core)


    def snap_image(self,core):  # called by 
            #core = Core() # !!! create the core in the main GUI not here !!! just pass the core to this function
            core.snap_image()
            #self.core.snap_image()
            tagged_image = core.get_tagged_image() # tagged_image is a numpy array on 1D.
            # reshape the 1D array to 2D array
            pixels = np.reshape(tagged_image.pix,
                                newshape=[tagged_image.tags['Height'], tagged_image.tags['Width']]) # reshape the 1D array to 2D array
            #pixels = pixels.astype(np.uint8) # convert to uint8

            pixels = np.clip(pixels, 0, 255).astype(np.uint8)


            # Clip to remove outliers (optional but recommended)
            # low = np.percentile(pixels, 1)
            # high = np.percentile(pixels, 99.9)
            # pixels = np.clip(pixels, low, high)
            # pixels = ((pixels - low) / (high - low) * 255).astype(np.uint8)
            # qImg = QImage(pixels.data, pixels.shape[1], pixels.shape[0], QImage.Format_Grayscale8)
            # pixmap = QPixmap.fromImage(qImg) # Convert the QImage to a QPixmap
            return pixels
            

    def get_device_properties(self, core):
            
            #core = Core()
            devices = self.core.get_loaded_devices()
            devices = [devices.get(i) for i in range(devices.size())]
            device_items = []
            for device in devices:
                names = core.get_device_property_names(device)
                props = [names.get(i) for i in range(names.size())]
                property_items = []
                for prop in props:
                    value = core.get_property(device, prop)
                    is_read_only = core.is_property_read_only(device, prop)
                    if core.has_property_limits(device, prop):
                        lower = core.get_property_lower_limit(device, prop)
                        upper = core.get_property_upper_limit(device, prop)
                        allowed = {
                            "type": "range",
                            "min": lower,
                            "max": upper,
                            "readOnly": is_read_only,
                        }
                    else:
                        allowed = core.get_allowed_property_values(device, prop)
                        allowed = {
                            "type": "enum",
                            "options": [allowed.get(i) for i in range(allowed.size())],
                            "readOnly": is_read_only,
                        }
                    property_items.append(
                        {"device": device, "name": prop, "value": value, "allowed": allowed}
                    )
                    # print('===>', device, prop, value, allowed)
                if len(property_items) > 0:
                    device_items.append(
                        {
                            "name": device,
                            "value": "{} properties".format(len(props)),
                            "items": property_items,
                        }
                    )
            print(device_items)

    def averageImages(self, core, num_images):
        # running average num_images images and return the average image
        for i in range(num_images):
            frame = self.snap_image(core)
            if i == 0:
                sum_frame = frame
            else:
                sum_frame = (sum_frame + frame)/ (i+1) # each image is weighted by 1/(i+1) to get a sum of 1
                
        
        print("average done!")
        return sum_frame

    def saveImage(self, image, image_dir):
         # save the image to the image_dir

        # Normalize to [0, 255]
        normalized_array = ((image - image.min()) * (1/(image.max() - image.min()) * 255)).astype('uint8')
        # Convert back to PIL Image
        normalized_image = Image.fromarray(normalized_array)
        print("image saved to: ", image_dir)
        # save the image im in image_dir as tiff
        normalized_image.save(image_dir + "/image.tif")



    def init_devices(self):
        # set the camera trigger to Edge Trigger
        
        self.core.set_property("Camera-1", "TriggerMode", "Edge Trigger")
        # print the camera trigger mode
        trigmode = self.core.get_property("Camera-1", "TriggerMode")
        print("getimage.init_devices - Trigger mode: ", trigmode)


