# If problems occur:
#                       1. Turn on camera - wait 1/2 minute
#                       2. Restart computer (turn on Polygon and microscope stage)
#                       3. Run Micro-manager with CamPolyStage.cfg configuration file
# This Python file uses the following encoding: utf-8
# the form.ui file is created using QT Designer MainGUI project


# self object attributes:
#                       self.binary_images = list of binary images of each cell
#                       self.unique_cells =  number of somas in the image (np.array) = np.unique(self.masks) 1,2,3..... 
#                       self.masks = image with unique integer value for each cell (not normalized)
#                       self.affine_transform = affine transformation matrix from image to DMD
#                       self.DMD_images = list of DMD images each corresponding to a cell location
#                       self.groups = dictionary of groups of cells (keys are group numbers and values are the unique_cells values in the group)
#                       self.group_image = image with unique integer value for each GROUP
#                       self.rand_groups = dictionary of random groups of cells (keys are group numbers and values are the unique_cells values in the group)   
#                       self.group_sums = dictionary of group images (keys are group numbers and values are the group images)
#                       self.culture.soma_masks = array of DMD images of each cell
#                       self.stages_table = dataframe of the protocol stages

# Arduino loaded with file: MainGUI_Arduino_Trigger @ G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Arduino
# Connect to COM port 13
# Arduino pin 3 triggers the light source
# Arduino pin 4 triggers the MaxOne digipins
# Arduino pin 5 triggers the DMD


import sys
import os
from pathlib import Path
import re
from datetime import datetime
import matplotlib.pyplot as plt
import cv2
from screeninfo import get_monitors
import tifffile # to save the cell masks unchanged (keep the indices)
import pandas as pd
import threading
import time
import pickle
import traceback

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QInputDialog
from PySide6.QtCore import Slot
from PySide6.QtCore import Qt
#from PySide6.QtGui import QImage, QPixmap, QScreen
# import QScreen from PySide6.QtGui to get the screen resolution


# Important: QT GUI
# You need to run the following command to generate the ui_form.py file (in Python terminal at the (pattern) environment):
#     cd("G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI")
#     pyside6-uic form.ui -o form_ui.py
#     cd G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI  
#     pyside6-uic Protocols.ui -o Protocols_ui.py  # for the protocols window


from form_ui import Ui_MainGui # import the GUI class from the ui_form.py file compiled from the form.ui file

from pyqtgraph import ImageView
# add path for the Camera class
from pycromanager import Core

# sys.path.append("g:\\My Drive\\Research\\Projects\\Theory of cortical mind\\Object representation\\Software\\Python\\QT_GUI\\Develope")
# sys.path.append("g:\\My Drive\\Research\\Projects\\Theory of cortical mind\\Object representation\\Software\\Python\\QTlearn\\CamMovie")
from protocol_design import protocol_set # import the protocol_set class from the protocol_design.py file
# import Camera from QTlearn/CamMovie/ folder
import Camera, MovThread_signal
import Polygon

from protocolSet import ProtocolSet as ps # import the ProtocolSet class from the protocolSet.py file
import DMDCalibrate as dc  # Calibrate DMD position with camera image
import clickcollect as cc # click on the image to get the DMD coordinates
import numpy as np
import DetectCell # detect cells using opencv
import DetectCells_thread as dct # detect cells using cellpose
#from AllSomaStim import SomaStimulationWorker # Stimulate all deected somas
from AllSomaQTimer import SomaStimulationWorker
import GUI_createMasks as gcm
from culture_data import Culture # import the Culture class
import RandomGroupCells as rgc# in development folder 

import serial # for serial communication with the Arduino COM13 that triggers the DMD, light source, and MaxOne digipins.
from arduino_comm import ArduinoComm

from runProtocol import ProtocolRunner # run the protocol - create the sequence of images to be displayed on the DMD
from protocolLoader import ProtocolLoader as pl
from remote_recording_manager import RemoteRecordingManager  # for remote recording management
from stage_controller import StageController
# import CreateMasks
# import DetectSomas


