# Must be callable exactly like:
# self.xy_stage = StageController(self.core, self.xy_stage_device, self.stage_position)

import time

class StageController:
    """
    Absolute stage control (µm), zero cross-coupling, correct inversion semantics.

    PUBLIC METHODS
    --------------
    get_position() -> (x, y)
    move_to(x_target: float, y_target: float)    # set both axes (absolute)
    move_x(x_target: float)                      # set X only (absolute)
    move_y(y_target: float)                      # set Y only (absolute)
    zero()                                       # adapter origin = current point
    update_gui()                                 # label: "X,Y" (two decimals)

    INVERSION (manual, per-axis)
    ----------------------------
    self.invert_x = False  # True: GUI +X corresponds to physical −X
    self.invert_y = False  # True: GUI +Y corresponds to physical −Y
    """

    def __init__(self, core, xy_stage_device, stage_position_label=None):
        self.core = core
        self.xy_stage = xy_stage_device          # do not change external usage
        self.stage_position_label = stage_position_label

        # Manual direction toggles (can be changed at runtime)
        self.invert_x = True
        self.invert_y = False

        self._timeout_s = 10.0
        self._eps = 1e-9

    # ---------- internals ----------
    def _wait_ready(self):
        t0 = time.time()
        while self.core.device_busy(self.xy_stage):
            if time.time() - t0 > self._timeout_s:
                raise TimeoutError("[StageController] Stage did not become ready in time")
            time.sleep(0.05)

    def _rel_x_only(self, dx_um: float):
        """Move physical X only. Sends (dx, 0.0) to the driver."""
        if abs(dx_um) <= self._eps:
            return
        self.core.set_relative_xy_position(self.xy_stage, float(dx_um), 0.0)
        self._wait_ready()

    def _rel_y_only(self, dy_um: float):
        """Move physical Y only. Sends (0.0, dy) to the driver."""
        if abs(dy_um) <= self._eps:
            return
        self.core.set_relative_xy_position(self.xy_stage, 0.0, float(dy_um))
        self._wait_ready()

    def _mx(self):
        return -1.0 if self.invert_x else +1.0

    def _my(self):
        return -1.0 if self.invert_y else +1.0

    # ---------- public API ----------
    def get_position(self):
        try:
            x = float(self.core.get_x_position(self.xy_stage))
            y = float(self.core.get_y_position(self.xy_stage))
            return x, y
        except Exception as e:
            raise RuntimeError(f"[StageController] Error reading position: {e}")

    def move_to(self, x_target: float, y_target: float):
        """
        Absolute move: set X and Y to the requested stage coordinates (µm).

        Inversion semantics (correct, convergent):
          sx = Mx * x_physical;  sy = My * y_physical
          dx_cmd = (Mx * x_target) - x_now
          dy_cmd = (My * y_target) - y_now
        """
        x_now, y_now = self.get_position()
        Mx, My = self._mx(), self._my()

        dx_cmd = (Mx * float(x_target)) - x_now
        dy_cmd = (My * float(y_target)) - y_now

        # Execute as two independent one-axis moves; do NOT recompute between axes
        self._rel_y_only(dy_cmd)
        self._rel_x_only(dx_cmd)

        self.update_gui()

    def move_x(self, x_target: float):
        """Move X only (absolute). Y is untouched."""
        x_now, _ = self.get_position()
        Mx = self._mx()
        dx_cmd = (Mx * float(x_target)) - x_now
        self._rel_x_only(dx_cmd)
        self.update_gui()

    def move_y(self, y_target: float):
        """Move Y only (absolute). X is untouched."""
        _, y_now = self.get_position()
        My = self._my()
        dy_cmd = (My * float(y_target)) - y_now
        self._rel_y_only(dy_cmd)
        self.update_gui()

    def zero(self):
        """Set adapter origin to the current point (does not change inversion flags)."""
        try:
            self.core.set_adapter_origin_xy(self.xy_stage, 0.0, 0.0)
            self.update_gui()
        except Exception as e:
            raise RuntimeError(f"[StageController] Error zeroing stage: {e}")

    def update_gui(self):
        if not self.stage_position_label:
            return
        try:
            x, y = self.get_position()
            self.stage_position_label.setText(f"{y:.2f},{-x:.2f}")
        except Exception as e:
            print(f"[StageController] GUI update failed: {e}")
