


# protocoSet class for setting the protocol parameters before running it
# activated following the "Load Protocol" button in the main window
# It create_stimulation_sequence which is the sequence of images to be displayed on the DMD (self.bridge._construct_java_object)
#
#from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QVBoxLayout, QMessageBox, QPushButton
#from PySide6.QtCore import Slot, Signal, QThread
import pandas as pd
import random
from Protocol import Protocol

class ProtocolSet():
        """ Class for setting the protocol parameters before running it"""
    
    
        def __init__(self, gui):
            super(ProtocolSet, self).__init__()
            self.stages_table = gui.stages_table # dataframe of the protocol
            self.manualSequence = gui.manualSequence # list of manually selected groups
            #self.images = gui.culture.transform_images # list of DMD images of each cell
            self.images = gui.culture.somaMasks
            self.bridge = gui.core._get_bridge() # get the Java bridge to create Java SLM sequence
            self.DMDArray = [] # list of Java arrayLists, each arrayList is a sequence of (vectorizred) images to be displayed on the DMD
            
            print("init protocol set", len(self.images))
            

        def extract_protocol(self):
            """ Extract the protocol from the dataframe before setting it"""

            # extract the headers of the dataframe
            self.headers = list(self.stages_table.columns)
            # extract the data of the dataframe
            self.data = self.stages_table.values.tolist()
            # extract the number of rows in the dataframe
            self.n_rows = len(self.data) # number of stages in the protocol

            self.numberCells = len(self.images)
            self.sequences = [] # list of lists of the sequence of image INDICES to be displayed on the DMD
            self.stages = []    
            
            # Build the sequences of the protocol
            for index, row in self.stages_table.iterrows():  # iterate over the stages in the protocol  
                
                print("stage number:", index, "row: \n", row)
                stage = Protocol()
                #stage.append(Protocol()) # create a new stage
                stage.number = index+1 # number of the stage in the protocol sequnce

                # get the stimulation type (stimType)
                stage.stimType = row['stimType']
                # (0, "Random") - randomize the sequence every iteration
                # (1,"Group only stim.") - stimulate only the groups in the sequence (no single cells/remaining cells)
                # (2, "Order") - repeat the same sequence over and over
                # (3, "Test") - run the sequence under calcium imaging
                # (4, "Spontaneous") - randomize stimulation to all cells in the culture (no groups)
                print("stimType:", stage.stimType)

                # get the group size
                stage.groupSize = int(row['groupSize'])
                # get the number of groups
                stage.groupsNumber = int(row['groupsNumber']) # number of multiple cells groups to be stimulated synchronously 
                stage.numberCells = self.numberCells # number of detected cells in the culture
                stage.groupFreq = float(row['groupFreq']) # stimulation frequency in Hz for all the groups (whole sequence cycle)
                stage.isManual = row['isManualSequence'] # get checkbox selection of isManualSequence
                print("protocolSet - isManual:", stage.isManual)

                # get the checkbox selection of prob_stim
                stage.isProbabilityStim = row['prob_stim'] # prob_stim will create a probability distribution of the groups according to the number of groups and predermined probabilities


                

                # create  groups
                if stage.isManual: # if the groups are selected manually using the mouse (Click and group button)
                    if len(self.manualSequence) < 1:
                        raise ValueError("There are no manual groups selected")
                    sequence = self.manualSequence # How remianing cells are handled?
                    #update groupsNumber
                    stage.groupsNumber = len(self.manualSequence)

                    print("manual sequence used!!!")
                else:
                    self.create_random_groups(self.numberCells, stage.groupsNumber, stage.groupSize) # add self.groups
                    sequence = self.groups + self.remaining_cells # indices of the cells to be stimulated in a sequence
                    if not sequence[-1]: # if the last element is empty
                        sequence.pop()
                        print("pop empty list")
                    
                        

                print("sequence:", sequence)
                self.sequences.append(sequence) # each stage has one list in sequences - for plotting testing
                
                
                # get the background frequency
                stage.backgroundFreq = float(row['backgroundFreq'])

                # calculate the stimulation frequency
                stage.onTime = 5 # ms
                stage.backgroundOnTime = 5 # ms
                # The inter-mask interval is the time 1/groupFreq
                
                stage.stimTime = int(row['stimTime']) # stage stimulation running time in minutes
                stage.cycleTime = 1/stage.groupFreq # one stage cycle time in seconds

                stage.calc_interMaskInterval() # ms - should be a parameter in the Protocol.py (also a class)

                stage.sequence = sequence
                #print("stage:", stage)

                print("stage num: ", index, "; repeats:", stage.sequenceRepeats)

                self.stages.append(stage)
                print("protocolSet-stages: sequence", self.stages[index].sequence)


            #print(self)
            #self.create_stimulation_sequence()


            
    # create the image index for the protocol sequence
        def create_stimulation_sequence(self): # called by handleLoadedData in maingui.py following the "Load Protocol" button
            """
            set the number of groups (requested groups + reminder single cells)
             self.n_groups = len(self.images) - self.groupSize*self.groupsNumber + self.remainingCells # sanity check
             if self.n_groups != self.groupsNumber:
                raise ValueError("Number of groups is not correct")
            
            create sequence of images to be displayed on the DMD
            The sequence is based on the self.sequence list of lists where each list is a group of cells or a single cell
            if the list is longer than 1, it sum the images in the list (each image stand for single soma. When summing is will be a group of somas)
            Create self.sequences_images which is the sequence of images to be displayed on the DMD
            """

            # create the sequence of images to be displayed on the DMD
            self.sequences_images = []
            javaarray = self.bridge._construct_java_object('java.util.ArrayList')
            for idx, stage in enumerate(self.sequences): # iterate over the stages in the protocol
                #print("idx", idx)
                
                # TODO:
                # IF probability stimulation is checked - create a distribution of the groups according to the number of groups
                # Add black image at the end of the sequence
                # self.black_image = np.zeros((self.core.getSLMHeight(self.dmd_name),
                #             self.core.getSLMWidth(self.dmd_name)), dtype=np.uint8)

                self.DMDArray.append(javaarray)
                sequence_images = []
                for group in stage: # group is a list of cells either of size 1 or larger
                    group_images = []
                    for cell in group:
                        group_images.append(self.images[cell - 1])
                    # sum the images in the group
                    group_sum = sum(group_images) # sum the images in the group - is stimulation to a group of cells
                    sequence_images.append(group_sum) # add one image to the sequence
                    
                    # add the image to the Java array
                    #print(type(group_sum))
                    self.DMDArray[idx].add(group_sum.ravel()) # add the image to the Java array
                self.sequences_images.append(sequence_images) # add one sequence to the list of sequences
            

            # print the number of sequences in the protocol
            print("number of sequences in the protocol:", len(self.sequences_images), "create_stimulation_sequence")

            # print all attributes of self.prot object
            # for attr, value in vars(self.stages).items():
            #     print(f"{attr} = {value}")


            # plot the sequence of images for testing - each panel is a group of cells (or a single cell)
            import matplotlib.pyplot as plt
            

            # plot the groups (of the DMDArray) in the stages 
            for stage, sequence_images in enumerate(self.sequences_images, start=1):
                fig, axes = plt.subplots(1, len(sequence_images), figsize=(15, 5))
                for i, image in enumerate(sequence_images):
                    axes[i].imshow(image, cmap='gray')
                    axes[i].set_title(f"Group {i}") 
                plt.show()


        def create_random_groups(self, numberCells, groupsNumber, group_size):
            # called by handleLoadedData in maingui.py
            # Check if the total number of required group members exceeds the numberCells
            if groupsNumber * group_size > numberCells:
                raise ValueError("Not enough cells to create the required number of groups without repeats")

            all_cells = list(range(1, numberCells + 1))
            self.groups = []

            for _ in range(groupsNumber):
                group = random.sample(all_cells, group_size)
                self.groups.append(group)
                # Remove the selected cells to ensure no repeats
                for cell in group:
                    all_cells.remove(cell)

            # create seperate list of each of the remaining cells
            #self.remaining_cells = [[item] for item in all_cells]
            
            # create one list of the remaining cells
            print("create groups", self.groups)
            self.remaining_cells = [all_cells]


        