class MainGui(QMainWindow, Ui_MainGui): # 
    def __init__(self):
        super(MainGui, self).__init__()
        
        self.setupUi(self) # setup the GUI from Ui_MainGui via the ui_form.py file
        self.imageview.ui.histogram.show() # show the histogram in the imageview widget
        self.stopProtocol.setVisible(False) # or True

        # Initialize core attributes
        self.core = None
        self.camera = None
        self.polygon = None
        self.monitor = None
        self.user_dir = r"D:\DATA\Patterns" # directory for the culture data
        self.working_dir = None
        self.image_dir = None
        self.DMD_dir = None # DMD pixel size (912, 1140)
        self.DMD_group_masks = None
        self.culture_dir = None
        self.culture = None
        self.stages_table = pd.DataFrame()
        self.manual_sequence = []    # list of lists of cells to be selected manually
        self.protocol = None # protocol object may have list of Stages
        self.mode = "test" # test or run
        self.soma_masks = [] # list of binary images of each cell
        self.binary_images = []
        self.binary_image_all = None
        self.light_click_pixels = 10 # size of the light click pixels in the mainGUI
        self.light_click_ms_time = 10
        self.img_rotated = None # image with detected cells rotated
        self.rotated_averageImage = None # average image rotated
        self.manualGroups = []
        self.recorder = None  # RemoteRecordingManager instance for recording
        self.chip_number = None  # MaxOne chip number
        self.pixel_to_stage_affine = None  # Affine transformation matrix from pixel to stage coordinates for mouse optogenetic stimulation

        self.monitor = get_monitors()[0]
        # Arduino loaded with file: Serial_trig_randvec_light_delay.ino
        self.arduino_port = 'COM13' # Arduino port to trigger the DMD, light source, and MaxOne digipins
        
        self.initialize()

    def initialize(self):
        self.initialize_core() # !!! initialize the core and camera !!!
        self.setup_directories()
        self.connect_buttons()
        
        # connect to Arduino
        #self.connect_arduino(port=self.arduino_port, baudrate=19200, timeout=2)
        self.arduino_comm = ArduinoComm.connect(port='COM13', baudrate=19200, timeout=2)
        self.arduino = self.arduino_comm.arduino # get the serial object from the ArduinoComm class
        
        # Load the affine transformation matrix from the last saved calibration
        self.load_old_affine()


    def initialize_core(self):
     try:
         self.core = Core(convert_camel_case=True)
         self.camera = Camera.getImage(self.core)
         self.polygon = Polygon.Polygon(self.core)
         #self.stage = self.core.getXYStageDevice() # Java case CamelCase
         self.xy_stage_device = self.core.get_xy_stage_device() # python case snake_case 
         self.xy_stage = StageController(self.core, self.xy_stage_device, self.stage_position) # xy stage interface object
         devices = [self.core.get_loaded_devices().get(i) for i in range(self.core.get_loaded_devices().size())]
         print(f"PycroManager connected. Devices: {devices}")
         self.update_stage_pos()
     except Exception as e:
         print("Failed to connect to Micro-Manager via PycroManager.")
         print("This may be due to an open Jupyter session or mismatched ZMQ version.")
         traceback.print_exc()
         QMessageBox.critical(self, "Core Error", "Failed to connect to Micro-Manager.\nIs another process (e.g. Jupyter) using Core?\n\nDetails:\n" + str(e))
         self.core = None

    def closeEvent(self, event):
        print("Closing MainGui.closeEvent-closing all connections and threads")
        if self.recorder:
            try:
                print("Closing server connection...")
                self.recorder.disconnect()
            except Exception as e:
                print(f"Error during disconnect: {e}")
        super().closeEvent(event)

        # Access the ImageView placeholder and set data
        #self.imageView = self.ui.imageview # get the widget promoted to imageview object from the ui_form.py file
    def snap_image(self):
        frame = self.camera.snap_image(self.core)
        self.imageview.setImage(frame) # self.imageview is the ImageView widget from the ui_form.py file

    def live_movie(self):
        # create MovieThread object if it doesn't exist
        if not hasattr(self, 'movie_thread'):
            self.movie_thread = MovThread_signal.MovieThread(self)
            print("live_movie - movie_thread created")
            self.stop_movie.clicked.connect(self.movie_thread.stop)
            self.movie_thread.start()
        self.movie_thread.is_running = True
        self.movie_thread.start()
        print("movie_thread pressed")

    def change_color_run(self):
        self.live.setStyleSheet("background-color: red")

    def change_color_stop(self):
        self.live.setStyleSheet("background-color: green")

    def DMD_Calibratiom(self):
        # show message box on how to calibrate the DMD
        self.show_error_message("DMD Calibration",
        """ 1. To perform DMD calibration, place a MIRROR under the objective.\n
            2. Turn on the Polygon input light.\n 
            3. Validate that the light path to the camera is clear (right turret filters).\n
            4. Validate that the image is in focus. Use MM to test that by projecting checkerboard (and turn it off!) \n
            5. maingui.py L210 \n
            6. Works for x4 or x5 objective. For higher needs to attenuate the light \n
            7. To test by steps go to: 
            Software\Python\PyQtGUI\SLMcalibrate.ipynb""")

        # run the affine transformation function
        dc.dmd_calibrate(self)
        self.affine_trans_old = self.core.affine_transform

        self.mouse_shoot.setEnabled(True)

    def mouse_DMD_shoot(self): 
        # to perform the affine transformation of image to stage coordinates use Affine_stage_image_GUI.py 
        if not hasattr(self, 'pixel_to_stage_affine'):
            affine_path = os.path.join(os.getcwd(), "affine_matrix.npy")
            if os.path.exists(affine_path):
                try:
                    self.pixel_to_stage_affine = np.load(affine_path)
                    print(f"Affine loaded from {affine_path}")
                except Exception as e:
                    print(f"Error loading affine_matrix.npy: {e}")
                    self.pixel_to_stage_affine = None
            else:
                print(f"Affine file not found at {affine_path}")
                self.pixel_to_stage_affine = None
        #self.show_error_message("title","error explanation")
        # get the light_click_pixels_size from the line edit
        self.light_click_pixels = int(self.light_click_pixels_size.text())
        self.light_click_ms_time = int(self.light_ms_time.text())

        if not hasattr(self, 'affine_transform'):
            self.load_old_affine()
            self.frame = self.camera.snap_image(self.core) # take background image
            self.collector = cc.ClickCollector(self)
            self.collector.show()
            
        else:
            self.frame = self.camera.snap_image(self.core) # take background image
            self.collector = cc.ClickCollector(self) # cc is the ClickCollector class from clickcollect.py file
            self.collector.show()

    def show_error_message(self, title, message, icon_type=QMessageBox.Critical):
        
        msg = QMessageBox()
        if icon_type in [QMessageBox.NoIcon, QMessageBox.Question, QMessageBox.Information, QMessageBox.Warning, QMessageBox.Critical]:
            msg.setIcon(icon_type)
        else:
            raise ValueError("Invalid icon type")
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()
        return  msg

    def load_old_affine(self):
        box = QMessageBox(self)
        box.setWindowTitle("Old affine transform")
        box.setText("Load old affine transform?")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        reply = box.exec()
       

        if reply == QMessageBox.Yes:
            # load old affine transformation
            file_path = r"G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Images\affine_transform.npy"
            self.affine_trans_old = np.load(file_path)
            self.affine_transform = self.affine_trans_old
            print("Previous affine transform loaded: ", self.affine_transform)
            #self.mouse_DMD_shoot()
            
        else:
            self.show_error_message("Calibrate DMD","Press the Calibrate DMD")
            

    def binning_set(self):
        # get the binning value from the combo box
        self.camera.binning = self.binning.currentText() # 
        self.core.set_property(self.core.get_camera_device(), "Binning", self.camera.binning)
        print("Binning updated: ", self.camera.binning)

    def exposure_set(self):
        # get the exposure value from the line edit
        print("current exposure: ", self.camera.exposure)
        self.exposure = float(self.exposureT.text())
        print("New exposure: ", self.exposure)

        self.core.set_exposure(self.exposure)

    def detect_Cells(self):
        # get the number of frames to average from nAverage line edit
        self.averageN = int(self.nAverage.text())
        
        #  averaging the Images (every run)
        self.averageImage = self.camera.averageImages(self.core, self.averageN)
        
        # show the average image in the imageview
        self.imageview.setImage(self.averageImage)
        
        # save the averaged image (self.averageImage) at self.image_dir
        # if user opens the gui twice in the same day - it gives an error because the directory already exists
        
        if self.image_dir is None:
            print("You already have a culture for today. Delete the folder and run again")
            # exit the function
            return

        print("Saving image to: ", self.image_dir)
        self.camera.saveImage(self.averageImage, self.image_dir)

        
        # Detecting cell bodies
        # get the min and max particle area from the line edits
        self.min_area = int(self.minsize.text())
        self.max_area = int(self.maxsize.text())
        self.cellDiameter = int(self.cellpose_diameter.text()) # cellpose_diameter


        self.rotated_averageImage = cv2.transpose(self.averageImage)
        detected_cells = DetectCell.detect_particles(self.rotated_averageImage, self.min_area, self.max_area)
        self.img_rotated = detected_cells
        
        # detected_cells = DetectCell.detect_particles(self.averageImage, self.min_area, self.max_area)
        # self.img_rotated = cv2.transpose(detected_cells)
        

        plt.imshow(self.img_rotated, cmap='gray')
        plt.title("Detected Neuronal Somas")

        fig_height, fig_width = self.img_rotated.shape[:2]
        x = 100
        y = 100
        manager = plt.get_current_fig_manager()
        manager.window.setGeometry(x, y, fig_width, fig_height)

        plt.show()

        # detect somas using Cellpose - conflicting error by use of OpenMP.
        # detected_somas = DetectSomas.detect_somas(self.averageImage, 10)
         # Create an instance of the worker
        print("Starting Cellpose processing, WAIT...")
        self.detectMsg = self.show_error_message("Soma detection","Cellpose processing, CLOSE THIS NOTIFICATION TO PROCEED", QMessageBox.Information)

        # print the size of the averageImage
        print("Average image before cellpose: ", self.averageImage[0, :3])


        # Soma detection using Cellpose
        #self.cellpose_worker = dct.CellposeWorker(self.rotated_averageImage, self.cellDiameter) # cells image and diameter
        
        self.cellpose_worker = dct.CellposeWorker(self.averageImage, self.cellDiameter) #  dct is  DetectCells_thread   cells image and diameter
        self.cellpose_worker.updatePlot.connect(self.cellPoseResult) # plot model output in main GUI thread - Cellpose
        self.cellpose_worker.finishedProcessing.connect(self.on_finished_processing)
        self.cell_mask = self.cellpose_worker.start()
        # when finished, the worker emits the finishedProcessing signal which is connected to the on_finished_processing function
        # print the size of the averageImage
        print("Average image following CellPose: ", self.averageImage[0, :3])


    # cellpose model results plotting     -  TAKE OUT OF MAIN GUI AND NEST IN CELLPOSE WORKER
    def cellPoseResult(self, img_array, masks, flow_magnitude): # activated by updatePlot.connect(self.cellPoseResult) in detect_Cells function
        # plot the results of cellpose model
        self.masks = masks # the masks is image with unique integer value for each cell
        # save the masks image in the image_dir using tifffile.imsave('mask_output.tif', masks)
        

        #print("cellPoseResult: ", type(self.masks))
        self.binary_image_all = (masks > 0).astype(np.uint8) # binary mask of all cells 0/1
        # print to screen min max of all binary_image
        print("binary_image min:", self.binary_image_all.min(), "binary_image max:", self.binary_image_all.max())
        
        # save the binary image of detected cells
        tifffile.imwrite(self.image_dir + "/mask_output.tif", self.masks)

        testing = True
        if testing:
            #unique_cells = np.unique(self.masks)
            #print("unique mask cells:", (unique_cells))
            # unique cells in the binary image
            #print("unique binary cells:", (np.unique(self.binary_image)))
            # read the saved binary image
            #self.read_mask_image = cv2.imread(self.image_dir + "/mask_output.tif", cv2.IMREAD_GRAYSCALE)
            self.read_mask_image = tifffile.imread(self.image_dir + "/mask_output.tif")
            # get the number unique cells from the binary image
            self.unique_cells = np.unique(self.read_mask_image)
            #print("read unique cells:", (self.unique_cells))


        plt.figure(figsize=(12, 4))
        # Add title to the figure window
        plt.suptitle("Soma Detection Results", fontsize=16)

        plt.subplot(1, 4, 1)
        
        plt.imshow(cv2.transpose(img_array), cmap='gray')
        plt.title("Original Image")

        plt.subplot(1, 4, 2)
        plt.imshow(cv2.transpose(self.masks), cmap='tab20b')
        plt.title("Segmentation Masks-DetectCells_thread.py")

        plt.subplot(1, 4, 3)
        plt.imshow(cv2.transpose(self.binary_image_all), cmap='gray')
        plt.title("Binary  Masks")

        plt.subplot(1, 4, 4)
        plt.imshow(cv2.transpose(flow_magnitude), cmap='viridis')
        plt.title("Flow Magnitude-cellPoseResult in MainGUI")

        plt.tight_layout()
        # move the figure window to the bottom right corner of the screen
        fig_width, fig_height = 1060, 460
        x = 20 #self.monitor.width - fig_width
        y = self.monitor.height - fig_height
        manager = plt.get_current_fig_manager()
        manager.window.setGeometry(x, y, fig_width, fig_height)


        plt.show()
        self.save_masks()

