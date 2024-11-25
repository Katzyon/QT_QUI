# get core from self.core and set initial polygon parameters

class Polygon:
    def __init__(self, core):
        self.core = core
        self.initialize()
        

        
    def initialize(self):
        # get the SLM device
        self.dmd_name = self.core.getSLMDevice()

        # set the Polygon properties - TriggerType
        try:
            self.core.setProperty(self.dmd_name, "TriggerType", "2")
            print("Polygon TriggerType set to External.")
        except Exception as e:
            print(f"Error setting TriggerType: {e}")
        
