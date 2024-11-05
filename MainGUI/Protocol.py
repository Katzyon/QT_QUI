


class Protocol:
    """This class represents a protocol stage. Each stage have many attributes, which determine the stimulation parameters and cellular groups to be stimulated.
    It is referred as self.stages[], in the maingui. Called by the protocolSet class"""


    def __init__(self):
        # define Culture as parent class
        

        self.number = int() # number of the stage in the protocol sequnce
        self.numberCells = int() # number of detected cells in the culture
        self.groupSize = int() # number of cells in each group
        self.groupsNumber = int() # number of groups
        self.groupFreq = float() # stimulation frequency in Hz for each group (whole sequence cycle)
        self.onTime = int() # DMD on time in ms for each stimulation
        self.backgroundFreq = float() # DMD background frequency in Hz
        self.backgroundOnTime = int() # DMD on time in ms - not in use (?)
        self.sequence = [] # list of each group indices of the cells to be stimulated in a sequence
        self.sequences_images = [] # list of images to be displayed in each sequence
        self.interMaskInterval = float() # ms time between each mask in a sequence
        self.sequenceRepeats = int()
        self.stimTime = int() # stimulation time for running the protocol in minutes
        self.cycleTime = float()
        self.imageRepeats = int()
        self.manualGroups = [] # list of manually selected groups
        self.isManual = False # get checkbox selection of isManualSequence
        self.isProbabilityStim = False # get checkbox selection of prob_stim

        
        

    def calc_interMaskInterval(self):
        
        self.interMaskInterval = (1000/self.groupFreq) / self.groupsNumber - self.onTime # ms
        print("groupFreq:", self.groupFreq, "groupsNumber:", self.groupsNumber)

        print("interMaskInterval:", self.interMaskInterval)
        # through a warning if interMaskInterval is shorter than 50 ms
        if self.interMaskInterval < 50:
            print("Warning: Protocol.py interMaskInterval is shorter than 50 ms")
            # it means that you should decrease the numbers of groups by increasing group size or group the remaining cells into larger groups (2 cells instead of 1) 

        self.cycleTime = 1/self.groupFreq # one cycle of a stage in seconds
        self.sequenceRepeats = round(self.stimTime*60 / self.cycleTime) # number of protocol repeats for running the protocol
        
        self.cycleTime = 1/self.groupFreq # one stage cycle time in seconds
       
        self.imageRepeats = self.sequenceRepeats * self.groupsNumber

        print("protocol time", self.stimTime*60, "sec", "calculated running time:", self.imageRepeats*self.interMaskInterval/1000, "sec")



