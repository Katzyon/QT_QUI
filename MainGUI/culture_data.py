import os
import pickle

class Culture:
    """This class represents a culture. Called during main GUI initialization"""
    def __init__(self, date, directory):
        self.date = date
        self.protocols = []
        self.cellsNumber = 0
        self.saveDirectory = directory
        self.somaMasks = None
        self.transform_images = None
        self.groupID = None # 



    def save(self):
        
        # create the file name
        fileName = self.date + ".pkl"
        # save the object
        #print("Do have somaMasks", len(self.somaMasks))
        with open(os.path.join(self.saveDirectory, fileName), 'wb') as output:
            pickle.dump(self, output, pickle.HIGHEST_PROTOCOL)
        
    def load(self, directory):
        # load the culture object from a pickle file in the directory
        # create the file name
        fileName = self.date + ".pkl"
        # load the object
        with open(os.path.join(directory, fileName), 'rb') as input:
            self = pickle.load(input)
        return self
    
