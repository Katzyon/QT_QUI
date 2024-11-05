# Started following button press on 'Stimulate all cells'. 
# It activate the DMD and project sequencialy single soma masks from the list self.binary_images


import numpy as np
from PySide6.QtCore import QThread, Signal, Slot

class SomaStimulationWorker(QThread):
    finishedStimulation = Signal()

    def __init__(self, gui, parent=None):
        super().__init__(parent)
        print("init SomaStimulationWorker")
        self.core = gui.core
        self.DMD_images = gui.DMD_images
        self.dmd_name = self.core.getSLMDevice()
        print("Core test - dmd name:", self.dmd_name)
        
        self.n_loops = 2
        self.current_loop = 0

    def run(self):
        print("run SomaStimulationWorker")
        self.stimulate_soma()

    def stimulate_soma(self):
        idx = 0

        print("current cell:", idx)
        # black_image = np.zeros((self.core.getSLMWidth(self.dmd_name),
        #                         self.core.getSLMHeight(self.dmd_name)), dtype=np.uint8)
        self.black_image = np.zeros((self.core.getSLMHeight(self.dmd_name),
                                 self.core.getSLMWidth(self.dmd_name)), dtype=np.uint8)
        # creat for loop to run over the n_loops and display each image in the DMD_images list
        for i in range(self.n_loops):
            for idx, image in enumerate(self.DMD_images):

                if idx < len(self.DMD_images) and self.current_loop < self.n_loops:
                    print("idx = ", idx, " current_loop = ", i+1, "of ", self.n_loops)
                    # Display next image
                    image = self.DMD_images[idx]
                    # print image min max values
                    print("image min:", image.min(), "image max:", image.max())

                    try:
                        # Attempt to set and display the SLM image
                        self.core.setSLMImage(self.dmd_name, image)
                        self.core.displaySLMImage(self.dmd_name)
                    except Exception as e:
                        print(f"Error occurred while setting or displaying SLM image: {e}")
                        # Handle the error appropriately, e.g., retry, skip, log, or terminate
                        break # Terminate the loop

                    self.msleep(200)
                    # QTimer.singleShot(500, self.update_display)  # 500 ms delay
                    

                else:
                    # After the last loop, present one image for x seconds
                    
                    self.display_single_image() # for testing

        self.clear_dmd()

    def display_single_image(self):
        # Send 1 stimulus to the DMD for 5 seconds
        self.core.setSLMImage(self.dmd_name, self.DMD_images[0])
        self.core.displaySLMImage(self.dmd_name)
        # Use QTimer.singleShot for a one-time delay
        # QTimer.singleShot(5000, self.clear_dmd)  #  QTimer kills the thread
        print("Single last image displayed")
        self.msleep(2000)

    #@Slot() #
    def clear_dmd(self):
        # Clear the DMD by projecting a black image
        
        self.core.setSLMImage(self.dmd_name, self.black_image)
        self.core.displaySLMImage(self.dmd_name)
        print("SomaStim clear DMD finished")
        self.finishedStimulation.emit()  # Signal that the process is complete





    


