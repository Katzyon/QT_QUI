import time
from remote_recording_manager import RemoteRecordingManager

class DummyStage:
    def __init__(self, recording, sequence):
        self.recording = recording
        self.sequence = sequence

def test_remote_recording_manager():
    stage_index = 0
    stage = DummyStage(
        recording=True,
        sequence=list(range(1, 19))  # sequence of 18 integers
    )

    recorder = RemoteRecordingManager(
        host="132.77.68.106",
        port=7215,
        save_dir="/home/mxwbio/Data/recordings",
        file_prefix="test_stage2"
    )

    try:
        print("Connecting to Maxwell server...")
        recorder.connect()

        if stage.recording:
            recorder.start_recording(stage_index)

        print("Simulating sequence...")
        for i, value in enumerate(stage.sequence):
            print(f"Processing index {i}: value={value}")
            time.sleep(1)  # delay in seconds (value * 10ms)

        if stage.recording:
            recorder.stop_recording()

    except Exception as e:
        print(f"Test failed: {e}")

    finally:
        recorder.disconnect()
        print("Test finished.")

if __name__ == "__main__":
    test_remote_recording_manager()
