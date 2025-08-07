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
        self.culture = gui.culture # culture object to save the protocol run data
        self.protocol = gui.protocol # protocol is a protocolSet object which contains Stage objects in the stages attribute
        self.stages = self.protocol.stages # list of stages in the protocol
        self.currentStage = 0
        #self.arduino = gui.arduino # arduino object to control the polygon, light source and MaxOne digipins
        self.arduino_comm = gui.arduino_comm # arduino communication object to send messages to the Arduino

        # print(dir(self.stages))

        # get the core to control the DMD
        self.core = gui.core
        #self.bridge = self.core._get_bridge()

        #self.DMDArray = gui.prot.DMDArray # list of Java arrayLists, each arrayList is a sequence of (vectorizred) images to be displayed on the DMD
        #self.DMDArray = DMDArray if DMDArray is not None else gui.prot.DMDArray
        # print the shape of DMDArray

        # The number of groups in the protocol - single cells not set into groups are considered as a group (e.g. in 15 cells with 2 groups of 6 cells and 3 single cells, we'll have 5 groups)
        # "image len", self.DMDArray[0][0].size()
        #         # Get the first ArrayList
        # first_array_list = self.stages[0].DMDArray # get the first Java ArrayList
        # first_element = first_array_list.get(0) # get the first Java arraylist element (flatten numpy array)
        # print("image java", type(first_element))
        # print("ravel image java", len(first_element))
 
        self.dmd_name = self.core.get_slm_device()
        self.slm_width = self.core.get_slm_width(self.dmd_name)
        self.slm_height = self.core.get_slm_height(self.dmd_name)
        #print("slm width:", self.slm_width, "slm height:", self.slm_height)
        #self.DMDArray = self.bridge._construct_java_object('java.util.ArrayList') # list of DMD images to be displayed in each sequence
        
        self.black_image = np.zeros((self.core.get_slm_height(self.dmd_name),
                             self.core.get_slm_width(self.dmd_name)), dtype=np.uint8)
        #print("black image shape:", self.black_image.shape)
        #self.sleepTime = 500 # time between images in ms - should be a parameter in the protocol...
        
        # not needed anymore as the sequence is randomized in the protocol design
        # self.Randjavaarray = self.bridge._construct_java_object('java.util.ArrayList')
        # self.randomization_order = [] # list of randomization orders for each stage and repeats - continuously increasing - need to save and clear it during run?
        # self.rand_vector = [] # list of randomized group numbers - up to 19 numbers due to Arduino buffer overflow
        

