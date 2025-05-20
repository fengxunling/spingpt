import os
import sys
sys.path.append(os.path.dirname(__file__)+'/napari-nifti-main/src/')
import numpy as np
from napari_nifti._reader import napari_get_reader
import napari
from napari import Viewer
import nibabel as nib
from qtpy.QtWidgets import QApplication

def show_3d_view(filepath):
    """Display 3D view of NIFTI file"""
    # Read image data
    reader = napari_get_reader(filepath)
    if not reader:
        print("Cannot find file reader")
        sys.exit(1)
        
    layer_data = reader(filepath)
    if not layer_data:
        print("Cannot read layer data")
        sys.exit(1)
        
    # Extract image data
    image_array = layer_data[0][0]
    metadata = layer_data[0][1]
    
    # Create viewer
    viewer = Viewer(title="3D file")
    viewer.window._qt_window.resize(800, 600)
    
    # Add volume rendering
    volume_layer = viewer.add_image(
        image_array,
        rendering='mip',  # Maximum intensity projection
        name='3D render image',
        blending='additive',
        opacity=0.7
    )
    
    # Set camera to 3D mode
    viewer.dims.ndisplay = 3
    
    # Display file information
    print(f"File: {os.path.basename(filepath)}")
    print(f"Data shape: {image_array.shape}")
    
    # Run napari
    napari.run()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Use default file
        default_file = "T2G002_MRI_Spine_t2_space_sag_p2_iso_20240820161941_19001.nii.gz"
        print(f"No file specified, using default file: {default_file}")
        file_name = default_file
    else:
        file_name = sys.argv[1].strip('"')  # Remove potential quotes
        
    # Build file path
    IMAGE_PATH = os.path.join(os.path.dirname(__file__), 'data')
    filepath = os.path.join(IMAGE_PATH, file_name)
    
    # Validate path
    if not os.path.exists(filepath):
        print(f"File path does not exist: {filepath}")
        sys.exit(1)
        
    # Show 3D view
    show_3d_view(filepath)