# saving binary images of each cell
    def save_masks(self): # called by cellPoseResult function
        # create a mask image for each cell and save it in the image_dir as BMP in the DMD folder
        
        
        if not hasattr(self, 'affine_transform'):
            self.load_old_affine()

        gcm.make_masks(self) # gcm is the GUI_createMasks.py file
        #print("save_masks: ", len(self.binary_images), " masks")

        
        try:
            gcm.affine_transform(self, self.binary_images, self.DMD_dir) # gcm is the GUI_createMasks.py file
            # self.soma_masks= array of binary images of each cell
            # The .affine_transform method saves the DMD images in the DMD folder

        except:
            print("You are probably testing. Try deleting todays culture file ", self.culture_dir,  "and run again")

        self.culture.cellsNumber = len(self.soma_masks)
        #self.culture.unique_cells = self.unique_cells # save the unique cells in the culture object
        # self.transform_images # used in runProtocol.py ProtocolRunner
        self.culture.save() # save the culture object with the new number of cells
        
        #print("transform_images length:", len(self.soma_masks), " images")



    def save_group_masks(self):
        # create a mask image for each group and save it in the image_dir as BMP in the DMD folder


        # get the group size from the line edit
        self.rand_group_size = int(self.group_size.text())

        #[self.group_image, self.rand_groups] = rgc.group_cells_in_image(self.masks, self.rand_group_size) # 
        rgc.group_cells_in_image(self) #
        
      
        image_arrays = list(self.group_sums.values()) # list of the group images from the dictionary self.group_sums
        stacked_group_images = np.stack(image_arrays, axis=0)
        gcm.affine_transform(stacked_group_images, self.DMD_group_masks)

        # create masks for each group
        
        
