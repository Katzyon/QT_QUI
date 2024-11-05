
import json
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt

def load_metadata():
    # Set up the root Tkinter window
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Open a file dialog to select the metadata file
    file_path = filedialog.askopenfilename(initialdir="D:/DATA/Tests", title="Select a file",
                                           filetypes=(("Text files", "*.txt"), ("all files", "*.*")))

    # Check if a file was selected
    if file_path:
        try:
            # Open and read the JSON data from the file
            with open(file_path, 'r') as file:
                metadata = json.load(file)

            # Process each FrameKey to extract ElapsedTime-ms
            elapsed_times = []
            frame_keys = [key for key in metadata.keys() if key.startswith('FrameKey')]
            frame_keys.sort()  # Ensure the keys are sorted in order
            
            for key in frame_keys:
                if "ElapsedTime-ms" in metadata[key]:
                    elapsed_times.append(metadata[key]["ElapsedTime-ms"])
            
            # Calculate time differences between consecutive images
            time_differences = [elapsed_times[i] - elapsed_times[i - 1] for i in range(1, len(elapsed_times))]

            # Plot the time differences
            plt.figure(figsize=(10, 5))
            plt.plot(range(1, len(time_differences) + 1), time_differences, marker='o', linestyle='-')
            plt.title('Time Difference Between Consecutive Images')
            plt.xlabel('Image Number')
            plt.ylabel('Time Difference (ms)')
            plt.grid(True)
            plt.show()

        except Exception as e:
            print("Failed to read or process the file:", e)
    else:
        print("No file selected")

# Run the function to load metadata and plot time differences
load_metadata()
