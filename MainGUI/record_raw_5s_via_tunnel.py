import datetime as dt
import time
import maxlab as mx

# Server-side save path (this path is on the MaxLab Linux machine)
SAVE_DIR = "/home/mxwbio/Data/recordings/Test"

DURATION_S = 5.0
WELL = 0
GROUP_NAME = "all_channels"
CHANNELS = list(range(1024))  # 0..1023

def main():
    # This MUST succeed through the SSH tunnel (localhost:7215 forwarded)
    mx.initialize()

    # offset the chip
    

    s = mx.Saving()
    s.open_directory(SAVE_DIR)

    file_name = "raw_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    s.start_file(file_name)

    # Raw traces require defining a group before start_recording
    # (exactly as in the official saving example)
    s.group_delete_all()
    s.group_define(WELL, GROUP_NAME, CHANNELS)

    s.start_recording([0])  # MaxOne: [0] is safe; some setups also accept no args
    time.sleep(DURATION_S)
    s.stop_recording()
    s.stop_file()

if __name__ == "__main__":
    main()
