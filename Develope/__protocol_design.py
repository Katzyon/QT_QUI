# an example of how to set a new protocol using stage_dialog.py which enable the user to set the parameters of the protocol

# Important:
# You need to run the following command to generate the ui_form.py file
#     cd("G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI")
#     pyside6-uic Protocols.ui -o Protocols_ui.py


from PySide6.QtWidgets import QDialog
from Protocols_ui import Ui_protocols

#import stage_dialog as sd
import pandas as pd
#from pandas.core.frame import DataFrame


class protocol_set(QDialog, Ui_protocols):
#class protocol_set(QMainWindow, Ui_protocols):
    def __init__(self, stages_table): # can add variables following the self argument passing from the main window call.
#   def __init__(self, masks, group_sums, DMD_images, parent=None):
        super(protocol_set, self).__init__()
        self.setupUi(self) # 
        self.stages_table = pd.DataFrame() # create an empty dataframe for the protocol
        # connect addStage button to add_new_stage method
        self.addStage.clicked.connect(self.add_new_stage)

        # connect removeStage button to remove_last_stage method
        self.removeStage.clicked.connect(self.remove_last_stage)

        # connect saveProtocol button to save_protocol method
        self.saveProtocol.clicked.connect(self.save_protocol)

        # connect closeWindow button to close method
        self.closeWindow.clicked.connect(self.close)

        self.df = pd.DataFrame()

    def get_stage_data(self):
        # retrieve data from the dialog fields: stimType (QComboBox), randFreq (QLineEdit), jitter (QCkeckBox), groupFreq (QLineEdit), groupSize (QLineEdit), stimTime (QLineEdit) 
        # and 
        return {

            # the parameters comes from Protocols.ui file (Qt Creator) translated into Protocols_ui.py file using pyside6-uic command
            "stimType": self.stimType.currentText(),
            "jitter": self.jitter.isChecked(),
            "backgroundFreq": self.backgroundFreq.text(),
            "groupFreq": self.groupFreq.text(), # stimulation frequency in Hz for each group (whole sequence cycle)
            "groupSize": self.groupSize.text(),
            "groupsNumber": self.groupsNumber.text(), # number of groups
            "stimTime": self.stimTime.text(),
            # Other parameters...   
        }
    


    def add_new_stage(self):
        # Get stage data from dialog and add to table of stages
        stage_data = self.get_stage_data()
        # print the stage data to listWidget
        self.listWidget.addItem(str(stage_data))

        # embed it into pandas dataframe
        df = pd.DataFrame([stage_data])
        
        # concat the new stage to the stages_table dataframe
        self.stages_table = pd.concat([self.stages_table, df], ignore_index=True)
        # print the stages_table dataframe
        print("Protocol design", self.stages_table)



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
        user_input = simpledialog.askstring("Protocol Name", "Please protocol name:")
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
        


# create instance of protocol_set
# app = QApplication([])
# window = protocol_set()
# window.show()
# app.exec()
