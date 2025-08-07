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

    def move_to(self, x, y):
        try:
            self.core.set_xy_position(x, y)
            self.core.wait_for_device(self.xy_stage)
            print(f"[StageController] Moved to: X={x}, Y={y}")
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
                self.stage_position_label.setText(f"{x:.2f},{y:.2f}")
                print(f"[StageController] GUI updated: X={x}, Y={y}")
            except Exception as e:
                print(f"[StageController] GUI update failed: {e}")
