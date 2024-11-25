# An example of using QTimer within a QThread to run timers in parallel

from PySide6.QtCore import QThread, QTimer, QEventLoop, Signal, Slot

t1 = 100
t2 = 300

class WorkerThread(QThread):
    finished = Signal()

    def __init__(self, parent=None):
        super(WorkerThread, self).__init__(parent)
        self.iteration = 0
        self.max_iterations = 4

    def run(self):
        # Timer 1
        self.timer1 = QTimer()
        self.timer1.timeout.connect(self.on_timeout1)
        self.timer1.start(t1)

        # Timer 2
        self.timer2 = QTimer()
        self.timer2.timeout.connect(self.on_timeout2)
        self.timer2.start(t2)

        # 
        while self.iteration < self.max_iterations:
            #print("Iteration:", self.iteration)
            loop = QEventLoop()
            # check the loop every 100 ms - set this time to be longer than the sum of the two timers X by the number of iterations - so it won't check too often
            Ttest = (t1 + t2)*self.max_iterations + 100
            QTimer.singleShot(Ttest, loop.quit)  # Check every 100 ms
            loop.exec()


        # Stop timers when max iterations reached
        self.stop_timers()


    def on_timeout1(self):
        print("Timer 1 triggered.")

    def on_timeout2(self):
        self.iteration += 1
        print("Timer 2 triggered.")

    def stop_timers(self):
        self.timer1.stop()
        self.timer2.stop()

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    # close the app when timers finish running
    def on_thread_finished():
        print("Thread finished, exiting application.")
        app.quit()

    app = QApplication(sys.argv)
    thread = WorkerThread()
    thread.finished.connect(on_thread_finished) # connect the thread finished signal to the on_thread_finished function
    thread.start()
    sys.exit(app.exec())
