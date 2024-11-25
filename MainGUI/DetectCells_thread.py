
from PySide6.QtCore import QThread, Signal
import numpy as np
import threading
import time
import sys


class CellposeWorker(QThread):

    # Signal to notify when cellpose processing is done
    finishedProcessing = Signal()
    updatePlot = Signal(np.ndarray, np.ndarray, np.ndarray) # create a signal that sends the model output to main GUI thread

    # init the thread and get input image
    def __init__(self, img_array, diameter=13):
        super().__init__()
        self.img_array = img_array
        self.diameter = diameter
        print("CellposeWorker initialized")
    

    def run(self):
        # Your cellpose function call goes here
        print("Running cellpose...")
        self.run_cellpose()
        self.finishedProcessing.emit() # Notify GUI thread that processing is done


    def run_cellpose(self):
        print("Internal Running ")
        # Import cellpose and related modules here
        # to ensure they are only used in this thread
        from cellpose import models
        
        img_array = (self.img_array - np.min(self.img_array)) / np.ptp(self.img_array) * 255
        img_array = img_array.astype(np.uint8)

        
        # Initialize the cellpose model for cyto (soma) detection
        model = models.Cellpose(gpu=False, model_type='cyto')

        # Run the model on the image
        masks, flows, styles, diams = model.eval(img_array, diameter=self.diameter, channels=[0,0])
        print("Shape of flows[0]:", flows[0].shape)
        print("Shape of flows[1]:", flows[1].shape)


        #flow_magnitude = np.sqrt(flows[0]**2 + flows[1]**2)
        flow_magnitude = np.sqrt(flows[0][..., 0]**2 + flows[0][..., 1]**2)
        self.updatePlot.emit(img_array, masks, flow_magnitude) # Send model output to main GUI thread

    


