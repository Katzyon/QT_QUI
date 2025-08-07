# called by protocolSet.py via Protocol object to create the sequence of images to be displayed on the DMD
# create the sequence indices (stage.sequence) and the images (stage.groups_images) to be displayed on the DMD
import random
import numpy as np
import matplotlib.pyplot as plt
import cv2
import os


def create_random_sequence(stage): # called by protocolSet.py via Protocol object to create the sequence of images to be displayed on the DMD
    # get Protocol object and randomly group the indices according to its parameters:
    # create probability distribution for the groups 


    all_cells = stage.input_cells.copy() # copy the list of all cells

    # remove output group from all_cells - THEY DO NOT GET ANY STIMULATION!!! 
    for cell in stage.output_group:
        stage.input_cells.remove(cell) # leaving only the input cells (pattern stimulated cells)
    print("all stimulated cells", stage.input_cells, "number of groups", stage.groups_number, "group size", stage.group_size)

    # create groups without the output group cell picked by the user
    for _ in range(stage.groups_number): # creates the major groups
        group = random.sample(all_cells, stage.group_size) # randomly select cells from the list of all cells
        print("sequence group", group)
        stage.groups.append(group) # add the group to the stage groups list
        # Remove the selected cells to ensure no repeats
        for cell in group:
            all_cells.remove(cell)
    
    # create one list of the remaining cells
    print("created groups", stage.groups)
    stage.remaining_cells = [all_cells] # what happens with the remaining cells? - they are not stimulated?

    # create the main groups probabilities
    stage.group_probabilities = create_decay_probabilities(stage.groups_number, stage.group_probability_ratio) 

    smaller_groups = []
    smaller_group_probabilities = []

    highest_group_prob = stage.group_probabilities[0] # probability of the first group (highest)

    for i, group in enumerate(stage.groups):
        if i == 0:  # Skip creating smaller groups for the highest probability group (first group)
            continue
        # Divide the group into smaller groups of size group_size / group_divider
        smaller_group_size = stage.group_size // stage.group_divider
        for j in range(stage.group_divider):
            start_idx = j * smaller_group_size
            end_idx = start_idx + smaller_group_size
            smaller_group = group[start_idx:end_idx]
            smaller_groups.append(smaller_group)
            
            # Assign probability for each smaller group (SG) such that its probability + its major group (MG) P would be equal to the highest probability group (HG)
            # p(HG) = p(MG1) + p(SG1) = p(MG2) + p(SG2)
            # p(MG1) > p(MG2) and p(SG1) < p(SG2) since the p for the first group is the highest and decays by stage.group_probability_ratio for the others
            smaller_group_probability = (highest_group_prob - stage.group_probabilities[i]) # / stage.group_divider
            smaller_group_probabilities.append(smaller_group_probability)



    # Combine original group probabilities and smaller group probabilities
    all_groups_but_high = stage.groups[1:] + smaller_groups  # Exclude the highest probability group from being duplicated
    all_probabilities = stage.group_probabilities[1:] + smaller_group_probabilities

    # Add the highest probability group back to the combined list
    all_groups_but_high.insert(0, stage.groups[0])
    all_probabilities.insert(0, stage.group_probabilities[0]) # add the highest probability group back to the list

    # Normalize all probabilities to sum to 1
    total_prob_all = sum(all_probabilities)
    all_probabilities = [prob / total_prob_all for prob in all_probabilities] # normalize the probabilities

    n_presentations = len(all_groups_but_high) * stage.group_distribution_number
    stage.sequence = random.choices(range(len(all_groups_but_high)), weights=all_probabilities, k=n_presentations)


    # create masks for all the groups
    all_groups = stage.groups + smaller_groups

    for group in all_groups: # group is a list of cells either of size 1 or larger
        group_images = []
        for cell in group: # [1, 3, 11] - list of cells in the group
            group_images.append(stage.images[cell - 1])

        # sum the images in the group
        group_sum = sum(group_images) # sum the images in the group - is stimulation to a group of cells
        stage.groups_images.append(group_sum) # add one image to the sequence

    #present the distribution of the groups in the sequence !!!! check the output thouroughly

    # Calculate frequency counts for stacked bar chart
    if 1: 
        all_counts = np.bincount(stage.sequence, minlength=len(all_groups_but_high)) # counts the number of appearance for each group
        #print(all_counts)

        # Split counts into original and pooled smaller groups
        original_counts = all_counts[:stage.groups_number] # Original groups - from index 0 to ngroups

        # check the smaller groups indices slices
        for i in range(stage.groups_number - 1):
            start_idx = stage.groups_number + i * stage.group_divider
            end_idx = stage.groups_number + (i + 1) * stage.group_divider
            indices = list(range(start_idx, end_idx))
            group_sum = sum(all_counts[start_idx:end_idx])
            
            # Print the indices and the sum for each group
            print(f"Indices: {indices}, Sum: {group_sum}")

        pooled_counts = [sum(all_counts[stage.groups_number + i * stage.group_divider:stage.groups_number + (i + 1) * stage.group_divider]) for i in range(stage.groups_number - 1)]
        pooled_counts = [0] + pooled_counts  # Add 0 for the highest probability group

        # Plot stacked bar chart to show distribution
        x = np.arange(stage.groups_number)
        width = 0.5

        plt.figure(figsize=(12, 6))
        # figure title
        plt.suptitle('create_sequence create_random_sequence', fontsize=16)

        plt.bar(x, original_counts, width, label='Original Groups', color='skyblue')
        plt.bar(x, pooled_counts, width, bottom=original_counts, label='Pooled Smaller Groups', color='lightgreen')
        plt.xlabel('Group Index')
        plt.ylabel('Frequency')
        plt.title('Stacked Distribution of Group Selections')
        plt.xticks(x)
        plt.legend()
        plt.show()



