import matplotlib.pyplot as plt

figure_references = {}

def display_image(img_data, caller_id=None):
    if caller_id is None:
        # Generate a default unique ID
        caller_id = id(img_data)
    
    if caller_id not in figure_references:
        figure_references[caller_id] = plt.figure()  # Create a new figure
        # set the position of the figure to top right corner
        figure_references[caller_id].canvas.manager.window.move(800, 50)


    else:
        plt.figure(figure_references[caller_id].number)  # Switch to the existing figure
        
    plt.clf()  # Clear the figure content
    plt.imshow(img_data)
    plt.axis('off')  # Turn off axis numbers and ticks
    plt.show()

# test the function
if __name__ == "__main__":
    import numpy as np
    img_data = np.random.random((600, 600))
    display_image(img_data, "hi")
