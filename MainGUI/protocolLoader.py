

import os
from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QVBoxLayout, QMessageBox, QPushButton

from PySide6.QtCore import Slot, Signal
import pandas as pd

class ProtocolLoader(QDialog):
    """ open a dialog to load a protocol csv file"""

    signalOutData = Signal(object) # signal to send the dataframe to the main window

    def __init__(self, parent=None):
        super(ProtocolLoader, self).__init__(parent)
        self.setWindowTitle("CSV File Loader")
        self.setGeometry(100, 100, 400, 300)

        self.layout = QVBoxLayout(self)

        # List widget to display file names
        self.listWidget = QListWidget(self)
        self.layout.addWidget(self.listWidget)
        #self.listWidget.clicked.connect(self.loadFile)

        # add a button to load the selected file
        self.loadButton = QPushButton("Load Protocol", self)
        self.layout.addWidget(self.loadButton)
        self.loadButton.clicked.connect(self.loadFile)

        # add a button to edit the selected csv file
        self.editButton = QPushButton("Edit Protocol", self)
        self.layout.addWidget(self.editButton)
        self.editButton.clicked.connect(self.editFile)


        # Populate the list with CSV files
        self.populateList()

    def populateList(self):
        directory = r"G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Protocols"
        for filename in os.listdir(directory):
            if filename.endswith(".csv"):
                self.listWidget.addItem(filename)

    @Slot() # use to act following - self.listWidget.clicked.connect(self.loadFile) click
    def loadFile(self):
        """Load the selected file into a dataframe and emit the signal to the main window"""

        selected_item = self.listWidget.currentItem()
        # if selected_item:
        file_name = selected_item.text()
        file_path = os.path.join(r"G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Protocols", file_name)
        #     # Here you can add the logic to handle the file loading
        #     QMessageBox.information(self, "File Selected", f"You selected: {file_path}")

        # read the csv data into a dataframe
        self.protocol = pd.read_csv(file_path)

        # return the dataframe to the main window with the signal emit
        self.signalOutData.emit(self.protocol)

        # close the dialog
        self.close()

    def editFile(self):
        """Edit the selected file"""
        selected_item = self.listWidget.currentItem()
        file_name = selected_item.text()
        file_path = os.path.join(r"G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Protocols", file_name)
        os.system(f"notepad {file_path}")

if __name__ == "__main__":
    app = QApplication([])
    dialog = ProtocolLoader()
    dialog.show()
    app.exec()
