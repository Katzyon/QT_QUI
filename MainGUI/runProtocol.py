# ProtocolRunner class for running a protocol
# It is a subclass of QThread
# It has a signal to send the dataframe to the main window
# It has a method to run the protocol (run_protocol) by iterating over the dataframe self.stages_table 
# The dataframe is a list of stages in the protocol create by the user in protocol_design.py
# It is called by the main window in the runProtocol method

#from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QVBoxLayout, QMessageBox, QPushButton
from PySide6.QtCore import Slot, Signal, QThread
import pandas as pd
import random
import time
import numpy as np
import threading
#import matplotlib.pyplot as plt
 # (masks > 0).astype(np.uint8)

class ProtocolRunner(QThread):
    
    #signalOutData = Signal(object) # signal to send the dataframe to the main window
    #protocolFinishSignal = Signal()

    def __init__(self, gui, parent=None):
        super().__init__(parent)
        self.stop_event = threading.Event() # event to stop the protocol from button press in the main GUI
        self.stages = gui.prot.stages # dataframe of the protocol
        self.currentStage = 0
        #self.onTime = 0 # DMD on time in ms for each stimulation
        #self.period = 0 # image display period in ms
        self.arduino = gui.arduino # arduino object to control the polygon, light source and MaxOne digipins
        
        print(dir(self.stages))
        print("number of stages:", len(self.stages)) # the DMAArray is in self.stages[i].DMDArray

        # get the core to control the DMD
        self.core = gui.core
        self.bridge = self.core._get_bridge()
        #self.DMDArray = gui.prot.DMDArray # list of Java arrayLists, each arrayList is a sequence of (vectorizred) images to be displayed on the DMD
        #self.DMDArray = DMDArray if DMDArray is not None else gui.prot.DMDArray
        # print the shape of DMDArray

        # The number of groups in the protocol - single cells not set into groups are considered as a group (e.g. in 15 cells with 2 groups of 6 cells and 3 single cells, we'll have 5 groups)
        print("DMDArray num stages:", len(self.stages), "num images", self.stages[0].DMDArray.size()) # "image len", self.DMDArray[0][0].size()
                # Get the first ArrayList
        first_array_list = self.stages[0].DMDArray # get the first Java ArrayList
        first_element = first_array_list.get(0) # get the first Java arraylist element (flatten numpy array)
        print("image java", type(first_element))
        print("ravel image java", len(first_element))
 
        self.dmd_name = self.core.getSLMDevice()
        self.slm_width = self.core.getSLMWidth(self.dmd_name)
        self.slm_height = self.core.getSLMHeight(self.dmd_name)
        #print("slm width:", self.slm_width, "slm height:", self.slm_height)
        
        self.black_image = np.zeros((self.core.getSLMHeight(self.dmd_name),
                             self.core.getSLMWidth(self.dmd_name)), dtype=np.uint8)
        #print("black image shape:", self.black_image.shape)
        #self.sleepTime = 500 # time between images in ms - should be a parameter in the protocol...
        self.Randjavaarray = self.bridge._construct_java_object('java.util.ArrayList')
        self.randomization_order = [] # list of randomization orders for each stage and repeats
        self.rand_vector = [] # list of randomized group numbers - up to 19 numbers due to Arduino buffer overflow
        #self.running = True

