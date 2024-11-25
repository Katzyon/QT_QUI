from PySide6.QtCore import QThread, QTimer, Signal, Slot

class MyThread(QThread):
    stopTimerSignal = Signal()

    def __init__(self, interval, parent=None):
        super(MyThread, self).__init__(parent)
        self.interval = interval
        self.timer = None  # Initialize timer attribute
        self.stopTimerSignal.connect(self.stopTimer)

    def run(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.onTimeout)
        self.timer.start(self.interval)

        self.exec_()  # Start the event loop

    @Slot()
    def onTimeout(self):
        print("Timer ticked")

    @Slot()
    def stopTimer(self):
        if self.timer and self.timer.isActive():
            self.timer.stop()

    def requestStop(self):
        self.stopTimerSignal.emit()

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    thread = MyThread(1000)  # 1000 ms interval
    thread.start()

    # ... Your application logic here ...

    # Request to stop the timer
    thread.requestStop()
    thread.quit()
    thread.wait()

    sys.exit(app.exec())
