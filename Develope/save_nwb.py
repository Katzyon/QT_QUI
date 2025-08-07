import os
import numpy as np
from datetime import datetime
from pynwb import NWBFile, NWBHDF5IO
from pynwb.base import TimeSeries
from datetime import timezone, datetime

def save_object_to_nwb(obj, file_name):
    """
    Saves a Python object to an NWB file inside the "Test" folder.

    Args:
        obj: Python object with attributes to save.
        file_name: The name of the NWB file to save (without path).
    """

    # Define the folder path
    folder_path = "Test"

    # Ensure the "Test" folder exists
    os.makedirs(folder_path, exist_ok=True)

    # Create full file path
    full_file_path = os.path.join(folder_path, file_name)
    session_start_time = datetime.now(timezone.utc)  # Use timezone-aware datetime

    nwbfile = NWBFile(
        session_description="Python object storage",
        identifier="example-id",
        session_start_time=session_start_time  # Use the defined variable
    )


    # Add object attributes to NWB file
    for attr_name in dir(obj):
        if attr_name.startswith("__") or callable(getattr(obj, attr_name)):
            continue

        attr_value = getattr(obj, attr_name)

        if isinstance(attr_value, list):  # Handle lists
            ts = TimeSeries(
                name=attr_name,
                data=np.array(attr_value),
                unit="",
                rate=1.0
            )
            nwbfile.add_acquisition(ts)

        elif isinstance(attr_value, np.ndarray):  # Handle NumPy arrays
            ts = TimeSeries(
                name=attr_name,
                data=attr_value,
                unit="",
                rate=1.0
            )
            nwbfile.add_acquisition(ts)

        elif isinstance(attr_value, str):  # Handle strings
            ts = TimeSeries(
                name=attr_name,
                data=np.array([attr_value]),
                unit="",
                rate=1.0
            )
            nwbfile.add_acquisition(ts)

        elif isinstance(attr_value, (int, float)):  # Handle numbers
            ts = TimeSeries(
                name=attr_name,
                data=np.array([attr_value]),
                unit="",
                rate=1.0
            )
            nwbfile.add_acquisition(ts)

        else:
            print(f"Skipping attribute {attr_name} of type {type(attr_value)}")
    
    absolute_path = os.path.abspath(full_file_path)
    print(f"Saving NWB file to: {absolute_path}")

    # Write NWB file to disk inside the "Test" folder
    with NWBHDF5IO(full_file_path, mode='w') as io:
        io.write(nwbfile)

    print(f"Object saved to {full_file_path}.")

# Example Usage
class MyObject:
    def __init__(self):
        self.list_data = [1, 2, 3, 4]
        self.array_data = np.random.rand(10)
        self.string_data = "Example String"
        self.int_data = 42
        self.image_data = np.random.rand(100, 100)  # Could save as a dataset
        
obj = MyObject()
save_object_to_nwb(obj, "example_file.nwb")
