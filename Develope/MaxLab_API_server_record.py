from maxlab.comm import api_context
import maxlab as mx
import time

HOST = "132.77.68.106"
PORT = 7215

save_dir = "/home/mxwbio/Data/recordings"
file_name = "26995_13DIV"

with api_context(host=HOST, port=PORT) as api:
    # Redefine methods to use the same persistent connection
    def send(command):
        return api.send(command)

    print("Sending offset command...")
    api.send("system_offset")  # Perform offset compensation on all activated wells

    print("Waiting 11 seconds for offset to complete...")
    time.sleep(11)
    
    
    print("Opening directory...")
    send(f"saving_open_dir {save_dir}")

    print("Starting file...")
    send(f"saving_start_file {file_name}")

    print("Starting recording...")
    send("saving_start_recording")

    time.sleep(5)

    print("Stopping recording...")
    send("saving_stop_recording")

    print("Closing file...")
    send("saving_stop_file")
