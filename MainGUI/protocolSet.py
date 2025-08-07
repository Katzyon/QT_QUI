


# protocolSet class for setting the protocol parameters before running it
# activated following the "Load Protocol" button in the main window
# It create_stimulation_sequence which is the sequence of images to be displayed on the DMD (self.bridge._construct_java_object)
#
#from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QVBoxLayout, QMessageBox, QPushButton
#from PySide6.QtCore import Slot, Signal, QThread
import pandas as pd
import random
from Protocol import Stage
import ast
import pickle
import os


class ProtocolSet():
        """ Class for setting the protocol parameters before running it"""
    
    
        def __init__(self, gui):
            super(ProtocolSet, self).__init__()
            self.stages_table = gui.stages_table # dataframe of the protocol
            self.manual_sequence = gui.manual_sequence # list of manually selected groups
            self.manual_groups = gui.manualGroups # list of manually selected groups
            self.images = gui.soma_masks # list of images of the cells somata
            #self.bridge = gui.core._get_bridge() # get the Java bridge to create Java SLM sequence (JavaObject)
            #self.sequences = [] # list of lists of the sequence of image INDICES to be displayed on the DMD
            self.stages = []   # list of the stages in the protocol - each stage is a Protocol object. 
            self.n_rows = 0 # number of stages in the protocol
            # protocol saving directory
            self.protocols_directory = gui.protocols_directory # directory for saving the protocol
            self.current_protocol_dir = gui.culture.current_protocol_dir # current protocol directory
            self.protocols_number = gui.culture.protocols_number # number of the current protocol
            
            print("init protocol set", self.current_protocol_dir)

        # def __getstate__(self): # called when pickling the ProtocolSet object by the pickle module
        #     # exclude the bridge attribute from pickling
        #     state = self.__dict__.copy()
        #     # Remove the bridge attribute before pickling
        #     if 'bridge' in state:
        #         del state['bridge']
        #     if 'images' in state:
        #         del state['images']
        #     # Handle nested Stage objects
        #     #state['stages'] = [stage.__getstate__() for stage in self.stages]
        #     return state
              

        def extract_protocol(self): # called from maingui.py following the "Load Protocol" button
            """ Extract the protocol from the dataframe before setting it. Called from maingui.py following the "Load Protocol" button"""

            """Extract and set up the protocol from a DataFrame, initiated from a GUI."""
            self.headers = list(self.stages_table.columns)
            self.data = self.stages_table.values.tolist()
            print("protocolSet - data:", self.data)
            self.n_rows = len(self.data)
            self.number_cells = len(self.images)

            for index, row in self.stages_table.iterrows():
                print(f"stage number: {index}, row: \n{row}")
                stage = self._create_stage_from_row(row, index)
                self.stages.append(stage)
                print(f"protocolSet output group: {stage.output_group}")
                print(f"protocolSet- sequence: {stage.sequence}")
                print(f"stage num: {index + 1}; repeats: {stage.sequence_repeats}")

            
        def _create_stage_from_row(self, row, index): # called by extract_protocol
            """Helper function to create and configure a Stage object from a DataFrame row."""
            stage = Stage(self.images) # call the Stage from Protocol.py
            stage.number = index + 1

            # Set attributes from the row
            stage.stim_type = row['stim_type']
            stage.group_size = int(row['group_size'])
            stage.groups_number = int(row['groups_number'])
            stage.number_cells = self.number_cells
            stage.groups_period = int(row['groups_period'])
            stage.is_manual = row['is_manual_sequence']
            stage.is_probability_stim = row['prob_stim']
            stage.output_group = ast.literal_eval(row['output_group'])
            stage.background_freq = float(row['background_freq'])
            stage.on_time = int(row['on_time'])
            stage.background_on_time = 5
            stage.stim_time = int(row['stim_time'])
            stage.cycle_time = stage.groups_period
            # set the recording flag from the boolean checkbox in the GUI 
            stage.recording = bool(row['record_stage'])


            print("P_set number of groups:", stage.groups_number)

            if stage.is_manual:
                # If manual sequence is selected, use the manual_sequence from the GUI
                #stage.sequence = self.manual_sequence # manual sequence ??? 
                stage.groups = self.manual_groups
                stage.groups_number = len(stage.groups) # number of groups in the manual sequence
                

            stage.create_sequence() # 
            stage.calc_interMaskInterval()
            return stage     


                # get the stimulation type (stimType)
                
                # (0, "Random") - randomize the sequence every iteration
                # (1,"Group only stim.") - stimulate only the groups in the sequence (no single cells/remaining cells)
                # (2, "Order") - repeat the same sequence over and over
                # (3, "Test") - run the sequence under calcium imaging
                # (4, "Spontaneous") - randomize stimulation to all cells in the culture (no groups)
                #print("stimType:", stage.stimType)

        def save_protocol(self, protocols_number):
            """ Save the protocol to a pickle file. """

            # Create directory for this protocol
            self.current_protocol_dir = os.path.join(self.protocols_directory, f"Protocol_{protocols_number}")
            os.makedirs(self.current_protocol_dir, exist_ok=True)


            # Save the current protocol object (which includes the selected protocol)
            file_name = f"protocol_{protocols_number}.pkl"
            file_path = os.path.join(self.current_protocol_dir, file_name)
            with open(file_path, 'wb') as culture_file:
                pickle.dump(self, culture_file)
            print(f"Protocol {protocols_number} saved to '{file_path}'")


        def save_sequence(self, index, sequence,start_time):
            """
            Save the sequence of a specific stage within a protocol.
            This function save the sequence to a pkl file.
            called by the runProtocol function
            """
            print("In save_sequence :index", index)


            file_name = f'sequence_{index}.pkl' 
            data = {'index': index, 
                    'protocol_number': self.protocols_number, 
                    'sequence': sequence,
                    'start_time': start_time,
            }
                    
            # Attempt to save the data to a file
            try:
                with open(os.path.join(self.current_protocol_dir, file_name), 'wb') as file:
                    pickle.dump(data, file)
                print(f"Sequence data saved successfully to {file_name}")
            except FileNotFoundError:
                # Handle the case where the directory does not exist
                print(f"Error: Directory '{self.current_protocol_dir}' does not exist.")
            except IOError as e:
                # Handle general input/output errors
                print(f"IOError when attempting to save the file: {e}")
            except pickle.PickleError as e:
                # Handle errors specifically related to the pickling process
                print(f"Pickle error: {e}")
            except Exception as e:
                # Handle any other unexpected errors
                print(f"An unexpected error occurred: {e}")

        def save_start_time(self, stage_index, start_time):
            """
            Save starting time of a specific stage within a protocol.
            This function appends the start time to a CSV log file.
            called by the runProtocol function
            """
            print("In save_start_time :", start_time)

            # create file name with the stage_index included
            LOG_FILE = f'Stage_startT_{stage_index}.csv'

            # Convert to DataFrame for structured saving
            new_entry = pd.DataFrame([{
                'time': start_time,
                'stage_index': stage_index,
                'protocol_index': self.protocols_number
            }])

            # Append to CSV file
            filepath = os.path.join(self.current_protocol_dir, LOG_FILE)    
            if not os.path.exists(filepath):
                new_entry.to_csv(filepath, index=False)
            else:
                new_entry.to_csv(filepath, mode='a', header=False, index=False)

            
            print(f"Saved start time {start_time} for Protocol {self.protocols_number}, Stage {stage_index}.")
                    


            
    # create the image index for the protocol sequence
        # def create_stimulation_sequence(self): # called by handleLoadedData in maingui.py following the "Load Protocol" button
        #     """
            
        #     create sequence of images to be displayed on the DMD depending on the protocol type and parameters
        #     The sequence is based on the self.sequence list of lists where each list is a group of cells or a single cell
        #     if the list is longer than 1, it sum the images in the list (each image stand for single soma. When summing is will be a group of somas)
        #     Create self.sequences_images which is the sequence of images to be displayed on the DMD
        #     """

        #     if self.stim_type == 'Random':
        #         cs.create_random_sequence(self)
        #     elif self.stim_type == 'Sequential':
        #         cs.create_sequential_sequence(self)
        #     else:
        #         print(f"Error: Unsupported stimulation type '{self.stim_type}'. Please use 'Random' or 'Sequential'.")


        #     # create the sequence of images to be displayed on the DMD
        #     self.sequences_images = []
            
        #     for idx, stage in enumerate(self.sequences): # iterate over the stages in the protocol to create groups' masks
        #         #print("idx", idx)


        #         # TODO:
        #         # IF probability stimulation is checked - create a distribution of the groups according to the number of groups
        #         # Add black image at the end of the sequence
        #         # self.black_image = np.zeros((self.core.getSLMHeight(self.dmd_name),
        #         #             self.core.getSLMWidth(self.dmd_name)), dtype=np.uint8)
        #         #javaarray = self.bridge._construct_java_object('java.util.ArrayList') # create a Java array list - each row is a vectorized image
        #         #self.DMDArray = javaarray  # Store the Java ArrayList for the current stage
        #         sequence_images = []
        #         group_sum = []

        #         for group in stage: # group is a list of cells either of size 1 or larger
        #             group_images = []
        #             for cell in group: # [1, 3, 11] - list of cells in the group
        #                 group_images.append(self.images[cell - 1])

        #             # sum the images in the group
        #             group_sum = sum(group_images) # sum the images in the group - is stimulation to a group of cells
        #             sequence_images.append(group_sum) # add one image to the sequence

        #             self.stages[idx].DMDArray.add(group_sum.ravel()) # add the image to the Java array 
        #             #self.DMDArray.append(group_sum.ravel()) # add the image to the Java array - used.add didn't work
        #             #print("num of images in DMArray", len(self.DMDArray[idx]))


        #             #print("group type", type(group_sum))
        #             #group_sum_ravel = group_sum.ravel()  # Flatten the image (if needed)
        #             #print("to_lsit type", type(group_sum_ravel.tolist()))


        #             # print("Number of images in DMDArray:", self.DMDArray[idx].size())
        #             # print("n images in sum", len(group_sum))
        #             #print(f"Number of images in DMDArray[{idx}]:", javaarray.size())
        #             #print(f"Size of group_sum (flattened): {len(group_sum_ravel)}")

        #         self.sequences_images.append(sequence_images) # add one sequence to the list of sequences. Use for testing (plot) and group verification
        #         # Debugging outputs
        #         print(f"Stage {idx}: Sequence {stage}, Number of groups: {len(stage)}")


        #     # print the number of sequences in the protocol
        #     print(f"Number of sequences in the protocol: {len(self.sequences_images)} (create_stimulation_sequence)")

            

        #     # print all attributes of self.prot object
        #     # for attr, value in vars(self.stages).items():
        #     #     print(f"{attr} = {value}")


        #     # plot the sequence of images for testing - each panel is a group of cells (or a single cell)
        #     import matplotlib.pyplot as plt
            

        #     # plot the groups (of the DMDArray) in the stages 
        #     for stage, sequence_images in enumerate(self.sequences_images, start=1):
        #         fig, axes = plt.subplots(1, len(sequence_images), figsize=(15, 5))
        #         for i, image in enumerate(sequence_images):
        #             axes[i].imshow(image, cmap='gray')
        #             axes[i].set_title(f"Group {i}") 
        #         plt.show()


        # def create_random_groups(self, numberCells, groupsNumber, group_size):
        #     # called by handleLoadedData in maingui.py
        #     # Check if the total number of required group members exceeds the numberCells
        #     if groupsNumber * group_size > numberCells:
        #         raise ValueError("Not enough cells to create the required number of groups without repeats")

        #     all_cells = list(range(1, numberCells + 1))
        #     self.groups = []

        #     for _ in range(groupsNumber):
        #         group = random.sample(all_cells, group_size)
        #         self.groups.append(group)
        #         # Remove the selected cells to ensure no repeats
        #         for cell in group:
        #             all_cells.remove(cell)

        #     # create seperate list of each of the remaining cells
        #     #self.remaining_cells = [[item] for item in all_cells]
            
        #     # create one list of the remaining cells
        #     print("created groups", self.groups)
        #     self.remaining_cells = [all_cells]


        