from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QLabel, QVBoxLayout, QFormLayout, QFileDialog, QDateEdit
from datetime import datetime

class CultureInitDialog(QDialog):
    def __init__(self, default_directory=None):
        super().__init__()
        self.setWindowTitle("Initialize Culture")

        # Culture specific inputs
        self.culture_number_input = QLineEdit()
        self.culture_div_input = QLineEdit()

        # Subject specific inputs
        self.description_input = QLineEdit("Primary cortical culture")
        self.species_input = QLineEdit("Mouse")
        self.genotype_input = QLineEdit("WT")
        self.age_input = QLineEdit("E18")
        self.plating_date_input = QDateEdit()
        self.plating_date_input.setCalendarPopup(True)
        self.plating_date_input.setDateTime(datetime(2025, 3, 12))
        self.strain_input = QLineEdit("c57BL/6")

        # Directory chooser
        self.dir_button = QPushButton("Choose Directory")
        self.dir_label = QLabel(default_directory if default_directory else "No directory selected")
        self.selected_directory = default_directory  # Set the initial directory

        # Layout setup
        form_layout = QFormLayout()
        form_layout.addRow("Culture Number:", self.culture_number_input)
        form_layout.addRow("Description:", self.description_input)
        form_layout.addRow("Species:", self.species_input)
        form_layout.addRow("Genotype:", self.genotype_input)
        form_layout.addRow("Age:", self.age_input)
        form_layout.addRow("Plating Date:", self.plating_date_input)
        form_layout.addRow("Strain:", self.strain_input)
        form_layout.addRow(self.dir_button, self.dir_label)

        # Submit button
        self.submit_button = QPushButton("Create Culture")
        self.submit_button.clicked.connect(self.accept)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.submit_button)
        self.setLayout(layout)

        self.dir_button.clicked.connect(self.choose_directory)

    def choose_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Culture Directory", self.selected_directory)
        if directory:
            self.selected_directory = directory
            self.dir_label.setText(directory)

            
    def get_inputs(self):
        return {
            "culture_number": self.culture_number_input.text(),
            "directory": self.selected_directory,
            "subject_attributes": {
                "description": self.description_input.text(),
                "species": self.species_input.text(),
                "genotype": self.genotype_input.text(),
                "age": self.age_input.text(),
                "plating_date": self.plating_date_input.dateTime().toPython(),
                "strain": self.strain_input.text()
            }
        }

    def exec_and_get_inputs(self):
        if self.exec() == QDialog.Accepted:
            return self.get_inputs()
        return None
