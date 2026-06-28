# ProtocolRunner class for running a protocol called by the main GUI when the user clicks the "Run Protocol" button.
# It is a subclass of QThread
# It has a signal to send the dataframe to the main window
# It has a method to run the protocol (run_protocol) by iterating over the dataframe self.stages_table 
# The dataframe is a list of stages in the protocol create by the user in protocol_design.py
# It is called by the main window in the runProtocol method

#from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QVBoxLayout, QMessageBox, QPushButton
from PySide6.QtCore import Slot, Signal, QThread
import pandas as pd
import time
import numpy as np
import threading
import traceback
from datetime import datetime, timedelta
import re


#import matplotlib.pyplot as plt
 # (masks > 0).astype(np.uint8)

class ProtocolRunner(QThread):
    
    #signalOutData = Signal(object) # signal to send the dataframe to the main window
    #protocolFinishSignal = Signal()
    plot_dmd = Signal(list, list) # signal to plot the DMD images and the sequence numbers - list of images and list of sequence numbers

    def __init__(self, gui, parent=None):
        super().__init__(parent)
        self.n_protocol_repeats = gui.n_protocol_repeats # number of protocol repeats from the main GUI
        self.file_tag = gui.get_file_tag() # file tag from the main GUI to use as prefix for saving files
        self.stop_event = threading.Event() # event to stop the protocol from button press in the main GUI
        self.culture = gui.culture # culture object to save the protocol run data
        self.protocol = gui.protocol # protocol is a protocolSet object which contains Stage objects in the stages attribute
        self.protocol_name = gui.protocol_name # protocol name from the main GUI to use for saving files
        self.stages = self.protocol.stages # list of stages in the protocol
        self.currentStage = 0
        #self.arduino = gui.arduino # arduino object to control the polygon, light source and MaxOne digipins
        self.arduino_comm = gui.arduino_comm # arduino communication object to send messages to the Arduino
        self.recorder = gui.recorder  # RemoteRecordingManager instance for recording - currently manually initialized in the main GUI (maxwell server)

        self.arduino_comm_time = 0.6 # time to wait for Arduino communication in seconds
        # print(dir(self.stages))

        # get the core to control the DMD
        self.core = gui.core
        #self.bridge = self.core._get_bridge()
        self.plot = False # whether to plot the DMD images at the start of each stage for validation



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

        #self.times = 0  
        self.culture.protocols_number += 1 # update the number of protocols in the culture object
        print("protocols number:", self.culture.protocols_number)
        # print the protocol name
        print("protocol prefix name:", self.protocol_name)
        # add the current protocol to the .protocols list in the culture object
        
        # print the number of stages in the protocol
        print("Number of stages in the protocol:", len(self.stages))
        
        
        
        try:
            for protocol_repeat_idx in range(self.n_protocol_repeats):
                print(f"=== Protocol repeat {protocol_repeat_idx + 1}/{self.n_protocol_repeats} ===")

                
                for stage_index, stage in enumerate(self.stages): # iterate over the number of stages in protocol                    

                    if self.stop_event.is_set():
                            print("Aborting the run")
                            return
                    
                    unique_stage_id = (protocol_repeat_idx+1) * len(self.stages) + stage_index
                    
                    # if index 0 update and save the culture and the protocol ????
                    if protocol_repeat_idx == 0 and stage_index == 0:
                        self.protocol.save_protocol(self.culture.protocols_number)
                        ### Update the culture object with the sequence of the stage
                        # create protocol index folder to save the protocol and stage data

                    sequence = stage.sequence
                    arduino_buffer = stage.ard_buffer # number of integers to be sent to the Arduino buffer - to sync with MaxOne
                    #print("Stage index:", stage_index, "|  Sequence length:", len(sequence), "|  Sequence repeats:", stage.sequence_repeats)
                    
                    print(f"Stage index:, {stage_index + 1} / out of {len(self.stages)}, |  Sequence length:, {len(sequence)}, |  Sequence repeats:, {stage.sequence_repeats} ")

                    print("Start-recording gate:",
                        "stage.recording=", stage.recording,
                        "stage.raw_recording=", getattr(stage, "raw_recording", None)
                        )


                    recording_started = False
                    if stage.recording and self.recorder:
                        self.update_protocol_name() # update the protocol name with the current date and time
                        
                        rp_str = f"rp_{protocol_repeat_idx + 1}"
                        si_str = f"si_{stage_index}"

                        prefix = (
                            f"{self.protocol_name}_"
                            f"{rp_str}_"
                            f"{si_str}_"
                            f"{stage.stim_type}"
                        )
                        
                        self.recorder.start_recording(prefix, raw_enabled=bool(getattr(stage, "raw_recording", False)))
                        recording_started = True
                        print(f"Started recording for stage {unique_stage_id} with prefix '{prefix}' at runProtocol.py")
                       
                    try:
                        stage.start_run_time = time.time() # time of the start of the stage run
                        self.protocol.save_sequence(unique_stage_id, sequence, stage.start_run_time) # save the sequence to the culture object
                        self.protocol.save_start_time(unique_stage_id, stage.start_run_time) # save_start_time in culture object protocolSet.py

                        # Handle Spontaneous: no Arduino/DMD; just wait for stim_time (in minutes)
                        if getattr(stage, "stim_type", None) == "Spontaneous":
                            total_wait_s = max(0, int(getattr(stage, "stim_time", 0) * 60))
                            end_time = datetime.now() + timedelta(seconds=total_wait_s)
                            print(f"Spontaneous stage: waiting {total_wait_s} s (no DMD / no Arduino) — ends at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            
            
                            deadline = time.time() + total_wait_s
                            while (not self.stop_event.is_set()) and (time.time() < deadline):
                                QThread.msleep(100) # Use QThread.msleep to remain responsive to stop requests
                            # Continue to next stage without touching DMD/Arduino
                            if stage.recording and self.recorder:
                                self.recorder.stop_recording()
                                recording_started = False
                                print("save Spontaneous stage completed.")
                            continue             

                        for seq_repeat in range(stage.sequence_repeats): # iterate over the number of repeats of the stage             

                            # use the sequence to create DMDArray of arduino_buffer size images (bound the Arduino buffer)
                            # running over the sequence with chuncks (steps) of arduino_buffer size
                            for i in range(0, len(sequence), arduino_buffer): # iterate over the length of arduino_buffer in the sequence
                                current_display_indices = sequence[i:i+arduino_buffer] # get the indices of the groups to be displayed
                                stage.create_DMDArray(current_display_indices) # create the DMDArray of images to be displayed on the DMD

                                if self.plot:
                                    if seq_repeat == 0 and i == 0:  # show only at the very first chunk of this stage
                                        imgs = self._extract_preview_images(stage.DMDArray, max_n=18)
                                        titles = [f"Stage {stage_index} | Img {k}" for k in range(len(imgs))]
                                        if imgs:
                                            self.plot_dmd.emit(imgs, titles)  # GUI thread will handle drawing

                                # print the size of the java array DMDArray
                                #print("DMDArray size:", stage.DMDArray.size())
                                self.core.load_slm_sequence(self.dmd_name, stage.DMDArray) # load the sequence to the DMD
                                self.msleep(len(current_display_indices)*4) # wait for the DMD to load the sequence - 4 ms per image
                                

                                if self.stop_event.is_set(): # User button pressed to stop the protocol
                                    print("Aborting the run")
                                    self.core.stop_slm_sequence(self.dmd_name)
                                    QThread.sleep(0.1)
                                    
                                    # Check if the DMD is responding and display black image
                                    try: # check if the DMD is responding
                                        device_label = self.core.get_property(self.dmd_name, "Label")
                                        print(f"Communication active: Device '{self.dmd_name}' responded with Label='{device_label}'.")    
                                        self.core.set_slm_image(self.dmd_name, self.black_image) # display black image
                                        self.core.display_slm_image(self.dmd_name) # display black image
                                    except Exception as e:
                                        # If an exception occurs, communication is likely disrupted
                                        print(f"Communication failed for device '{self.dmd_name}'. Error: {e}")         
                                    return

                                # Use Arduino to trigger the presentation of the images
                                arduino_display_indices = [x + 1 for x in sequence[i:i+arduino_buffer]] # adds 1 to the groups due to issues with Arduino encoding zeros digipins                                
                                # message = f"{arduino_display_indices},{self.stages[stage_index].groups_period},{self.stages[stage_index].on_time}\n"
                                # self.arduino.write(message.encode()) # Length of message is limited due to Arduino buffer overflow - ~19 numbers
                                # print(f"Message sent to Arduino: {message.strip()}") # uncheck to validate the message sent to Arduino
                            
                                self.core.start_slm_sequence(self.dmd_name) # start the sequence in external trigger mode needs TTL input (to Polygon and LED) to display the images
                                self.arduino_comm.send_message(arduino_display_indices, stage.groups_period, stage.on_time) # Upload the sequence part to Arduino and trigger the display of the images
                                response = self.arduino_comm.wait_for_sequence_end_blocking(stop_event=self.stop_event) # wait for the Arduino to finish the sequence

                                if response: # for test purposes - validate the response from Arduino
                                    #print(f"Arduino response: {response}")
                                    #print(f"num. presents {i}, of: {len(sequence)} completed by Arduino.")
                                    pass
                                else:
                                    print("Arduino wait exited (stopped or error).")
                                    break
                            # sequence cuts loop ends here

                            # at the end of each sequence:
                            self.core.stop_slm_sequence(self.dmd_name) # stop the sequence  - findout where to put it !!!!!!       
                            print(f"Sequence repeat {seq_repeat + 1}, out of: {self.stages[stage_index].sequence_repeats} completed by Arduino.")  

                        # seq_repeat loop ends here
                        print("Completed stage:", stage_index + 1, "recording:", stage.recording)


                    finally:

                        # Best-effort: stop SLM sequence so it never leaks into the next stage
                        try:
                            self.core.stop_slm_sequence(self.dmd_name)
                        except Exception:
                            pass

                        # Guaranteed recording stop for this stage
                        if recording_started and self.recorder:
                            print("Stopping recording for unique stage", unique_stage_id, "at runProtocol.py")
                            try:
                                self.recorder.stop_recording()
                                recording_started = False
                            except Exception as e:
                                print(f"Error stopping recording for unique stage {unique_stage_id}: {e}")

                    
                print(">>> FINISHED ALL STAGES in this repeat")
                # stages loop ends here
            # protocol repeats loop ends here

            # stop the recording if it was started
        except Exception as e:  # try catch for stage_index, stage loop
            print("Error in runProtocol:", e)
            traceback.print_exc()


        # if self.recorder:
        #     try:
        #         self.recorder.stop_recording()
        #         print("Final stop_recording() sent at protocol end.")
        #     except Exception as e:
        #         print(f"Error during final recording stop: {e}")

        end_time = time.time()
        duration = end_time - stage.start_run_time
        print("Protocol run duration:", duration)
        # print the expected protocol time
        comm_cycles = (len(sequence) / arduino_buffer) # number of communication cycles with Arduino per stage
        expected_time = len(sequence)*4/1000 + stage.stim_time*stage.sequence_repeats*60 + comm_cycles * self.arduino_comm_time  # in sec
        print("Expected stage time:", expected_time, "comm cycles:", comm_cycles)
        
        

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
    def _extract_preview_images(self, dmd_array, max_n=18):
        """Convert first max_n flattened patterns to HxW uint8 images."""
        H, W = self.slm_height, self.slm_width
        expect = H * W
        images = []

        # Supports both Java ArrayList (.size/.get) and Python list
        length = dmd_array.size() if hasattr(dmd_array, "size") else len(dmd_array)
        n = min(length, max_n)

        for i in range(n):
            flat = dmd_array.get(i) if hasattr(dmd_array, "get") else dmd_array[i]
            arr = np.asarray(flat, dtype=np.uint8).ravel(order='C')  # ravel() was used to add
            if arr.size != expect:
                # skip silently; you can log if needed
                continue
            images.append(arr.reshape(H, W))  # Use order='F' here only if you ravel(order='F')
        return images
    
    def update_protocol_name(self):
        """Replace the YYYYMMDD and time (_HHMM_ or _HHMMSS_) parts with current date/time.

        Expected (loosely): <chip>_<YYYYMMDD>_<HHMM or HHMMSS>_<rest...>
        We locate the date by matching the current year.
        The time is replaced only when it's between underscores.
        """
        if not self.protocol_name:
            re.error("Protocol name is empty. Cannot update with current date/time.")
            return self.protocol_name
            

        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M")      # you said H,m
        year = now.strftime("%Y")

        s = self.protocol_name

        # Replace the first date like YYYYMMDD that starts with current year
        s, n_date = re.subn(rf"{year}\d{{4}}", date_str, s, count=1)
        if n_date == 0:
            re.error(f"No date found in protocol name '{self.protocol_name}' to replace. Expected a date starting with the current year {year}.")
            self.protocol_name = s
            return self.protocol_name

        # Replace the first time between underscores AFTER the date: _HHMM_ or _HHMMSS_
        idx = s.find(date_str)
        prefix = s[:idx + len(date_str)]
        rest = s[idx + len(date_str):]

        # Replace digits only, requiring underscores on both sides
        rest, _ = re.subn(r"_(\d{4}|\d{6})_", f"_{time_str}_", rest, count=1)

        self.protocol_name = prefix + rest
        return self.protocol_name


