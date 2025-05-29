# an example of how to set a new protocol using stage_dialog.py which enable the user to set the parameters of the protocol

# Important:
# You need to run the following command to generate the ui_form.py file
#     cd("G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI")
#     pyside6-uic Protocols.ui -o Protocols_ui.py


from PySide6.QtWidgets import QDialog, QMessageBox
from Protocols_ui import Ui_protocols

#import stage_dialog as sd
import pandas as pd
#from pandas.core.frame import DataFrame
import GroupCellsClickWidget as gcc
import tifffile


class protocol_set(QDialog, Ui_protocols):

# add sphinx documentation
    """ open a dialog to set a new protocol parameters
    Parameters
    ----------
    stages_table : pandas dataframe
        an empty dataframe to store the protocol parameters
    Returns
    -------
    stages_table : pandas dataframe
        a dataframe with the protocol parameters that includes the following columns:
        stimType: string, the type of stimulation (e.g. 'random', 'grouped', 'sequence')
        jitter: boolean, True or False
        backgroundFreq: float, the background frequency in Hz
        groupFreq: float, the stimulation frequency in Hz for each group (whole sequence cycle)
        groupSize: int, the number of cells in each group
        groupsNumber: int, the number of groups
        stimTime: int, the stimulation time in seconds
        onTime: int, the DMD on time in ms for each stimulation


    """



    def __init__(self, culture): # called by the main GUI to set the protocol parameters
        # can add variables following the self argument passing from the main window call. maingui line 475 - protocols_window
        # cellsNumber 
        super(protocol_set, self).__init__()
        self.setupUi(self) # setup the UI from Protocols_ui.py file (Qt Creator)
        self.stages_table = pd.DataFrame() # create an empty dataframe for the protocol
        # connect addStage button to add_new_stage method
        self.addStage.clicked.connect(self.add_new_stage)

        # connect removeStage button to remove_last_stage method
        self.removeStage.clicked.connect(self.remove_last_stage)

        # connect saveProtocol button to save_protocol method
        self.saveProtocol.clicked.connect(self.save_protocol)

        # connect closeWindow button to close method
        self.closeWindow.clicked.connect(self.close)

        # set the number of cells in the culture in ncells label
        self.ncells.setText(str(culture.cellsNumber)) # self.culture.cellsNumber

        # connect the output group button to the output_group method
        self.output_group.clicked.connect(self.select_output_group)

        self.culture = culture
        self.out_group = []
        self.df = pd.DataFrame()

    def get_stage_data(self):
        # Initialize the stage data dictionary
        stage_data = {
            "stim_type": self.stim_type.currentText(),
            "jitter": self.jitter.isChecked(),
            "background_freq": self.background_freq.text(),
            "groups_period": self.groups_period.text(),  # stimulation frequency in Hz for each group (whole sequence cycle)
            "group_size": self.group_size.text(),
            "groups_number": self.groups_number.text(),  # number of groups
            "stim_time": self.stim_time.text(),
            "on_time": self.on_time.text(),  # onTime
            "is_manual_sequence": self.is_manual_sequence.isChecked(),
            "prob_stim": self.prob_stim.isChecked(),
            
            # Other parameters...
        }

        # Check if self.out_group is not empty and contains a list
        if hasattr(self, 'out_group') and isinstance(self.out_group, list) and len(self.out_group) > 0:
            stage_data['output_group'] = self.out_group
        else:
            stage_data['output_group'] = []  # Default to an empty list if out_group is invalid

        return stage_data
    


    def add_new_stage(self):
        """ add a new stage to the protocol which includes the parameters of the protocol
        """

        # Get stage data from dialog and add to table of stages
        stage_data = self.get_stage_data()
        # print the stage data to listWidget
        self.listWidget.addItem(str(stage_data))

        # embed it into pandas dataframe
        df = pd.DataFrame([stage_data])
        
        # concat the new stage to the stages_table dataframe
        self.stages_table = pd.concat([self.stages_table, df], ignore_index=True)
        # print the stages_table dataframe
        print("Protocol design \n", self.stages_table)



    def remove_last_stage(self):
        # remove the last stage from stages_table dataframe
        self.stages_table = self.stages_table.drop(self.stages_table.tail(1).index)
        
        # remove the last stage from the listWidget
        self.listWidget.takeItem(self.listWidget.count()-1)
        # print the stages_table dataframe
        print("Protocol design", self.stages_table)


    def save_protocol(self):
        # save the stages_table dataframe to a csv file in Protocols folder
        from tkinter import simpledialog
        import datetime


        path = r"G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Protocols"
        # add prefix as the current date and time
        # get the current date and time from the system
        
        now = datetime.datetime.now()
        prefix = now.strftime("%Y%m%d_%H%M%S")

        # Open a dialog and ask the user to add a name for the protocol
        user_input = simpledialog.askstring("Protocol Name", "Please name the protocol:")
        # Print or use the input
        
        # get the protocol name from the dialog
        self.protocol_name = user_input
        # add the protocol name to the prefix
        prefix = prefix + "_" + self.protocol_name

        # save the stages_table dataframe to a csv file in Protocols folder
        self.stages_table.to_csv(path + "\\" + prefix + "_protocol.csv", index=False)

        
        # print the stages_table dataframe
        print("Protocol design", self.stages_table)
        #
        self.show_message("Protocol Saved", "The protocol is saved. You can close the window now.")
        
    def show_message(self, title, message, icon_type=QMessageBox.Information):
        
        msg = QMessageBox()
        if icon_type in [QMessageBox.NoIcon, QMessageBox.Question, QMessageBox.Information, QMessageBox.Warning, QMessageBox.Critical]:
            msg.setIcon(icon_type)
        else:
            raise ValueError("Invalid icon type")

        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()
        return  msg
    
    def select_output_group(self):
        # select the output group of cells that will not be stimulated

        # Click and group button - manual grouping of cells
        # Adding manual masks for cells
        print("Define the output-group of cells that will not be pattern stimulated")
        
        #import GroupCellsClick as gcc # sys.path.append at the beginning of the file solves the problem
        
        image_path = self.culture.image_dir + r"\mask_output.tif"
        read_mask_image = tifffile.imread(image_path)

        #cell_picker = gcc.CellPicker(read_mask_image) # 
        self.cell_picker_widg = gcc.CellPickerWidget(read_mask_image) # 
        self.cell_picker_widg.show()
        # when cell_picker_widg is closed, the groups are saved in the self.groups variable
        self.cell_picker_widg.cell_picker.groups_ready.connect(self.handle_output_group_ready) 

    # emitted signal from cell_picker_widg when the window is closed
    def handle_output_group_ready(self, out_group):
        """Handle the output_group_ready signal from the cell_picker_widg"""

        #self.manualGroups = groups
        print("protocol design handle_groups_ready: ", out_group[0])
        print("cell list", out_group[0]['cells']) # cell_list = out_group[0]['cells']

        self.out_group = out_group[0]['cells']
    

        

# create instance of protocol_set
# app = QApplication([])
# window = protocol_set()
# window.show()
# app.exec()
