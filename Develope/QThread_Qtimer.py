# construct app
import os
import cv2
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QWidget

class SomaStimulationWorker(QThread):
    finishedStimulation = Signal()

    def __init__(self, DMD_images, parent=None):
        super().__init__(parent)
        print("init SomaStimulationWorker")
        
        self.timer = QTimer()
        self.DMD_images = DMD_images
        self.idx = 0
        self.n_loops = 2
        self.current_loop = 0

    def run(self):
        print("run SomaStimulationWorker")
        self.stimulate_soma()


    def stimulate_soma(self):    

        print("idx = ", self.idx, " current_loop = ", self.current_loop)

        # creat for loop to run over the n_loops and display each image in the DMD_images list
        for i in range(self.n_loops):
            # print current loop and image        
            for self.idx, image in enumerate(self.DMD_images):
                print("current loop:", i, " current image:", self.idx)
                if self.idx < 5:
                    
                    self.idx += 1
                    #self.msleep(200)
                    self.timer.singleShot(500, self.stimulate_soma)  # 500 ms delay

                    
                elif self.current_loop < self.n_loops:
                    self.idx = 0
                    print("loop index:", self.current_loop )
                    self.current_loop += 1

                    #self.msleep(200)
                    self.timer.singleShot(500, self.stimulate_soma)

                else:
                    self.display_single_image()
        self.clear_dmd()

    def display_single_image(self):
        print("display_single_image started")
        #self.msleep(2000)
        self.timer.singleShot(500, self.stimulate_soma)
        
        

    def clear_dmd(self):
        print("SomaStim clear DMD finished")
        self.finishedStimulation.emit()  # Signal that the process is complete
        sys.exit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    DMD_images = []
    DMD_dir = r"D:\DATA\Patterns\Patt_2023-11-09\DMD"
    DMD_files = os.listdir(DMD_dir)
    sorted_file_names = sorted(DMD_files, key=lambda x: int(x.split(".")[0]))

    # create the DMD_images array
    for filen in sorted_file_names:
        if filen.endswith(".bmp"):
            # read the image and append
            image = cv2.imread(os.path.join(DMD_dir, filen), cv2.IMREAD_GRAYSCALE)
            DMD_images.append(image)


    widget = SomaStimulationWorker(DMD_images)
    widget.run()
    sys.exit(app.exec())







    


