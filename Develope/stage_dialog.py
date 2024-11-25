# StageDialog class enable the user to set the parameters of the protocol
# called by protocol_design.py 


from PySide6.QtWidgets import QDialog, QVBoxLayout, QComboBox, QLineEdit, QDialogButtonBox

class StageDialog(QDialog):
    def __init__(self, parent=None):
        super(StageDialog, self).__init__(parent)
        
        self.layout = QVBoxLayout(self)

        # Dropdown for type of stimulation
        self.stimulation_type = QComboBox()
        self.stimulation_type.addItems(["Type 1", "Type 2", "Type 3"])
        self.layout.addWidget(self.stimulation_type)

        # Input for frequency
        self.frequency = QLineEdit()
        self.layout.addWidget(self.frequency)

        # Input for group size
        self.group_size = QLineEdit()
        self.layout.addWidget(self.group_size)

        # Other parameters...

        # Dialog button box
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

    def get_stage_data(self):
        # Method to retrieve data from the dialog fields
        return {
            "stimulation_type": self.stimulation_type.currentText(),
            "frequency": self.frequency.text(),
            "group_size": self.group_size.text(),
            # Other parameters...
        }