# if you need to run a distribution of images with different probabilities we need to create:
        # 1. a list of probabilities for each group
        # 2. a vector of the group's identifier having similar probabilities at 1 for accoring to the group identifier
        # Need to iterate over the vector if the group identifier and create sequences to be displayed on the DMD
        # 3. Determine the sequence length (up to 2000 images) - 
        # 4. create sequences by iterating over the vector of group identifiers and create a sequence of images to be displayed on the DMD
    
    # Automatically called when running QThread  
    def run(self):

        self.times = 0

        # add one to the protocol index
        
        self.culture.protocols_number += 1 # update the number of protocols in the culture object
        print("protocols number:", self.culture.protocols_number)
        # add the current protocol to the .protocols list in the culture object
        
        
        
        try:
            for stage_index, stage in enumerate(self.stages): # iterate over the number of stages in protocol


                if self.stop_event.is_set():
                        print("Aborting the run")
                        break
                
                # if index 0 update and save the culture and the protocol ????
                if stage_index == 0:
                    ### Update the culture object with the sequence of the stage
                    # create protocol index folder to save the protocol and stage data

                    #self.culture.save() # save the culture object to the disk - handled in culture_data.py
                    self.protocol.save_protocol(self.culture.protocols_number)    # save the protocol to the culture folders. handled in culture_data.py
                    

                sequence = stage.sequence
                # save the sequence to disk - handled in culture_data.py
                #start_time = time.time() # get the current time
                stage.start_run_time = time.time() # time of the start of the stage run

                self.protocol.save_sequence(stage_index, sequence, stage.start_run_time) # save the sequence to the culture object
                
                 # get the sequence of the stage
                arduino_buffer = stage.ard_buffer # number of integers to be sent to the Arduino buffer - to sync with MaxOne
                #sequence_cuts = round(len(sequence)/arduino_buffer) # number of cuts of the sequence to fit the arduino buffer
                # print the number of protocol repeats for running the protocol
                print("protocol repeates", stage.sequence_repeats)
                
                    
                # Update the stage start time and save it.
                self.protocol.save_start_time(stage_index, stage.start_run_time)

                for seq_repeat in range(stage.sequence_repeats): # iterate over the number of repeats of the stage
                    

                    # wait 100ms
                    #self.msleep(100) # wait for file saving


                    # use the sequence to create DMDArray of arduino_buffer size images (bound the Arduino buffer)
                    # running over the sequence with chuncks (steps) of arduino_buffer size
                    for i in range(0, len(sequence), arduino_buffer): # iterate over the length of arduino_buffer in the sequence
                            current_display_indices = sequence[i:i+arduino_buffer] # get the indices of the groups to be displayed
                            stage.create_DMDArray(current_display_indices) # create the DMDArray of images to be displayed on the DMD

                            # print the size of the java array DMDArray
                            print("DMDArray size:", stage.DMDArray.size())
                            self.core.load_slm_sequence(self.dmd_name, stage.DMDArray) # load the sequence to the DMD
                            self.msleep(len(current_display_indices)*4) # wait for the DMD to load the sequence - 4 ms per image

                            if self.stop_event.is_set():
                                print("Aborting the run")
                                self.core.stop_slm_sequence(self.dmd_name)
                                QThread.sleep(1)
                                
                                # Check if the DMD is responding
                                try: # check if the DMD is responding
                                    device_label = self.gui.core.get_property(self.dmd_name, "Label")
                                    print(f"Communication active: Device '{self.dmd_name}' responded with Label='{device_label}'.")    
                                    self.core.set_slm_image(self.dmd_name, self.black_image) # display black image
                                    self.core.display_slm_image(self.dmd_name) # display black image
                                except Exception as e:
                                    # If an exception occurs, communication is likely disrupted
                                    print(f"Communication failed for device '{self.dmd_name}'. Error: {e}")         
                                break

                            # self.times += int(self.stages[index].stim_time) # validation of run timing - TBA

                            # Use Arduino to trigger the presentation of the images
                            arduino_display_indices = [x + 1 for x in sequence[i:i+arduino_buffer]] # adds 1 to the groups due to issues with Arduino encoding zeros digipins
                            
                            
                            # message = f"{arduino_display_indices},{self.stages[stage_index].groups_period},{self.stages[stage_index].on_time}\n"
                            # self.arduino.write(message.encode()) # Length of message is limited due to Arduino buffer overflow - ~19 numbers
                            # print(f"Message sent to Arduino: {message.strip()}") # uncheck to validate the message sent to Arduino
                      
                            # while not self.stop_event.is_set(): # Wait for Arduino to confirm it received the message
                            #     if self.arduino.in_waiting > 0:
                            #         response = self.arduino.readline().decode().strip()
                            #         #print(f"Arduino response: {response}") # uncheck to validate arduino response
                            #         if response == "Message received":
                            #             #print("Arduino confirmed message received. Starting sequence.")
                            #             break

                            # send the message to the Arduino via adruino_comm.py
                            #self.arduino_comm.send_message(arduino_display_indices, self.stages[stage_index].groups_period, self.stages[stage_index].on_time) # send the message to the Arduino 
                            self.arduino_comm.send_message(arduino_display_indices, stage.groups_period, stage.on_time) # start the sequence by the Arduino

                            self.core.start_slm_sequence(self.dmd_name) # start the sequence in external trigger mode needs TTL input to display the images
                            #print("Sequence started - waiting for trigger")

                            # while not self.stop_event.is_set(): # As long as stop wasn't pressed, wait for Arduino to confirm it received the message
                            #     if self.arduino.in_waiting > 0:
                            #         response = self.arduino.readline().decode().strip()
                            #         print(f"Arduino response: {response}") # uncheck to see the presented images indices
                            #         if "Sequence finished" in response:
                            #             print(f"num. presents {i}, of: {len(sequence)} completed by Arduino.")
                            #             break
                            response = self.arduino_comm.wait_for_sequence_end_blocking(stop_event=self.stop_event) # wait for the Arduino to finish the sequence

                            if response:
                                print(f"Arduino response: {response}")
                                print(f"num. presents {i}, of: {len(sequence)} completed by Arduino.")
                            else:
                                print("Arduino wait exited (stopped or error).")
                                break

                    self.core.stop_slm_sequence(self.dmd_name) # stop the sequence  - findout where to put it !!!!!!       
                    print(f"Sequence repeat {seq_repeat + 1}, out of: {self.stages[stage_index].sequence_repeats} completed by Arduino.")    

      
                    # no trigger display
                    # # DISPLAY THE IMAGES - iterate over the repeats of the stage
                    # for i in range(self.stages[index].groupsNumber): #prot.stages[0].imageRepeats
                    #     #print("stage:", index +1, "repeat:", i, "of ", self.stages[index].imageRepeats)
                    #     if self.stop_event.is_set():
                    #         print("Aborting the run")
                    #         break

                    #     self.core.displaySLMImage(self.dmd_name) # advance to the next image in the sequence
                    #     self.msleep(self.stages[index].interMaskInterval) # sleep between each group (image) presentation in the sequence

        except Exception as e:
            print("Error in runProtocol:", e)


        end_time = time.time()
        duration = end_time - stage.start_run_time
        print("Protocol run duration:", duration)
        
        

        # display black image because there's is a delay in the DMD dispaly between groups
        # self.core.setSLMImage(self.dmd_name, self.black_image)
        # self.msleep(5) # upload time is about 4 ms
        # self.core.displaySLMImage(self.dmd_name)
        #print("black image- Protocol finished")
        #self.protocolFinishSignal.emit()
        # END OF RUN PROTOCOL

    def stop(self):
        print("Trying to abort the protocol")
        self.stop_event.set() # send the signal to stop the protocol run - stop the qthread of runProtocol.

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
        self.randomization_order.append(self.rand_vector) # is it increasing indefinitely? - need to check
        
        self.Randjavaarray.clear() # clear the java array list
        # Place each image in its new position
        for original_idx, new_idx in enumerate(self.rand_vector):
            
            #DMDRandArray[original_idx] = javaSequence.get(new_idx)
            #print("javaSequence[idx] type:", type(javaSequence.get(new_idx)), "javaSequence[idx] len:", len(javaSequence.get(new_idx)))
            self.Randjavaarray.add(javaSequence.get(new_idx)) # add the flatten image to the java array list

        #print("Randjavaarray prepared")
        #return self.Randjavaarray

        
           


