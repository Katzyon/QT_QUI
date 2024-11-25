# gets masks image and make a single mask image for each cell
# create random ansembles of grouped masks and save them as a movie
import numpy as np
import cv2
import matplotlib.pyplot as plt
import tifffile
import time
import socket
 # cd("D:\DATA\Patterns\Patt_2023-10-31")

class MaskCreator:
    def create_masks(self):
        self.local_ip = socket.gethostbyname(socket.gethostname())
        if self.local_ip == "132.77.68.241":
            print("Local IP is 132.77.68.241. Running the script...")
            self.DMD_dir = r"C:\Users\yon.WISMAIN\Google Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Patt_2023-10-31\DMD\Masks"
            self.Images = r"C:\Users\yon.WISMAIN\Google Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Patt_2023-10-31\Images"
        # Add your main code here.
        else:
            self.DMD_dir = r"D:\DATA\Patterns\Patt_2023-10-31\DMD"
            self.Images = r"D:\DATA\Patterns\Patt_2023-10-31\Images"
        #self.save_mask()


    def make_masks(self): # called by CreateMasks.py
             
        # load the image mask_output.tif from D:\DATA\Patterns\Patt_2023-10-31\Images
        #self.masks = cv2.imread(self.Images + "\mask_output.tif", cv2.IMREAD_GRAYSCALE)
        self.masks = tifffile.imread(self.Images + "/mask_output.tif")
        print("shape of masks:", self.masks.shape)

        self.unique_cells = np.unique(self.masks)
        print(type(self.unique_cells))
        self.unique_cells = self.unique_cells[self.unique_cells != 0]  # Exclude background (0 value)

        self.binary_images = []
        # Create a binary image for each cell
        for cell_id in self.unique_cells:
            # print("cell_id:", cell_id)
            # print("type of cell_id:", type(cell_id))    

            binary_cell_image = (self.masks == cell_id).astype(np.uint8)
            self.binary_images.append(binary_cell_image)


            # saving images to DMD folder
            #print(self.DMD_dir + "\\" + str(cell_id) + ".bmp")
            #cv2.imwrite(self.DMD_dir + "\\" + str(cell_id) + ".bmp", binary_cell_image * 255)

        # plot the image using matplotlib
        plt.figure(figsize=(12, 4))
        plt.imshow(self.masks, cmap='gray')
        plt.title("Original Image")
        plt.show()
        # sleep
        

    
    def affine_transform(self):

        if self.local_ip == "132.77.68.241":
            file_path = r"C:\Users\yon.WISMAIN\Google Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Images\affine_transform.npy"
        else:
        # Load the affine transformation matrix
            file_path = r"G:\My Drive\Research\Projects\Theory of cortical mind\Object representation\Software\Python\QT_GUI\MainGUI\Images\affine_transform.npy"
        
        
        self.affine_tranform = np.load(file_path)
        print("affine_tranform:", self.affine_tranform)

        # Apply affine transformation to the self.binary_images array
        transformed_images = []
        for image_number, image in enumerate(self.binary_images, start=1):
            
            transformed_image = cv2.warpAffine(image, self.affine_tranform, (912, 1140))
            transformed_images.append(transformed_image)
            # saving images to DMD folder
            #print(self.DMD_dir + "\\" + str(cell_id) + ".bmp")
            cv2.imwrite(self.DMD_dir + "\\" + str(image_number) + ".bmp", transformed_image * 255)

      
        # return transformed_image

mask_creator = MaskCreator()
mask_creator.create_masks()
mask_creator.make_masks()
mask_creator.affine_transform()



# call the function


   
