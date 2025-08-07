
from PySide6.QtWidgets import QMessageBox 
import random
import create_sequence as cs
from pycromanager import JavaObject

# import matplotlib
# matplotlib.use('Agg')  # Use the non-GUI backend for matplotlib
# import matplotlib.pyplot as plt
# import os

class Stage: # called by protocolSet.py
    """This class represents a protocol stage. Each stage have many attributes, which determine the stimulation parameters and cellular groups to be stimulated.
    It is referred as self.stages[], in the maingui. Called by the protocolSet class"""
    
    

    def __init__(self, images): 
        # define Culture as parent class
        #   CURRENTLY THE PROTOCOL AND STAGES ARE MIXED TOGETHER!!!! 

        self.number = int() # number of the stage in the protocol sequnce
        self.number_cells = int() # number of detected cells in the culture
        self.group_size = int() # number of cells in each group
        self.groups_number = int() # number of groups
        #self.groupFreq = float() # stimulation frequency in Hz for each group (whole sequence cycle)
        self.groups_period = int() # time of one run of all groups. The average time between same group stimulation in ms (when probability stimulation is similar to groups)
        self.on_time = int() # DMD on time in ms for each stimulation
        self.background_freq = float() # DMD background frequency in Hz
        self.background_on_time = int() # DMD on time in ms - not in use (?)
        self.sequence = [] # list of each group indices of the cells to be stimulated in a sequence
        #self.sequences = [] # list of sequences, each is a list of groups to be stimulated in the protocol
        self.sequences_images = [] # list of images to be displayed in each sequence
        self.inter_mask_interval = float() # ms time between each mask in a sequence
        self.sequence_repeats = int()
        self.stim_time = int() # stimulation time for running the protocol in minutes
        self.cycle_time = float() # 
        self.image_repeats = int()
        self.manual_groups = [] # list of manually selected groups
        self.is_manual = False # get checkbox selection of isManualSequence
        self.is_probability_stim = False # get checkbox selection of prob_stim
        #self.period = int() # time between triggers in ms
        self.ID = int() # ID of the stage - used to reproduce the stage by the user
        # self.bridge = Brigde # bridge to the Java code
        # self.DMDArray = self.bridge._construct_java_object('java.util.ArrayList') # list of DMD images to be displayed in each sequence
        self.DMDArray = JavaObject('java.util.ArrayList') # use the core JavaObject from pycromanager to create a Java ArrayList
        self.input_groups = [] # List of lists of cells belonging to each group of stimulated neurons
        self.input_cells = [] # List of all cells to be stimulated by pattened light
        self.output_group = [] # List of cells not to be stimulated by pattened light
        self.stim_type = str() # type of stimulation (e.g. 'random', 'sequential', 'repeated', 'manual', 'probability', 'sleep')
        self.jitter = False # jittering of the stimulation
        self.jitter_time = int() # jitter time in ms
        self.group_probabilities = [] # list of probabilities for each group (both small and large groups)
        self.groups = [] # list of groups of cells to be stimulated. Created by create_sequence.py
        self.remaining_cells = [] # list of individual cells not grouped
        self.images = images # list of images of the cells somata
        self.groups_images = [] # list of images of the groups of cells. Created by create_sequence.py
        self.ard_buffer = 18 # number of integers to be sent to the Arduino buffer - to sync with MaxOne
        self.group_distribution_number = 50 # Average number of group presentations in the sequence 
        self.group_probability_ratio =  1.5 # probability ratio between groups 
        self.group_divider = 3 # number of groups to divide the groupSize into - for the probability stimulation to break the group into smaller groups so the stimulation do not synchronize all cells.
        self.help_counter = 0 # counter for to plot the DMDArray at the first run of the protocol
        self.start_run_time = None # time of the start of the stage run
        self.square_size = 10
        self.square_groups = 1 # number of square simultaneuosly presented as a group
        
    def __getstate__(self):
        state = self.__dict__.copy()
        # Remove non-pickleable or unwanted attributes
        if 'bridge' in state:
            del state['bridge']
        if 'DMDArray' in state:
            del state['DMDArray']
        if 'images' in state:
            del state['images']
        if 'groups_images' in state:
            del state['groups_images']
        return state
        

    def calc_interMaskInterval(self):
        
        self.inter_mask_interval = (self.groups_period / self.groups_number) - self.on_time # ms
        
        # show a warning window if inter_mask_interval is negative
        if self.inter_mask_interval < 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Timing error")
            msg.setText("inter_mask_interval < 0. Change onTime, Frequency or Group number")
            msg.exec()
            # it means that you should decrease the numbers of groups by increasing group size or group the remaining cells into larger groups (2 cells instead of

        print("groups_period:", self.groups_period, "groupsNumber:", self.groups_number, "onTime:", self.on_time ,"inter_mask_interval:", self.inter_mask_interval)
        # through a warning if inter_mask_interval is shorter than 50 ms
        if self.inter_mask_interval < 50:
            print("Warning: Protocol.py inter_mask_interval is shorter than 50 ms")
            # it means that you should decrease the numbers of groups by increasing group size or group the remaining cells into larger groups (2 cells instead of 1) 

        self.cycle_time = self.inter_mask_interval*len(self.sequence)/1000 # one cycle of a sequence in seconds
        self.sequence_repeats = round(self.stim_time*60 / self.cycle_time) # number of protocol repeats for running the protocol
        print("stimTime sec:", self.stim_time*60, "cycleTime sec:", self.cycle_time, "n sequence repeats =", self.sequence_repeats) 

        print("protocol time", self.stim_time*60, "sec") # can have few stages with different times???



    def create_sequence(self): # replaces  def createSequence(stage) in protocolSet.py

        # print self attributes
        
        # Check if the total number of required group members exceeds the numberCells
        if self.groups_number * self.group_size > self.number_cells:
            # print the number of cells and groups
            print(f"Number of cells: {self.number_cells}, Number of groups: {self.groups_number}, Group size: {self.group_size}")   
            raise ValueError("Not enough cells to create the required number of groups without repeats")
            

        # check if self.output_group is empty
        if not self.output_group:
        # Asks the user if self.output_group should be created
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("Output group")
            msg.setText("Do you want to create an output group?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Yes)
            response = msg.exec()

            if response == QMessageBox.Yes:
                self.create_output_group()
            else:
                self.output_group = []
                

        self.input_cells = list(range(1, self.number_cells + 1)) # handled by create_sequences.py 
        

        # create groups according to the selected stimulation type
        print("stimulation type:", self.stim_type) 
        print("Protocol output group", self.output_group)
        if self.stim_type == 'Random':
            # create_sequence
            
            cs.create_random_sequence(self) # create_sequence in the Potocol object stage (create_sequence.py)
        elif self.stim_type == 'Sequential':
            cs.create_sequential_sequence(self)

        elif self.stim_type == 'Test':
            cs.create_test_sequence(self)
        elif self.stim_type == 'Squares':
            cs.create_squares_sequence(self)
        else:
            print(f"Error: Unsupported stimulation type '{self.stim_type}'. Please use 'Random' or 'Sequential'.")




    def create_DMDArray(self, indices):  # replaces def create_stimulation_sequence in protocolSet.py CALLED by protocolSet.py via Protocol object

        # clear the DMDArray
        self.DMDArray.clear()
        
        for idx in indices:  # iterate over the groups' indices in the sequence to create the DMD array
            # the groups index corresponds to an image in groups_images
            ind_image = self.groups_images[idx]  # get the image of the group created by create_sequence.py
            self.DMDArray.add(ind_image.ravel())  # add the image to the Java array

        # Debugging output
        print("image indices", indices) 

        # if self.help_counter == 0:  # plot the DMDArray at the first run of the protocol
        #     self.help_counter += 1

        #     # Assuming indices and self.groups_images are defined
        #     fig, axes = plt.subplots(nrows=3, ncols=6, figsize=(18, 10))  # 3 rows, 6 columns
        #     axes = axes.flatten()  # Flatten the 2D axes array for easier indexing

        #     for i, idx in enumerate(indices):
        #         image = self.groups_images[idx]
        #         axes[i].imshow(image, cmap='gray')
        #         axes[i].set_title(f"Group {idx}")
        #         axes[i].axis('off')  # Optional: turn off axes for cleaner presentation

        #     # Hide any unused subplots
        #     for j in range(len(indices), len(axes)):
        #         axes[j].axis('off')

        #     plt.tight_layout()


        #     # Save the plot in the Protocols folder
        #     protocols_dir = os.path.join(os.getcwd(), "Protocols")  # Path to Protocols folder
        #     os.makedirs(protocols_dir, exist_ok=True)  # Create the folder if it doesn't exist
        #     output_path = os.path.join(protocols_dir, "DMDArray_plot.png")
        #     plt.savefig(output_path)
        #     print(f"Plot saved to {output_path}")