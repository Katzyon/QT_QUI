
# gets masks image and make a single mask image for each cell
# create random ansembles of grouped masks and save them as a movie
import numpy as np
import cv2
import matplotlib.pyplot as plt
#import tifffile

# self is the instance of maingui and carry all the data from maingui
def make_masks(self):
            
    # load the image mask_output.tif from D:\DATA\Patterns\Patt_2023-10-31\Images
    #self.masks = cv2.imread(self.Images + "\mask_output.tif", cv2.IMREAD_GRAYSCALE)
    
    print("shape of masks:", self.masks.shape)

    self.unique_cells = np.unique(self.masks) # number of somas in the image
    self.unique_cells = self.unique_cells[self.unique_cells != 0]  # Exclude background (0 value)
    print("unique_cells:", self.unique_cells)

    self.binary_images = []
    # Create a binary image for each cell
    for cell_id in self.unique_cells:
        #print("cell_id:", cell_id)
        # print("type of cell_id:", type(cell_id))    

        binary_cell_image = (self.masks == cell_id).astype(np.uint8)
        
        # turn non-zero values to 255
        binary_cell_image = binary_cell_image * 255

        self.binary_images.append(binary_cell_image) # list of binary images of each soma/cell - black background and white soma/cell
        # print min max values
        #print("gcm GUI_createMasks image min:", self.binary_images[cell_id-1].min(), "image max:", self.binary_images[cell_id-1].max())


    # plot the image using matplotlib
    plt.figure(figsize=(12, 4))
    plt.get_current_fig_manager().set_window_title("GUI_createMasks_make_masks")
    plt.imshow(self.masks, cmap='gray')
    plt.title("Masks Images Gray scaled somas index")
    plt.show()
    # sleep

# summing together the binary images of the cells in each group to create a group mask
def make_group_masks(self):
    # create masks for each group from the dictionary self.rand_groups
    # number of groups in the dictionary
    group_sums = {}
    
    
    for cell_id, group_ids in self.rand_groups.items():
        
        cell_image = self.binary_images[cell_id - 1] # cell_id starts from 1 and not from 0

        for group_id in group_ids:
            if group_id in group_sums:
                group_sums[group_id] += cell_image
            else:
                group_sums[group_id] = cell_image.copy()

    return group_sums


def affine_transform(self, images, save_dir):
    # apply affine transformation to the binary images and save them to DMD folder
       
    
    #print("affine_tranform:", self.affine_transform)

    # Apply affine transformation to the self.binary_images array
    self.transformed_images = []
    for image_number, image in enumerate(images, start=1):
        
        transformed_image = cv2.warpAffine(image, self.affine_transform, (912, 1140))
        #print("transformed image min:", transformed_image.min(), "transformed image max:", transformed_image.max())

        self.transformed_images.append(transformed_image)
        # saving images to DMD folder
        #print(self.DMD_dir + "\\" + str(cell_id) + ".bmp")
        #cv2.imwrite(self.DMD_dir + "\\" + str(image_number) + ".bmp", transformed_image * 255)
        cv2.imwrite(save_dir + "\\" + str(image_number) + ".bmp", transformed_image)
        #check the image min max values - the binary images are 0 and 255 so why multiply by 255?

    
    return self.transformed_images # the DMD images of each cell


# mask_creator.make_masks()
# mask_creator.affine_transform()

