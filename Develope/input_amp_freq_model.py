import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from mpl_toolkits.mplot3d import Axes3D

# Initialize the figure and axis
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Define the grid for the two-dimensional space
x = np.linspace(-5, 5, 100)
y = np.linspace(-5, 5, 100)
X, Y = np.meshgrid(x, y)

# Initial parameters for the distributions
mean1 = [0, 0]
cov1 = [1, 1]

mean2 = [2, 2]
cov2 = [1.5, 1.5]

# Function to calculate 2D Gaussian
def gaussian_2d(x, y, mean, cov):
    X = np.stack([x, y], axis=-1)
    cov_matrix = np.array([[cov[0], 0], [0, cov[1]]])
    inv_cov = np.linalg.inv(cov_matrix)
    det_cov = np.linalg.det(cov_matrix)
    norm_const = 1 / (2 * np.pi * np.sqrt(det_cov))
    diff = X - mean
    exponent = -0.5 * np.einsum('...k,kl,...l->...', diff, inv_cov, diff)
    return norm_const * np.exp(exponent)

# Initial plot of the multiplied Gaussians
Z1 = gaussian_2d(X, Y, mean1, cov1)
Z2 = gaussian_2d(X, Y, mean2, cov2)
Z = Z1 * Z2
surf = ax.plot_surface(X, Y, Z, cmap='viridis', edgecolor='none')
ax.set_title('Multiplication of Two 2D Gaussian Distributions')
ax.set_xlabel('X-axis')
ax.set_ylabel('Y-axis')
ax.set_zlabel('Probability Density')


# Create sliders
axcolor = 'lightgoldenrodyellow'
ax_mean1_x = plt.axes([0.1, 0.02, 0.3, 0.02], facecolor=axcolor)
ax_mean1_y = plt.axes([0.1, 0.06, 0.3, 0.02], facecolor=axcolor)
ax_cov1_x = plt.axes([0.5, 0.02, 0.3, 0.02], facecolor=axcolor)
ax_cov1_y = plt.axes([0.5, 0.06, 0.3, 0.02], facecolor=axcolor)
# Add an additional slider for Z-axis range
ax_zlim = plt.axes([0.1, 0.1, 0.3, 0.02], facecolor=axcolor)
zlim_slider = Slider(ax_zlim, 'Z Max', 0.001, 0.05, valinit=0.005)

mean1_x_slider = Slider(ax_mean1_x, 'Mean1 X', -5, 5, valinit=mean1[0])
mean1_y_slider = Slider(ax_mean1_y, 'Mean1 Y', -5, 5, valinit=mean1[1])
cov1_x_slider = Slider(ax_cov1_x, 'Cov1 X', 0.1, 3, valinit=cov1[0])
cov1_y_slider = Slider(ax_cov1_y, 'Cov1 Y', 0.1, 3, valinit=cov1[1])

# Update function for sliders
def update(val):
    global surf
    ax.clear()
    mean1_updated = [mean1_x_slider.val, mean1_y_slider.val]
    cov1_updated = [cov1_x_slider.val, cov1_y_slider.val]
    Z1 = gaussian_2d(X, Y, mean1_updated, cov1_updated)
    Z2 = gaussian_2d(X, Y, mean2, cov2)  # mean2 and cov2 remain constant
    Z = Z1 * Z2
    surf = ax.plot_surface(X, Y, Z, cmap='viridis', edgecolor='none')
    ax.set_zlim(0, zlim_slider.val)  # Set Z-axis height based on slider
    ax.set_title('Multiplication of Two 2D Gaussian Distributions')
    ax.set_xlabel('X-axis')
    ax.set_ylabel('Y-axis')
    ax.set_zlabel('Probability Density')
    fig.canvas.draw_idle()

# Connect sliders to the update function
mean1_x_slider.on_changed(update)
mean1_y_slider.on_changed(update)
cov1_x_slider.on_changed(update)
cov1_y_slider.on_changed(update)
zlim_slider.on_changed(update)

# Show the plot with interactive sliders
plt.show()