# Click and group button - manual grouping of cells
    def manual_masks(self):
        # Adding manual masks for cells
        print("groupCells clicked")
        
        #import GroupCellsClick as gcc # sys.path.append at the beginning of the file solves the problem
        import GroupCellsClickWidget as gcc
        
        image_path = self.image_dir + r"\mask_output.tif"
        read_mask_image = tifffile.imread(image_path)

        #cell_picker = gcc.CellPicker(read_mask_image) # 
        self.cell_picker_widg = gcc.CellPickerWidget(read_mask_image) # 
        self.cell_picker_widg.show()
        # when cell_picker_widg is closed, the groups are saved in the self.groups variable
        self.cell_picker_widg.cell_picker.groups_ready.connect(self.handle_groups_ready) 

        
# emitted signal from cell_picker_widg when the window is closed
# handles the manual selected groups
    def handle_groups_ready(self, groups):
        """Handle the groups_ready signal from the cell_picker_widg"""
        self.manualGroups = []  # Initialize manualGroups
        print("maingui handle_groups_ready: ", groups)
        
        for group in groups:
            self.manualGroups.append(group['cells'])
        print("manualGroups:", self.manualGroups)
        # create self.manual_sequence which includes the list of the manualGroups and the remaining_cells.
        # the remaining_cells are the cells that were not selected manually
        # print("type of self.culture.unique_cells:", type(self.culture.unique_cells))
        # print("type of self.unique_cells:", type(self.unique_cells))
        
        
        # #remaining_cells = self.unique_cells.tolist() # convert numpy array to list
        # remaining_cells = list(range(len(self.protocol.images)))
        # for group in self.manualGroups:
        #     for cell in group:
        #         remaining_cells.remove(cell)
        
        # self.remainingManualCells = [[item] for item in remaining_cells] # list the remaining cells separately as groups of 1 cell each
        # self.manual_sequence = self.manualGroups + self.remainingManualCells # NOT IS USE! create the manual sequence a list of the manual groups and the remaining cells as groups of ones.
        # # print("manual_sequence:", self.manual_sequence)
        
        # # update isManual
        



    def on_finished_processing(self):
    # Handle post-processing after cellpose is done
        print("MainGUI Cellpose processing finished")
        # the thread is stopped after finishing the run() method
        # close the detectMsg message box
        self.detectMsg.close()

    # stimulation of all detected somas
    def stim_from_dir(self):
        if not hasattr(self, 'affine_transform'):
            self.load_old_affine()

        # create all the DMD images from the masks files
        if not hasattr(self, 'DMD_images'):
            print("Load DMD images from the DMD_dir")
            self.DMD_images = []
            # list all the files in the DMD_dir
            DMD_files = os.listdir(self.DMD_dir)
            sorted_file_names = sorted(DMD_files, key=lambda x: int(x.split(".")[0]))

            # create the DMD_images array
            for filen in sorted_file_names:
                if filen.endswith(".bmp"):
                    # read the image and append
                    image = cv2.imread(os.path.join(self.DMD_dir, filen), cv2.IMREAD_GRAYSCALE)
                    self.DMD_images.append(image)

                    # print the size the DMD_images array
            print(len(self.DMD_images), " :", filen, image.shape)
            # add the images to the gui
        
        # print the size of the first image
        print("DMD_images[0] shape:", self.DMD_images[0].shape)

        self.soma_worker = SomaStimulationWorker(self)
        self.soma_worker.start()
        self.soma_worker.finishedStimulation.connect(self.handle_soma_stimulation_finished)

    def handle_soma_stimulation_finished(self):
        # Handle the SomaStimulationWorker  completion here
        print("AllSomaStims.py - Soma stimulation finished.")
        del self.soma_worker


