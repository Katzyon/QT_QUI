


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
import shutil



class ProtocolSet():
        """ Class for setting the protocol parameters before running it"""
    
    
        def __init__(self, gui):
            super(ProtocolSet, self).__init__()
            self.roi_mask_path = getattr(gui, "roi_dmd_mask_path", None)
            self.roi_directory = getattr(gui, "ROI_dir", None)
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
            self.repeats = gui.n_protocol_repeats
            self.roi_directory = getattr(gui, "ROI_dir", None)
            
            print("init protocol set", self.current_protocol_dir)

        def __getstate__(self):
            state = self.__dict__.copy()
            state.pop("images", None)
            #state.pop("gui", None)  # NEW: MainGui is not picklable
            return state

        def extract_protocol(self): # called from maingui.py following the "Load Protocol" button
            """ Extract the protocol from the dataframe before setting it. Called from maingui.py following the "Load Protocol" button"""

            if "use_roi" not in self.stages_table.columns:
                self.stages_table["use_roi"] = False
            if "dt" not in self.stages_table.columns:
                self.stages_table["dt"] = 0.0
            if "IPI" not in self.stages_table.columns:
                self.stages_table["IPI"] = 0.0
            if "stim_type" in self.stages_table.columns:
                self.stages_table["stim_type"] = self.stages_table["stim_type"].replace({"DTSP": "STDP"})

            """Extract and set up the protocol from a DataFrame, initiated from a GUI."""
            self.headers = list(self.stages_table.columns)

            self.data = self.stages_table.values.tolist()
            print("protocolSet - data:", self.data)
            self.n_rows = len(self.data)
            self.number_cells = len(self.images)

            for index, row in self.stages_table.iterrows():
                print(f"stage number: {index}, user input row:s \n{row}")
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
            stage.stim_type = str(row['stim_type']).replace('DTSP', 'STDP')

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
            stage.stim_time = float(row['stim_time'])
            stage.dt = float(row.get('dt', 0.0))
            stage.IPI = float(row.get('IPI', 0.0))
            stage.Tmin = float(stage.stim_time)
            stage.cycle_time = stage.groups_period
            # set the recording flag from the boolean checkbox in the GUI 
            stage.recording = bool(row['record_stage'])
            stage.raw_recording = bool(row.get("raw_recording", False)) # whether to enable raw-trace recording for this stage (if False, only maxlab spikes will be recorded)
            stage.use_roi = bool(row.get("use_roi", False))
            stage.roi_mask_path = getattr(self, "roi_mask_path", None)


            if stage.stim_type == "STDP":
                if not self.roi_directory:
                    raise FileNotFoundError(
                        "ROI directory is not defined."
                    )

                stage.stdp_mask_1_path = os.path.join(
                    self.roi_directory,
                    "stdp_roi1_mask.bmp",
                )

                stage.stdp_mask_2_path = os.path.join(
                    self.roi_directory,
                    "stdp_roi2_mask.bmp",
                )

                stage.use_stdp_masks = bool(row.get("use_roi", False))



            if stage.use_roi:
                if stage.stim_type == "STDP":
                    missing = [
                        path
                        for path in (
                            stage.stdp_mask_1_path,
                            stage.stdp_mask_2_path,
                        )
                        if not path or not os.path.isfile(path)
                    ]

                    if missing:
                        raise FileNotFoundError(
                            "STDP mask files are missing. "
                            "Create the STDP masks in Simple DMD Stim first.\n"
                            + "\n".join(missing)
                        )

                elif not stage.roi_mask_path or not os.path.isfile(stage.roi_mask_path):
                    raise FileNotFoundError(
                        "ROI mask file is missing."
                    )



            print("protocolSet number of groups:", stage.groups_number)

            if stage.is_manual:
                # If manual sequence is selected, use the manual_sequence from the GUI
                #stage.sequence = self.manual_sequence # manual sequence ??? 
                stage.groups = self.manual_groups
                stage.groups_number = len(stage.groups) # number of groups in the manual sequence
                print("protocolSet groups:", stage.groups)
                print("protocolSet number of groups:", stage.groups_number)
                print("protocolSet Manual groups:", stage.manual_groups)

            stage.use_roi = bool(row.get("use_roi", False))
            stage.roi_mask_path = getattr(
                self,
                "roi_mask_path",
                None,
            )

            if stage.stim_type == "STDP" and stage.use_roi:
                self._snapshot_stdp_masks(stage)

            if stage.use_roi and stage.is_manual:
                raise ValueError(
                    "Invalid stage configuration: both Manual Groups "
                    "and ROI are enabled. Choose only one."
                )   

            stage.create_sequence_pointer() # 
            stage.calc_interMaskInterval()
            return stage     


                # get the stimulation type (stimType)
                
                # (0, "Random") - randomize the sequence every iteration
                # (1,"Group only stim.") - stimulate only the groups in the sequence (no single cells/remaining cells)
                # (2, "Order") - repeat the same sequence over and over
                # (3, "Test") - run the sequence under calcium imaging
                # (4, "Spontaneous") - randomize stimulation to all cells in the culture (no groups)
                #print("stimType:", stage.stimType)

        
        def snapshot_stdp_masks(self, stage, protocol_dir):
            """
            Copy the current STDP ROI masks into the protocol-specific directory.
            """
            if stage.stim_type != "STDP" or not stage.use_roi:
                return

            if not self.roi_directory:
                raise FileNotFoundError(
                    "ROI directory is not defined."
                )

            source_mask_1 = os.path.join(
                self.roi_directory,
                "stdp_roi1_mask.bmp",
            )

            source_mask_2 = os.path.join(
                self.roi_directory,
                "stdp_roi2_mask.bmp",
            )

            missing = [
                path
                for path in (source_mask_1, source_mask_2)
                if not os.path.isfile(path)
            ]

            if missing:
                raise FileNotFoundError(
                    "STDP ROI masks are missing. "
                    "Create the STDP masks in Simple DMD Stim first:\n"
                    + "\n".join(missing)
                )

            os.makedirs(protocol_dir, exist_ok=True)

            destination_mask_1 = os.path.join(
                protocol_dir,
                f"stage_{stage.number}_stdp_roi1_mask.bmp",
            )

            destination_mask_2 = os.path.join(
                protocol_dir,
                f"stage_{stage.number}_stdp_roi2_mask.bmp",
            )

            shutil.copy2(
                source_mask_1,
                destination_mask_1,
            )

            shutil.copy2(
                source_mask_2,
                destination_mask_2,
            )

            stage.stdp_mask_1_path = destination_mask_1
            stage.stdp_mask_2_path = destination_mask_2

            print(
                "STDP masks copied:",
                destination_mask_1,
                destination_mask_2,
            )


        def snapshot_all_stdp_masks(self):
            """
            Copy STDP masks for every ROI-based STDP stage into the
            current protocol directory.
            """
            if not self.current_protocol_dir:
                raise FileNotFoundError(
                    "Current protocol directory is not defined."
                )

            for stage in self.stages:
                if stage.stim_type == "STDP" and stage.use_roi:
                    self.snapshot_stdp_masks(
                        stage,
                        self.current_protocol_dir,
                    )
        

        def prepare_protocol_directory(self, protocols_number):
            self.current_protocol_dir = os.path.join(
                self.protocols_directory,
                f"Protocol_{protocols_number}",
            )

            os.makedirs(
                self.current_protocol_dir,
                exist_ok=True,
            )

            return self.current_protocol_dir

 
        def save_protocol(self, protocols_number):
            if not self.current_protocol_dir:
                self.prepare_protocol_directory(
                    protocols_number
                )

            file_name = f"protocol_{protocols_number}.pkl"
            file_path = os.path.join(
                self.current_protocol_dir,
                file_name,
            )

            with open(file_path, "wb") as culture_file:
                pickle.dump(self, culture_file)

            print(
                f"Protocol {protocols_number} saved to "
                f"'{file_path}'"
            )



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
                    

