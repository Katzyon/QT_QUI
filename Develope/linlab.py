from pycromanager import Core

core = Core()
x = core.get_x_position()
y = core.get_y_position()
z = core.get_z_position()
print(f"Stage position: X={x}, Y={y}, Z={z}")


# set stage position to (0, 0, 0)
core.set_xy_position(0, 0)
core.set_z_position(0)


# List all devices
#print(core.get_loaded_devices())



