# Started following button press on 'Stimulate all cells'. 
# It activate the DMD and project sequencialy single soma masks from the list self.binary_images


import numpy as np
from PySide6.QtCore import QThread, Signal, QTimer, Slot

class SomaStimulationWorker(QThread):
    finishedStimulation = Signal()

    def __init__(self, gui, parent=None):
        super().__init__(parent)
        print("init SomaStimulationWorker")
        self.timer = QTimer()
        self.timer.timeout.connect(self._stimulate_step)
        self.idx = 0
        self.current_loop = 0

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
        self.timer.start(200)  # Set timer to 200 ms

    def _stimulate_step(self):
        

        if self.idx < len(self.DMD_images) and self.current_loop < self.n_loops:
            print("idx =", self.idx, "current_loop =", self.current_loop + 1, "of", self.n_loops)

            # Display next image
            image = self.DMD_images[self.idx]
            print("image min:", image.min(), "image max:", image.max())

            try:
                # set and display the SLM image
                self.core.setSLMImage(self.dmd_name, image)
                self.core.displaySLMImage(self.dmd_name)
            except Exception as e:
                print(f"Error occurred while setting or displaying SLM image: {e}")
                self.timer.stop()  # Stop the timer
                # Handle the error appropriately
                return

            # Increment the index and loop count
            self.idx += 1
            if self.idx >= len(self.DMD_images):
                self.idx = 0
                self.current_loop += 1
                if self.current_loop >= self.n_loops:
                    self.clear_dmd()
                    self.timer.stop()  # Stop the timer when all loops
                    
                    #self.display_single_image() # for testing

        

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
