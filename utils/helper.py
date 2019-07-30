import numpy as np
import nibabel as nb
import matplotlib.pyplot as plt


# helper function to plot 3D NIfTI images
def plot_slice(fname):
    # Load the image
    img = nb.load(fname)
    data = img.get_data()

    # Cut in the middle of the brain
    cut = int(data.shape[-1] / 2) + 10

    # Plot the data
    plt.imshow(np.rot90(data[..., cut]), cmap="gray")
    plt.gca().set_axis_off()