def create_order_sequence(stage):
    # create a sequence of images according to the order of the groups (same probability for all groups)
    # repeat the basic sequence many times
   
    print("create_order_sequence called")   
    n = stage.group_distribution_number* stage.groups_number # number of repetitions of the sequence
    stage.sequence = np.tile(np.arange(stage.groups_number), n).tolist()
    
    print("manual groups:", stage.groups)
    for group in stage.groups: # group is a list of cells either of size 1 or larger
        print("group:", group)
        group_images = []
        for cell in group: # [1, 3, 11] - list of cells in the group
            group_images.append(stage.images[cell - 1])

        # sum the images in the group
        group_sum = sum(group_images) # sum the images in the group - is stimulation to a group of cells
        stage.groups_images.append(group_sum) # add one image to the sequence
        print("group image shape:", group_sum.shape)
        




def create_decay_probabilities(groupsNumber, group_probability_ratio):
    
    
    base_prob = 1.0   

    probabilities = []
    total_prob = 0.0
    for i in range(groupsNumber):
        prob = base_prob / (group_probability_ratio ** i)
        probabilities.append(prob)
        total_prob += prob

    # Normalize the probabilities to sum to 1
    group_probabilities = [prob / total_prob for prob in probabilities]
    return group_probabilities

def create_test_sequence(stage):
    # create a test sequence with 10 groups of 3 cells each
    all_cells = stage.input_cells.copy() # copy the list of all cells

    # remove output group from all_cells - THEY DO NOT GET ANY STIMULATION!!! 
    for cell in stage.output_group:
        stage.input_cells.remove(cell) # leaving only the input cells (pattern stimulated cells)
    print("all stimulated cells", stage.input_cells, "number of groups", stage.groups_number, "group size", stage.group_size)

    # create groups without the output group cell picked by the user
    for _ in range(stage.groups_number):
        group = random.sample(all_cells, stage.group_size)
        print("sequence group", group)
        stage.groups.append(group)
        # Remove the selected cells to ensure no repeats
        for cell in group:
            all_cells.remove(cell)

    # create one list of the remaining cells
    stage.remaining_cells = [all_cells] # what happens with the remaining cells? - they are not stimulated?

    # create the main groups probabilities
    group_probabilities = round(1 / stage.groups_number, 2)
    stage.group_probabilities = [group_probabilities] * stage.groups_number
    #group_distribution_number = 50 is the number of times each group is presented in the sequence

    #n_presentations = stage.groups_number * stage.group_distribution_number
    
    stage.sequence = np.repeat(stage.groups_number, stage.group_distribution_number).tolist() # create a sequence of the groups, each accoring its probabigroup_probabilities

    for group in stage.groups: # group is a list of cells either of size 1 or larger
        group_images = []
        for cell in group: # [1, 3, 11] - list of cells in the group
            group_images.append(stage.images[cell - 1])

        # sum the images in the group
        group_sum = sum(group_images) # sum the images in the group - is stimulation to a group of cells
        stage.groups_images.append(group_sum) # add one image to the sequence


def create_squares_sequence(stage):
    # Create a sequence of square presentations
    
    folder = r"D:\DATA\Patterns\Squares_114px"
    # count the number of images in the folder

    image_files = [f for f in os.listdir(folder) if f.endswith('.bmp')]
    #stage.groups_images = [cv2.imread(os.path.join(folder, f), cv2.IMREAD_GRAYSCALE) for f in image_files]
    stage.groups_images = [
        cv2.threshold(
            cv2.imread(os.path.join(folder, f), cv2.IMREAD_GRAYSCALE), 127, 255, cv2.THRESH_BINARY
        )[1] # Convert to binary image. The [1] extracts the binary image from the tuple returned by cv2.threshold
        for f in image_files
    ]

    # plot the size of the first image
    print("Size of first image:", stage.groups_images[0].shape)
    # create a sequence of indices for the images
    stage.sequence = list(range(len(stage.groups_images)))
