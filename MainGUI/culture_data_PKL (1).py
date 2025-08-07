import os
import pickle

class Culture:
    """This class represents a culture. Called during main GUI initialization"""
    def __init__(self, date, directory):
        self.date = date
        self.protocols = [] # list of protocols
        #self.stages = []
        self.cellsNumber = 0
        self.directory = directory # directory where all culture data is saved
        self.somaMasks = None
        #self.transform_images = None
        #self.groupID = None # 
        self.image_dir = os.path.join(directory, "Images")  # Directory to save images
        self.save_directory = os.path.join(directory, "Culture")  # Directory to save the culture object
        self.protocols_directory = os.path.join(directory, "Protocols")  # Directory to save the protocols - copied from maingui.py 605
        self.current_protocol_dir = None

        # other folders:
        """ self.image_dir =  self.working_dir + "\\Images"
            print("Image dir: ", self.image_dir)
            self.DMD_dir = self.working_dir + "\\DMD"
            self.DMD_group_masks = self.working_dir + "\\DMD_Groups" """


    def save(self):
        """
        Saves the current culture object to a pickle file.
        """
        file_name = f"{self.date}.pkl"
        file_path = os.path.join(self.save_directory, file_name)
        with open(file_path, 'wb') as output:
            pickle.dump(self, output, pickle.HIGHEST_PROTOCOL)
        print(f"Culture object saved to {file_path}")
        
    
    def load(self, directory):
        """
        Loads a culture object from a pickle file in the specified directory.
        """
        file_name = f"{self.date}.pkl"
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'rb') as input_file:
            loaded_culture = pickle.load(input_file)
        print(f"Culture object loaded from {file_path}")
        return loaded_culture
    
    def save_protocol(self, protocol, protocol_index):
        """
        create a new folder Protcol + "index"
        """
        # Create a new folder for the protocol
        protocol_dir = os.path.join(self.protocols_directory, f"Protocol{protocol_index}")
        os.makedirs(protocol_dir, exist_ok=True)
        self.current_protocol_dir = protocol_dir
        file_name = f"Protocol{protocol_index}.pkl"
        file_path = os.path.join(protocol_dir, file_name)

        with open(file_path, 'wb') as output:
            pickle.dump(protocol, output, pickle.HIGHEST_PROTOCOL)
        print(f"protocol object saved to {file_path}")

        
                    
    def save_start_time(self, protocol_index, stage_index, start_time):
        """
        Save starting time to the specified stage (sequence).
        
        Parameters:
        - stage_index (int): Index of the stage in the `self.stages` list.
        - start_time (datetime or str): The time to append (datetime object or formatted string).
        """

        # Append the new start time
        self.protocols[protocol_index].stages[stage_index].start_run_time.append(start_time)
        print(f"Appended start time {start_time} to stage {stage_index}")

        # Save the entire list of starting times to .pkl file
        file_name = f"Stage{stage_index}_times.pkl"
        file_path = os.path.join(self.current_protocol_dir, file_name)
        with open(file_path, 'wb') as output:
            # Dump the entire list of start times
            pickle.dump(self.protocols[protocol_index].stages[stage_index].start_run_time, output, pickle.HIGHEST_PROTOCOL)
