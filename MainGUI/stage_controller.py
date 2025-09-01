class StageController:
    def __init__(self, core, xy_stage, stage_position_label=None):
        """
        A wrapper for handling XY stage operations.

        Parameters:
        - core: PycroManager core object
        - xy_stage: device name of the XY stage (string)
        - stage_position_label: optional QLabel to display coordinates
        """
        self.core = core
        self.xy_stage = xy_stage
        self.stage_position_label = stage_position_label

    def get_position(self):
        try:
            x = self.core.get_x_position(self.xy_stage)
            y = self.core.get_y_position(self.xy_stage)
            return x, y
        except Exception as e:
            print(f"[StageController] Error reading position: {e}")
            return 0.0, 0.0

    def move_to(self, user_y, user_x):

        
        print(f"[StageController] Requested move to: X={user_y}, Y={user_x}")
        # print the type of user_x and user_y
        #print(f"[StageController] Types: user_y={type(user_y)}, user_x={type(user_x)}")

                # send notification to user that x or y is out of bounds if it was adjusted
        if user_y < -200 or user_y > 2500 or user_x < -200 or user_x > 4400:
            print(f"[StageController] Warning: Adjusted position to within bounds: X={user_x}, Y={user_y}")

        # bound the values of x,y 
        user_y = max(min(user_y, 2500), -200)
        user_x = max(min(user_x, 4400), -200)
        user_y = -user_y # Invert x for correct stage movement


        try:
            self.core.set_xy_position(float(user_y), float(user_x))
            self.core.wait_for_device(self.xy_stage)
            print(f"[StageController] Moved to: Y={user_y}, X={user_x} ")
            self.update_gui()
        except Exception as e:
            print(f"[StageController] Error moving stage: {e}")
            raise

    def zero(self):
        try:
            self.core.set_adapter_origin_xy(self.xy_stage, 0.0, 0.0)
            print("[StageController] Origin set to (0, 0).")
            self.update_gui()
        except Exception as e:
            print(f"[StageController] Error zeroing stage: {e}")
            raise

    def update_gui(self):
        if self.stage_position_label:
            try:
                x, y = self.get_position()
                self.stage_position_label.setText(f"{y:.2f},{-x:.2f}") # Invert x for display
                print(f"[StageController] GUI updated: X={y:.2f}, Y={-x:.2f}")
            except Exception as e:
                print(f"[StageController] GUI update failed: {e}")
