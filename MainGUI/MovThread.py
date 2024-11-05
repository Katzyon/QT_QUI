# A thread for movie acquisition and display
# While running, it grabs a frame from the camera and displays it in the imageview widget


from PySide6.QtCore import QThread
import time

class MovieThread(QThread):
    # use of thread example
    # https://stackoverflow.com/questions/16879971/example-of-the-right-way-to-use-qthread-in-pyqt
    def __init__(self, MainGUI):
        super().__init__()
        # self.camera = MainGUI.camera
        # self.imageview = MainGUI.imageview
        # self.core = MainGUI.core
        self.MainGUI = MainGUI
        self.is_running = True   

    def run(self):
        #self.camera.acquire_movie(8)
        #print("MovieThread run")
        
        while self.is_running:
            frame = self.MainGUI.camera.snapImage(self.MainGUI.core)
            self.MainGUI.imageview.setImage(frame)
            time.sleep(0.1) # Why 0.1? cause it works

    # stop the movie thread
    def stop(self):
        self.is_running = False
        #self.terminate() # terminate the thread
        #print("MovieThread stopped")

    