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
#                       self.culture.somaMasks = array of DMD images of each cell
#                       self.stages_table = dataframe of the protocol stages



import sys
import os
from datetime import datetime
import matplotlib.pyplot as plt
import cv2
from screeninfo import get_monitors
import tifffile # to save the cell masks unchanged (keep the indices)
import pandas as pd
import threading
import time
import pickle

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtCore import Slot
#from PySide6.QtGui import QImage, QPixmap, QScreen
# import QScreen from PySide6.QtGui to get the screen resolution


# Important:
# You need to run the following command to generate the ui_form.py file
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
import Camera, MovThread


import DMDCalibrate as dc  # Calibrate DMD position with camera image
import clickcollect as cc # click on the image to get the DMD coordinates
import numpy as np
import DetectCell # detect cells using opencv
import DetectCells_thread as dct # detect cells using cellpose
#from AllSomaStim import SomaStimulationWorker # Stimulate all deected somas
from AllSomaQTimer import SomaStimulationWorker
import GUI_createMasks as gcm
from culture_data import Culture # import the Culture class


#import CreateMasks
# import DetectSomas


class MainGui(QMainWindow, Ui_MainGui): # 
    def __init__(self):
        super(MainGui, self).__init__()
        
        self.setupUi(self) # setup the GUI from Ui_MainGui via the ui_form.py file
        self.stopProtocol.setVisible(False) # or True
        try:
            self.core = Core(convert_camel_case=False) # keep the Java names as they are in CamelCase not snake_case
            self.camera = Camera.getImage(self.core) # create the camera object
        except:
            # popout a window to show the error message
            self.show_error_message("core error","Micro-manager core cannot be initialized - open Micro-manager first")
            
        self.monitor = get_monitors()[0]
        #self.screen_width, self.screen_height = self.monitor.width, self.monitor.height

        
        # Connect all buttons to their functions
        self.snap.clicked.connect(self.snap_image) # Snap image
        self.live.clicked.connect(self.live_movie) # Live movie
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


        # create new working directory for the current session at D:\DATA. The directory name starts with Patterns followed by the current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        self.working_dir = r"D:\DATA\Patterns" + "\\Patt_" + current_date
        print("Working dir: ", self.working_dir)


        # create the working directory if it doesn't exist
        if not os.path.exists(self.working_dir): 
            print("Creating new working directory")
        
        # create the directories for the experimental files
            self.image_dir =  self.working_dir + "\\Images"
            self.DMD_dir = self.working_dir + "\\DMD"
            self.DMD_group_masks = self.working_dir + "\\DMD_Groups"
            self.culture_dir = self.working_dir + "\\Culture"
            
            os.makedirs(self.working_dir)
            os.makedirs(self.image_dir)
            os.makedirs(self.DMD_dir)
            os.makedirs(self.DMD_group_masks)
            os.makedirs(self.culture_dir)

            print("creating Culture")
            # initialize culture list variable and save it in the culture directory
            self.culture = Culture(current_date, self.culture_dir) # in the future might have couple of cultures in the same day
            self.culture.date = current_date
            self.culture.save()
            print("Culture created")

        # else: # to be deleted in the future - just for testing when starting the same session many times
        #     self.image_dir = self.working_dir + "\\Images" 
        #     self.DMD_dir = self.working_dir + "\\DMD"
        #     self.DMD_group_masks = self.working_dir + "\\DMD_Groups"

        # Create empty protocols table
        self.stages_table = pd.DataFrame()
        self.manualSequence = [] # list of lists of cells to be selected manually

        # Load the affine transformation matrix from the last saved calibration
        self.load_old_affine()

        # Access the ImageView placeholder and set data
        #self.imageView = self.ui.imageview # get the widget promoted to imageview object from the ui_form.py file
    def snap_image(self):
        frame = self.camera.snapImage(self.core)
        self.imageview.setImage(frame)

    def live_movie(self):
        # create MovieThread object if it doesn't exist
        if not hasattr(self, 'movie_thread'):
            self.movie_thread = MovThread.MovieThread(self)
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
        
        #self.show_error_message("title","error explanation")

        if not hasattr(self, 'affine_transform'):
            self.load_old_affine()
            self.frame = self.camera.snapImage(self.core) # take background image
            self.collector = cc.ClickCollector(self)
            self.collector.show()
            
        else:
            self.frame = self.camera.snapImage(self.core) # take background image
            self.collector = cc.ClickCollector(self)
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
        reply = QMessageBox.question(self, 'Old affine transform', 'Load old affine transform?', QMessageBox.Yes | QMessageBox.No)
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
        self.camera.binning = self.binning.currentText()
        self.core.setProperty(self.core.getCameraDevice(), "Binning", self.camera.binning)
        print("Binning updated: ", self.camera.binning)

    def exposure_set(self):
        # get the exposure value from the line edit
        print("current exposure: ", self.camera.exposure)
        self.exposure = float(self.exposureT.text())
        print("New exposure: ", self.exposure)

        self.core.setExposure(self.exposure)

    def detect_Cells(self):
        # get the number of frames to average from nAverage line edit
        self.averageN = int(self.nAverage.text())
        
        #  averaging the Images (every run)
        self.averageImage = self.camera.averageImages(self.core, self.averageN)
        
        # show the average image in the imageview
        self.imageview.setImage(self.averageImage)
        
        # save the averaged image (self.averageImage) at self.image_dir
        # if user opens the gui twice in the same day - it gives an error because the directory already exists
        # solve the problem...
        self.camera.saveImage(self.averageImage, self.image_dir)

        # Detecting cell bodies
        # get the min and max particle area from the line edits
        self.min_area = int(self.minsize.text())
        self.max_area = int(self.maxsize.text())
        self.cellDiameter = int(self.cellpose_diameter.text()) # cellpose_diameter

        detected_cells = DetectCell.detect_particles(self.averageImage, self.min_area, self.max_area)
        img_rotated = cv2.transpose(detected_cells)
        #img_rotated = cv2.flip(img_rotated, flipCode=0)  # flip vertically
        plt.imshow(img_rotated, cmap='gray')
        plt.title("Detected Neuronal Somas")
        
        fig_height, fig_width = img_rotated.shape[:2]
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


        # Soma detection using Cellpose
        self.cellpose_worker = dct.CellposeWorker(self.averageImage, self.cellDiameter) # cells image and diameter
        self.cellpose_worker.updatePlot.connect(self.cellPoseResult) # plot model output in main GUI thread - Cellpose
        self.cellpose_worker.finishedProcessing.connect(self.on_finished_processing)
        self.cell_mask = self.cellpose_worker.start()
        # when finished, the worker emits the finishedProcessing signal which is connected to the on_finished_processing function


    # cellpose model results plotting     -  TAKE OUT OF MAIN GUI AND NEST IN CELLPOSE WORKER
    def cellPoseResult(self, img_array, masks, flow_magnitude): # activated by updatePlot.connect(self.cellPoseResult) in detect_Cells function
        # plot the results of cellpose model
        self.masks = masks # the masks is image with unique integer value for each cell
        # save the masks image in the image_dir using tifffile.imsave('mask_output.tif', masks)
        

        #print("cellPoseResult: ", type(self.masks))
        self.binary_image = (masks > 0).astype(np.uint8) # binary mask of all cells 0/1
        # print to screen min max of all binary_image
        print("binary_image min:", self.binary_image.min(), "binary_image max:", self.binary_image.max())
        
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
            print("read unique cells:", (self.unique_cells))


        plt.figure(figsize=(12, 4))
        # Add title to the figure window
        plt.suptitle("Soma Detection Results", fontsize=16)

        plt.subplot(1, 4, 1)
        plt.imshow(img_array, cmap='gray')
        plt.title("Original Image")

        plt.subplot(1, 4, 2)
        plt.imshow(self.masks, cmap='tab20b')
        plt.title("Segmentation Masks-DetectCells_thread.py")

        plt.subplot(1, 4, 3)
        plt.imshow(self.binary_image, cmap='gray')
        plt.title("Binary  Masks")

        plt.subplot(1, 4, 4)
        plt.imshow(flow_magnitude, cmap='viridis')
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
    def save_masks(self):
        # create a mask image for each cell and save it in the image_dir as BMP in the DMD folder
        
        
        if not hasattr(self, 'affine_transform'):
            self.load_old_affine()

        gcm.make_masks(self)

        try:
            self.culture.somaMasks = gcm.affine_transform(self, self.binary_images, self.DMD_dir) # self.binary_images= array of binary images of each cell
        except:
            print("You are probably testing. Try deleting todays culture file ", self.culture_dir,  "and run again")

        self.culture.cellsNumber = len(self.culture.somaMasks)
        # self.transform_images # used in runProtocol.py ProtocolRunner
        self.culture.save()
        print("transform_images length:", len(self.culture.somaMasks), " images")



    def save_group_masks(self):
        # create a mask image for each group and save it in the image_dir as BMP in the DMD folder

        import RandomGroupCells as rgc# in development folder 
        

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
    def handle_groups_ready(self, groups):
        """Handle the groups_ready signal from the cell_picker_widg"""

        #self.manualGroups = groups
        print("maingui handle_groups_ready: ", groups)
        
        self.manualGroups = []
        for group in groups:
            self.manualGroups.append(group['cells'])
        print("manualGroups:", self.manualGroups)
        # create self.manualSequence which includes the list of the manualGroups and the remaining_cells.
        # the remaining_cells are the cells that were not selected manually
        print("type of self.unique_cells:", type(self.unique_cells))
        remaining_cells = self.unique_cells.tolist() # convert numpy array to list
        for group in self.manualGroups:
            for cell in group:
                remaining_cells.remove(cell)
        
        self.remainingManualCells = [[item] for item in remaining_cells] # list the remaining cells separately as groups of 1 cell each
        self.manualSequence = self.manualGroups + self.remainingManualCells
        print("manualSequence:", self.manualSequence)
        # update isManual
        

        
        # save the groups dictionary in the image_dir
        #np.save(self.image_dir + "/groups.npy", self.groups)


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
        self.protocol_window = protocol_set(self.stages_table, self.culture.cellsNumber)
        # wait until the protocol window is closed
        self.protocol_window.exec()
        self.stages_table = self.protocol_window.stages_table
        # get the stages_table from the protocol window
       
        print("MainGUI: ", self.stages_table)



    def load_protocol(self):
        from protocolLoader import ProtocolLoader as pl
        

        file_loader_dialog = pl(self)
        file_loader_dialog.signalOutData.connect(self.handleLoadedData) # signalOutData = Signal(object) # signal to send the dataframe to the main window
        file_loader_dialog.exec() # 

    # handle the dataframe returned from the file_loader_dialog (in load_protocol function)
    def handleLoadedData(self, data):
        import protocolSet as ps
        #print("handleLoadedData: ", data)
        self.stages_table = data # data is the protocol csv file as a dataframe returned from the file_loader_dialog
        self.prot = ps.ProtocolSet(self) # create the Protocol setting object
        self.prot.extract_protocol() # 
        print("self.prot.stages.numberCells: ", self.prot.stages[0].numberCells)
        print("self.prot.stages.repeats: ", self.prot.stages[0].sequenceRepeats)
        self.prot.create_stimulation_sequence() # in ps.ProtocolSet
        # print the size of sequences_images in prot object
        print("self.prot.stages.sequences_images[0] length: ", len(self.prot.sequences_images[0]))

    

    def run_protocol(self):
        from runProtocol import ProtocolRunner

        
        self.stopProtocol.setVisible(True) # make the stopProtocol button visible
        # check if a protocol is loaded
        if self.stages_table.empty:
            print("No protocol loaded")
            self.show_error_message("No protocol loaded","Load protocol from file")
        else:
            print("Protocol set")
            print(self.stages_table)

            # check that the protocol is not running
            #if not self.protocol_runner.isRunning():
                # run the protocol
            self.protocol_runner = ProtocolRunner(self)
            self.protocol_runner.start() # run the protocol
            #self.protocol_runner.protocolFinishSignal.connect(self.cleanupProtocolRunner)
            self.protocol_runner.finished.connect(self.cleanupProtocolRunner)
        
    def cleanupProtocolRunner(self):
        
        self.protocol_runner.deleteLater()
        # wait for two seconds
        time.sleep(2)

        print("Protocol runner deleted")
        self.stopProtocol.setVisible(False)
        

    def stop_protocol(self):
        self.protocol_runner.stop()
        
    def load_test_culture(self): # the culture is saved in the culture_dir created in the init function and updated in save_masks function
        # load the test culture from the pickle file in D:\DATA\Patterns\Patt_2023-11-28\Culture
        # create the file name
        fileName = "2023-12-19" + ".pkl"
        # load the object
        with open(os.path.join(r'D:\DATA\Patterns\Test_DO_NOT_DELETE\Culture', fileName), 'rb') as input:
            self.culture = pickle.load(input)
        print("Culture with", self.culture.cellsNumber , "cells loaded")

        


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainGui()
    widget.show()
    sys.exit(app.exec())
