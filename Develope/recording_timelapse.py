import time
import datetime as dt
import sys
import os

# Add parent directory (QT_GUI) to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from MainGUI.remote_recording_manager import RemoteRecordingManager

# Time configuration (in seconds)
TOTAL_DURATION = 60*60*12     #  seconds total duration
RECORDING_TIME = 20            # Record for  seconds
RECORD_CYCLE = 60*30          # Every  seconds

def record_seconds_every_minutes_for_time():
    manager = RemoteRecordingManager()
    manager.connect()

    try:
        total_cycles = TOTAL_DURATION // RECORD_CYCLE  # 6 cycles for 1 hour

        for stage_index in range(total_cycles):


            file_name = f"{manager.file_prefix}_{stage_index}"
            print(f"\n[{dt.datetime.now()}] Starting recording cycle {stage_index}")
            print(f"Recording will be saved as: {file_name}")

            manager.start_recording(stage_index)

            time.sleep(RECORDING_TIME)

            manager.stop_recording()
            print(f"[{dt.datetime.now()}] Finished recording cycle {stage_index}")

            if stage_index < total_cycles - 1:
                sleep_time = RECORD_CYCLE - RECORDING_TIME
                print(f"Waiting {sleep_time} seconds for next cycle...")
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nRecording loop interrupted by user.")
    finally:
        manager.disconnect()

if __name__ == "__main__":
    record_seconds_every_minutes_for_time()
