import os
import sys
from PySide6.QtWidgets import QApplication

import pickle  # Only kept for legacy loading if needed
from datetime import datetime, timezone

from pynwb import NWBFile, NWBHDF5IO
from pynwb.file import Subject
from culture_dialog import CultureInitDialog

# import pandas as pd
# import numpy as np
# import h5py

class Culture:
    """This class represents a culture, storing data in NWB format.
    It is referred as self.culture in the maingui.
    The protocols are stored in a list of Protocol objects."""
    
    def __init__(self, directory):
        self.date = None
        #self.protocols = []  # List of protocols
        self.protocols_number = 0  # Number of protocols - updated by runProtocol.py
        self.cellsNumber = 0 # updated by save_masks in maingui.py
        self.directory = directory  # Main directory for culture data (chip number= single culture)
        self.culture_dir = os.path.join(directory, "Culture")  # Directory for culture data
        self.subject = None

        # Define directories
        self.image_dir = os.path.join(directory, "Images")  
        #self.save_directory = os.path.join(directory, "Culture")  
        self.protocols_directory = os.path.join(directory, "Protocols")  
        self.current_protocol_dir = None

        self.initialize_new_culture()

    def initialize_new_culture(self):
        # gui dialog for culture initialization by the user
        # This function is called once when the culture is created from the main GUI
        #app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        dialog = CultureInitDialog(self.directory)
        result = dialog.exec_and_get_inputs()
        if result:
            culture_number = int(result['culture_number'])
            directory = result['directory']
            subject_attrs = result['subject_attributes']

            culture_div = (datetime.now() - subject_attrs['plating_date']).days
            print(f"Culture DIV: {culture_div}")
            culture_id = f"culture_{culture_number}_DIV{culture_div}"

            self.subject = Subject(
                subject_id=culture_id,
                description=subject_attrs['description'],
                species=subject_attrs['species'],
                genotype=subject_attrs['genotype'],
                age=subject_attrs['age'],
                date_of_birth=subject_attrs['plating_date'],
                strain=subject_attrs['strain']
            )
            # calculate the DIV from the plating_date and the current date
            #current date - plating_date = culture_div
            
            
            print(f"Initialized culture with directory: {result['directory']}")
            self.save()
        else:
            print("Culture initialization canceled.")

        
        # # Initialize NWB File
        # self.nwbfile = NWBFile(
        #     session_description="Patterns culture data",
        #     identifier=f"Culture_{self.date}",
        #     session_start_time=datetime.now(timezone.utc),
        #     subject=self.subject
        # )
        # # print the NWBFile object
        # print(self.nwbfile) 
        
    
    def save(self): # called by the main GUI to save the culture object
        """
        Saves the current Culture object to a Pickle (.pkl) file.
        """
        print("Saving culture object...")
        

        self.date = datetime.now().strftime("%Y-%m-%d_%H-%M")  # Update date to current time
        file_name = f"culture_{self.date}.pkl"
        file_path = os.path.join(self.culture_dir, file_name)

        try:
        # Attempt to open the file and dump the object
            with open(file_path, 'wb') as f:
                pickle.dump(self, f)  # saving self object = the culture object
            print(f"Culture object saved to {file_path}")
        except (IOError, pickle.PickleError) as e:
            # Handle I/O errors or pickle errors during the saving process
            print(f"Failed to save the culture object to {file_path}. Error: {e}")
        except Exception as e:
            # Handle any other unforeseen exceptions
            print(f"An unexpected error occurred while saving the culture object: {e}")

    def load(self, directory): # called by the main GUI to load the culture object
        """
        Loads a culture object from an NWB file.
        """

        file_name = f"{self.date}.pkl"
        file_path = os.path.join(directory, file_name)

        with open(file_path, 'rb') as f:
            culture = pickle.load(f)

        print(f"Culture object loaded from {file_path}")
        return culture
    
    # def save_protocol(self): # called by runProtocol in Protocol.py
    #     """
    #     Saves the current protocol object using Pickle (.pkl).
    #     Called once by runProtocol() and initializes the storage for this protocol.
    #     """
    #     # Create directory for this protocol
    #     self.current_protocol_dir = os.path.join(self.protocols_directory, f"Protocol_{self.protocols_number}")
    #     os.makedirs(self.current_protocol_dir, exist_ok=True)   

    #     # Build filename
    #     file_name = f"protocol_{self.protocols_number}.pkl"
    #     file_path = os.path.join(self.current_protocol_dir, file_name)

    #     try:
    #     # Open the file and dump only the declared attributes of self
    #         with open(file_path, 'wb') as culture_file:
    #             # Filter self.__dict__ to only save declared attributes
    #             #data_to_save = {k: v for k, v in self.__dict__.items() if not k.startswith('__') and not callable(v)}
    #             pickle.dump(self, culture_file)
    #         print(f"Culture with protocol {self.protocols_number} saved to '{file_path}'")
    #     except Exception as e:
    #         # Handle exceptions related to file access or pickling errors
    #         print(f"Failed to save the culture with protocol {self.protocols_number}. Error: {e}")
        

    
    
    # def save_sequence(self, index, sequence):
    #     """
    #     Save the sequence of a specific stage within a protocol.
    #     This function save the sequence to a pkl file.
    #     called by the runProtocol function
    #     """
        
    #     file_name = f'sequence_{index}.pkl' 
    #     data = {'index': index, 'protocol_number': self.protocols_number, 'sequence': sequence}
                
    #     with open(os.path.join(self.current_protocol_dir, file_name), 'wb') as file:
    #         pickle.dump(data, file)

        
        

    def save_attributes(nwbfile, obj, group_name):
        for attr, value in obj.__dict__.items():
            if isinstance(value, (int, float, str)):
                nwbfile.add_lab_meta_data({group_name: {attr: value}})
            elif isinstance(value, list):
                nwbfile.add_lab_meta_data({group_name: {attr: value}})
    
if __name__ == "__main__":
    culture = Culture(date=datetime.now(), directory=r"D:\DATA\Patterns")
