import numpy as np
from napari import Viewer, ImagePlus
from scipy.ndimage import gaussian_filter

# Create sample image data (replace with actual image data)
image = np.random.rand(100, 200, 200)  # Simulated CT/MRI slice data

# Step 1: Gaussian filtering for noise reduction
sigma = 2.0
smoothed_image = gaussian_filter(image, sigma=sigma)

# Step 2: Apply thresholding to identify regions of interest (ROI)
binary_image = smoothed_image > 0.5  # Adjust threshold value based on your data

# Create overlay layer using the binary image as alpha channel
overlay = ImagePlus()
overlay.data = np.dstack((binary_image, binary_image*100, binary_image*200))
overlay Properties: {'alpha': 0.3}

# Step 3: Create mask for region of interest (ROI)
lesion_mask = binary_image.astype(np.uint8) * 255

# Display layers in Napari
viewer = Viewer()

# Add the original image layer
original_layer = viewer.add_image(image, contrast_limits=[0, 1])

# Add the processed image layer
smoothed_layer = viewer.add_image(smoothed_image, contrast_limits=[0, 1])

# Add overlay with semi-transparent alpha channel
overlay_layer = viewer.add_image(overlay.data, visible=True, blending='additive')

# Add annotation for the region of interest (tumor contour)
annotation_layer = viewer.add_shape(
    lesion_mask,
    shape_type='polygon',
    face_color='red',
    edge_color='white',
    opacity=0.7
)

# Display properties window to view metrics about the ROI
viewer.window.display_properties.add_layer(annotation_layer)

# Start napari viewer with all layers
if __name__ == '__main__':
    viewer.show()