# if you need to run a distribution of images with different probabilities we need to create:
        # 1. a list of probabilities for each group
        # 2. a vector of the group's identifier having similar probabilities at 1 for accoring to the group identifier
        # Need to iterate over the vector if the group identifier and create sequences to be displayed on the DMD
        # 3. Determine the sequence length (up to 2000 images) - 
        # 4. create sequences by iterating over the vector of group identifiers and create a sequence of images to be displayed on the DMD
    
    # Automatically called when running QThread  
    def run(self):


        start_time = time.time()
        self.times = 0

        try:
            for index, row in enumerate(self.stages):

                if self.stop_event.is_set():
                        print("Aborting the run")
                        break
                #self.images = self.images_[index] # list of DMD images of each cell 
                #print("images in running prot:", len(self.images))
                
                javaSequence = self.stages[index].DMDArray  # self.DMDArray.append(javaarray)list of Java arrayLists, each arrayList is a sequence of (vectorizred) images to be displayed on the DMD
                print("sequence type:", type(javaSequence), "sequence len:", javaSequence.size())
                
                self.times += int(self.stages[index].stimTime)

                for seq_repeat in range(self.stages[index].sequenceRepeats): # need to randomize the sequence every sequence repeat
                    #print("sequence repeat:", seq_repeat + 1, "of", self.stages[index].sequenceRepeats)
                    if self.stop_event.is_set():
                            print("Aborting the run")
                            break
                    #self.javaSequence = self.randomizeSequence(javaSequence)
                    #self.core.loadSLMSequence(self.dmd_name, javaSequence) # - test the logic of the javaSequence!!!!
                    self.randomizeSequence(javaSequence) # randomize the sequence of images
                    self.core.loadSLMSequence(self.dmd_name, self.Randjavaarray) # load the sequence to the DMD
                    
                    # wait 10 ms for the DMD to load the sequence - if the sequence is long - need to adjust the time accordingly, How? 
                    
                    self.msleep(10)
                    
                    #print("image repeats:", self.stages[index].imageRepeats)
                    # Send sequence information to Arduino (indices, period, on_time)
                    message = f"{self.rand_vector},{self.stages[index].period},{self.stages[index].onTime}\n"
                    self.arduino.write(message.encode())
                    # show error message if the length of self.rand_vector is < 2
                    if len(self.rand_vector) < 2:
                        print("Error: The number of groups in the sequence is less than 2- runProtocol L97")
                        break

                    print(f"Sent to Arduino: Sequence {self.rand_vector} with period {self.stages[index].period} ms and on time {self.stages[index].onTime} ms")

                    
                    # Wait for Arduino to confirm it received the message
                    while not self.stop_event.is_set():
                        if self.arduino.in_waiting > 0:
                            response = self.arduino.readline().decode().strip()
                            print(f"Arduino response: {response}")
                            if response == "Message received":
                                #print("Arduino confirmed message received. Starting sequence.")
                                break

                    self.core.startSLMSequence(self.dmd_name) # start the sequence in external trigger mode needs TTL input to display the images
                    #print("Sequence started - waiting for trigger")

                    while not self.stop_event.is_set():
                        if self.arduino.in_waiting > 0:
                            response = self.arduino.readline().decode().strip()
                            print(f"Arduino response: {response}")
                            if response == "Sequence finished":
                                print(f"Sequence repeat {seq_repeat + 1}, out of: {self.stages[index].sequenceRepeats} completed by Arduino.")
                                break


                    
                    # no trigger display
                    # # DISPLAY THE IMAGES - iterate over the repeats of the stage
                    # for i in range(self.stages[index].groupsNumber): #prot.stages[0].imageRepeats
                    #     #print("stage:", index +1, "repeat:", i, "of ", self.stages[index].imageRepeats)
                    #     if self.stop_event.is_set():
                    #         print("Aborting the run")
                    #         break

                    #     self.core.displaySLMImage(self.dmd_name) # advance to the next image in the sequence
                    #     self.msleep(self.stages[index].interMaskInterval) # sleep between each group (image) presentation in the sequence
                        


                self.core.stopSLMSequence(self.dmd_name)
        except Exception as e:
            print("Error in runProtocol:", e)


        end_time = time.time()
        duration = end_time - start_time
        print("Protocol run duration:", duration)
        print("Protocol theoretical run duration:", self.times*60, "sec")
        
        # display black image because there's is a delay in the DMD dispaly between groups
        self.core.setSLMImage(self.dmd_name, self.black_image)
        self.core.displaySLMImage(self.dmd_name)
        # self.msleep(150)
        #print("black image- Protocol finished")
        #self.protocolFinishSignal.emit()

    def stop(self):
        print("Trying to abort the protocol")
        #self.protocolFinishSignal.emit()
        #self.running = False
        self.stop_event.set() # 

    def randomizeSequence(self, javaSequence):
        # randomize the sequence of images
        # see for details - QT_GUI/Develope/RandGroupDistribute.ipynb
        #print("runProtocol: sequence type:", type(javaSequence), "sequence len:", javaSequence.size())
        
        # create a random vector to randomize the order of the images
        self.rand_vector = np.random.choice(range(javaSequence.size()), javaSequence.size(), replace=False).tolist()
        print("randomizeSequence- rand_vector:", self.rand_vector)

            # Initialize self.randomization_order if it doesn't exist
        if not hasattr(self, 'randomization_order'):
            self.randomization_order = []

        # Append the randomization order to the class variable
        self.randomization_order.append(self.rand_vector)
        
        self.Randjavaarray.clear() # clear the java array list
        # Place each image in its new position
        for original_idx, new_idx in enumerate(self.rand_vector):
            
            #DMDRandArray[original_idx] = javaSequence.get(new_idx)
            #print("javaSequence[idx] type:", type(javaSequence.get(new_idx)), "javaSequence[idx] len:", len(javaSequence.get(new_idx)))
            self.Randjavaarray.add(javaSequence.get(new_idx)) # add the flatten image to the java array list

        #print("Randjavaarray prepared")
        #return self.Randjavaarray

        
           


