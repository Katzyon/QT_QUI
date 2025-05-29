# A thread for movie acquisition and display
# While running, it grabs a frame from the camera and displays it in the imageview widget


from PySide6.QtCore import QThread,  Signal, Slot
import time

class MovieThread(QThread):
    # use of thread example
    # https://stackoverflow.com/questions/16879971/example-of-the-right-way-to-use-qthread-in-pyqt
    frame_ready = Signal(object)  # Signal to indicate a new frame is ready

    def __init__(self, MainGUI):
        super().__init__()
        self.MainGUI = MainGUI
        self.is_running = True
        self.frame_ready.connect(self.update_imageview)  # Connect the signal to the slot   

    def run(self):
        #self.camera.acquire_movie(8)
        #print("MovieThread run")
        
        while self.is_running:
            frame = self.MainGUI.camera.snap_image(self.MainGUI.core)
            self.frame_ready.emit(frame)  # Emit the signal with the new frame
            self.msleep(100)  # Sleep for 100 ms (equivalent to 0.1 seconds)

    @Slot(object)
    def update_imageview(self, frame):
        self.MainGUI.imageview.setImage(frame)

    # stop the movie thread
    def stop(self):
        self.is_running = False
        self.wait()  # Wait for the thread to finish cleanly
        #self.terminate() # terminate the thread
        #print("MovieThread stopped")

    