# open protocols window and get info from user
    def protocols_window(self):
        """ Opens the protocols window and gets the protocol from the user"""

        
        # Opens the protocol window
        self.protocol_window = protocol_set(self.culture) # self.culture.cellsNumber

        # Connect the `finished` signal to a callback to handle post-dialog actions
        self.protocol_window.finished.connect(self.on_protocol_window_closed)
        
        # Show the protocol window non-modally
        self.protocol_window.show()


    def on_protocol_window_closed(self):
        """Callback for when the protocol window is closed"""
        # Get the updated stages_table from the protocol window
        self.stages_table = self.protocol_window.stages_table
        # look for the output_group column in the stages_table ? 
        print("MainGUI: stages ", self.stages_table)



    def load_protocol(self):
        # load the protocol from a file
        
        file_loader_dialog = pl(self)
        file_loader_dialog.signalOutData.connect(self.handleLoadedData) # signalOutData = Signal(object) # signal to send the dataframe to the main window
        file_loader_dialog.exec() # 

    # handles the dataframe returned from the file_loader_dialog (in load_protocol function)
    def handleLoadedData(self, data):
        # Set all the parameters for running the protocol 

        #print("handleLoadedData: ", data)
        self.stages_table = data # data is the protocol csv file as a dataframe returned from the file_loader_dialog
        self.protocol = ps(self) # create the Protocol setting object by protocolSet.py file
        self.protocol.extract_protocol() # 
        # print("self.protocol.stages.numberCells: ", self.protocol.stages[0].number_cells)
        # print("self.protocol.stages.repeats: ", self.protocol.stages[0].sequence_repeats)

        # print the size of sequences_images in prot object
        # for i in range(len(self.protocol.stages[0].sequences_images)):
        #     print("self.protocol.stages.sequences_images ", i, " length: ", len(self.protocol.sequences_images[i]))

    

    def run_protocol(self):
        """ Following button press run the protocol """
        
        
        self.stopProtocol.setVisible(True) # make the stopProtocol button visible
        # check if a protocol is loaded
        if self.stages_table.empty:
            print("No protocol loaded")
            self.show_error_message("No protocol loaded","Load protocol from file")
        else:
            print("Protocol set")
            print(self.stages_table)

            
            # run the protocol
            self.protocol_runner = ProtocolRunner(self)
            self.protocol_runner.start() # run the protocol
            #self.protocol_runner.protocolFinishSignal.connect(self.cleanupProtocolRunner)
            self.protocol_runner.finished.connect(self.cleanupProtocolRunner)
        
    def cleanupProtocolRunner(self):
        
        self.protocol_runner.deleteLater()
        

        print("Protocol runner deleted")
        self.stopProtocol.setVisible(False)
        # !!! save and update the culture object with the new protocol
        

    def stop_protocol(self):
        self.protocol_runner.stop()
        # wait to the protocol_runner to finish
        self.protocol_runner.wait() # wait for the thread to finish
        self.cleanupProtocolRunner()
        
    def load_test_culture(self): 
        # the culture is saved in the culture_dir created in the init function and updated in save_masks function
        # load the test culture from the pickle file in D:\DATA\Patterns\Patt_2023-11-28\Culture
        # create the file name
        fileName = "2023-12-19" + ".pkl"
        # load the object
        with open(os.path.join(r'D:\DATA\Patterns\Test_DO_NOT_DELETE\Culture', fileName), 'rb') as input:
            self.culture = pickle.load(input)
            
        print("Culture with", self.culture.cellsNumber , "cells loaded")
        
        self.working_dir = r"D:\DATA\Patterns\Test_DO_NOT_DELETE"
        self.image_dir =  self.working_dir + "\\Images"
        self.DMD_dir = self.working_dir + "\\DMD"
        self.DMD_group_masks = self.working_dir + "\\DMD_Groups"
        self.culture_dir = self.working_dir + "\\Culture"
        print("Updated all exp directories: ", self.image_dir)
        self.read_mask_image = tifffile.imread(self.image_dir + "/mask_output.tif")
        self.unique_cells = np.unique(self.read_mask_image)
       

    def load_culture(self):
    

        # load the culture object from the Culture directory
        print("Loading culture object from: ", self.culture_dir)
        culture_path = Path(self.culture_dir)
        pkl_files = sorted(culture_path.glob('*.pkl'), key=os.path.getmtime, reverse=True) 
        if pkl_files:
            try:
                with open(pkl_files[0], 'rb') as f: # load the last created culture object
                    self.culture = pickle.load(f)
                    print(vars(self.culture))
                    print("cellsNumber: ", self.culture.cellsNumber)    
                    print(f"Culture object loaded from {pkl_files[0]}")
                    if not isinstance(self.culture, Culture):
                        self.show_error_message("Culture load", "No Culture object loaded.")
                        return
            except Exception as e:
                print(f"Error loading culture: {e}")
        
        # load the soma masks from the DMD directory
        self.soma_masks = []
        DMD_files = os.listdir(self.DMD_dir)
        sorted_file_names = sorted(DMD_files, key=lambda x: int(x.split(".")[0]))
        # create the DMD_images array
        for filen in sorted_file_names:
            if filen.endswith(".bmp"):
                # read the image and append
                image = cv2.imread(os.path.join(self.DMD_dir, filen), cv2.IMREAD_GRAYSCALE) # Read DMD sized images
                self.soma_masks.append(image)
                # print the size the DMD_images array
        print(f"cell_number: {len(self.soma_masks)}, image size: {image.shape}")

        protocols_dir = os.path.join(self.culture_dir, "Protocols")
        pattern = re.compile(r'^Protocol_(\d+)$') # matches "Protocol_1", "Protocol_2", etc.
        # Get all existing protocol indices
        existing_indices = []
        for name in os.listdir(protocols_dir):
            match = pattern.match(name)
            if match:
                existing_indices.append(int(match.group(1)))

        next_index = max(existing_indices, default=0) + 1
        new_folder_name = f"Protocol_{next_index}"
        new_folder_path = os.path.join(protocols_dir, new_folder_name)
        os.makedirs(new_folder_path)
        self.culture.current_protocol_dir = new_folder_path

        print(f"Created new protocol directory: {new_folder_path}")




    def setup_directories(self):

        ask = QMessageBox.question(
            self, 'Load existing culture',
            'Do you want to load existing culture?',
            QMessageBox.Yes | QMessageBox.No
        )

        if ask == QMessageBox.Yes:
            selected_dir = QFileDialog.getExistingDirectory(self, "Select Directory", self.user_dir)
            if selected_dir:
                self.working_dir = os.path.normpath(selected_dir)
                print("Selected directory:", self.working_dir)
                self._define_subdirectories()
                self.load_culture() # load the culture object from the Culture directory
            else:
                print("No directory selected - try again") 
                #self._create_new_directories()
                
        else:
            self._create_new_directories()


    def _define_subdirectories(self):
        base = self.working_dir
        self.image_dir = os.path.join(base, "Images")
        self.DMD_dir = os.path.join(base, "DMD")
        self.Squares = os.path.join(self.DMD_dir, "Squares") # directory for the squares images
        self.DMD_group_masks = os.path.join(base, "DMD_Groups")
        self.culture_dir = os.path.join(base, "Culture")
        self.protocols_directory = os.path.join(self.culture_dir, "Protocols")   


    def _create_new_directories(self):
        self.chip_number, ok = QInputDialog.getText(self, 'Chip Number', 'Enter the MaxOne chip number:')
        if not (ok and self.chip_number):
            print("Chip number input cancelled.")
            return

        self.working_dir = os.path.join(self.user_dir, self.chip_number)

        if os.path.exists(self.working_dir):
            self.show_error_message("Directory exists", "The directory already exists. Please select a different directory.")
            print("Directory already exists. Please select a different directory.")
            return

        self._define_subdirectories()

        for path in [
            self.working_dir,
            self.image_dir,
            self.DMD_dir,
            self.DMD_group_masks,
            self.culture_dir,
            self.protocols_directory
        ]:
            os.makedirs(path, exist_ok=False)

        self.culture = Culture(self.working_dir)  # the object is created by culture_data.py file
        # Future support for multiple cultures per day
        print("Directories created:")
        print("\n".join([
            self.working_dir,
            self.image_dir,
            self.DMD_dir,
            self.DMD_group_masks,
            self.culture_dir
        ]))



    def connect_buttons(self):
        self.snap.clicked.connect(self.snap_image)
        self.live.clicked.connect(self.live_movie)
        self.live.clicked.connect(self.change_color_run)
        self.stop_movie.clicked.connect(self.change_color_stop) # Stop movie
        self.somasStims.clicked.connect(self.stim_from_dir) # connect somsStims to AllSomaStim function
        self.DMD_Calibrate.clicked.connect(self.DMD_Calibratiom) # DMDCalibrate
        self.mouse_shoot.clicked.connect(self.mouse_DMD_shoot) # mouse_shoot clicked
        self.binning.currentIndexChanged.connect(self.binning_set) # connect binning combo box to binning function
        self.exposureT.returnPressed.connect(self.exposure_set) # connect exposure line edit to exposure function
        self.detectCells.clicked.connect(self.detect_Cells) # connect detectCells button to detectCells function
        self.ManualGroup.clicked.connect(self.manual_masks) # connect ManualGroup button to manual_masks function
        self.RandGroup.clicked.connect(self.save_group_masks) # connect RandGroup button to random_masks function
        self.createProtocol.clicked.connect(self.protocols_window) # Opens create protocol window # connect self.protocolsB button to protocols window open
        self.loadProtocol.clicked.connect(self.load_protocol) # connect loadProtocol button to load protocol from file
        self.runProtocol.clicked.connect(self.run_protocol) # connect runProtocol button to run protocol
        self.stopProtocol.clicked.connect(self.stop_protocol) # connect stopProtocol button to stop protocol
        self.loadTest.clicked.connect(self.load_test_culture) # connect loadTest button to load test culture
        self.testGroup.clicked.connect(self.test_group_select) # connect testGroup button to test_group_select function
        self.update_stage.clicked.connect(self.update_stage_pos) # connect update_stage button to update_stage function
        self.zero_stage.clicked.connect(self.zero_stage_pos) # connect zero_stage button to zero_stage function
        self.move_stage.clicked.connect(self.move_stage_pos) # connect move_stage button to move_stage function
        self.record_button.clicked.connect(self.init_recording) # connect recording button to init_recording function

    def init_recording(self):
        if self.recorder is not None:
            print("Recorder is already initialized and connected.")
            return

        print("Initializing RemoteRecordingManager...")
        # check if the chip number is set
        if not hasattr(self, 'chip_number') or not self.chip_number:
            self.chip_number = self.working_dir.split(os.sep)[-1]  # Use the last part of the working directory as chip number
        print("chip number was artificially set")

        self.recorder = RemoteRecordingManager(
            host="132.77.68.106",
            port=7215,
            save_dir="/home/mxwbio/Data/recordings",
            file_prefix=self.chip_number  # file name + stage index
        )

        try:
            self.recorder.connect()
            time.sleep(1)  # wait for connection to stabilize
            print("Recorder connected successfully.")
            print(f"Recorder save directory: {self.recorder.save_dir} , file prefix: {self.recorder.file_prefix}")
        except Exception as e:
            print(f"Error connecting to recorder: {e}")
            self.recorder = None


    def connect_arduino(self, port='COM13', baudrate=19200, timeout=2):

        try:
            self.arduino = serial.Serial(port, baudrate, timeout=timeout)
            print("Arduino connected.")
        except serial.SerialException as e:
            print(f"Error connecting to Arduino: {e}")
            self.arduino = None
            return False
        return True

    def test_group_select(self): # Output_group
        # Let the user select the TEST (output layer) group of cells that will not be patterned stimulated.
        # The user will click on the cells to be selected and then press the group button
        # The selected cells will be saved in the self.testGroupCells variable
        pass

    def get_stage_position(self):
        self.xy_stage.get_position()


    def update_stage_pos(self):
        # Update the microscope stage position in the GUI
        self.xy_stage.update_gui()

        
    def zero_stage_pos(self):
        # set the current poisition as zero position
        self.xy_stage.zero()

    def move_stage_pos(self):
    # read position from text field and Move the stage to a specified position
        
        x = int(self.xpos.text())
        y = int(self.ypos.text())
        self.xy_stage.move_to(x, y)
       
        


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainGui()
    widget.show()
    sys.exit(app.exec())
