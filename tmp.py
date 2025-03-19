import os
import sys
sys.path.append(os.path.dirname(__file__)+'/napari-nifti/src/')
print(os.path.dirname(__file__)+'')

import threading
import time
from datetime import datetime
import numpy as np
from imageio import get_writer
from mss import mss  # cross-platform screen capture library
from napari_nifti._reader import napari_get_reader
import napari
from napari import Viewer

from PIL import Image, ImageDraw, ImageFont
import queue

import nibabel as nib
from qtpy.QtCore import QPoint, QTimer, Qt
from qtpy.QtWidgets import QLineEdit, QPushButton, QHBoxLayout, QToolBar, QSlider, QWidget, QLabel, QSizePolicy
from recorder import ScreenRecorder
from viewer_module import ViewerUI

import sounddevice as sd 
from scipy.io.wavfile import write as write_wav

import cv2

# set the parameters
RECORD_PATH = os.path.dirname(__file__)+'/recorded_materials/'  # recording file path
FPS = 15  # frames per second
RECORD_REGION = None  # set the recording region to default

FONT_PATH = "arial.ttf"  # font file path
FONT_SIZE = 30
TEXT_COLOR = 255  
TEXT_POSITION = (10, 10)  # text position
MAX_TEXT_DURATION = 5  # seconds of text duration

# 初始化录制器
recorder = ScreenRecorder(FONT_PATH=FONT_PATH, FONT_SIZE=FONT_SIZE, RECORD_PATH=RECORD_PATH, FPS=FPS)

# set the file path
IMAGE_LIST = [
    "D:/projects/spingpt/data/T2G003_Spine_NIFTI/Dicoms_Spine_MRI_t2_space_sag_p2_iso_2050122160508_5001.nii.gz",
    # "D:/projects/spingpt/data/T2G003_Spine_NIFTI/Dicoms_Spine_MRI_t2_spc_tra_iso_ZOOMit_05_TR2500_interpol_T11_L2_20250122160508_6001.nii.gz",
    # "D:/projects/spingpt/data/T2G003_Spine_NIFTI/Dicoms_Spine_MRI_t2_trufi3d_cor_06_2050122160508_4001.nii.gz",
    # "D:/projects/spingpt/data/T2G003_Spine_NIFTI/T2G003_Spine_MRI_t2_space_sag_p2_iso_20250122160508_5001.nii.gz",
]
current_image_idx = 0 


filepath = IMAGE_LIST[current_image_idx]
image_name = os.path.splitext(os.path.basename(filepath))[0]
recorder.image_name = image_name  # set the image name

img = nib.load(filepath)
header = img.header

# image dimensions
dimensions = header.get_data_shape()  
print(dimensions)
# voxel dimensions (in mm)
voxel_sizes = header.get_zooms()    
print(f'voxel_dimensions:{voxel_sizes}') 

# read the image data
reader = napari_get_reader(filepath)
if not reader:
    print("Can't find a reader for the file")
    sys.exit()

layer_data = reader(filepath)
if not layer_data:
    print("not layer data")
    sys.exit()

# extract the image data
image_array = layer_data[0][0]
metadata = layer_data[0][1]


# Create Viewer and add image layer (hidden)
viewer3d = ViewerUI(image_array, metadata, filepath)
viewer = viewer3d.get_viewer()
points_layer = viewer3d.get_points_layer()

viewer.window._qt_window.showFullScreen() # full screen
QTimer.singleShot(100, lambda: [
    [tb.setVisible(False) for tb in viewer.window._qt_window.findChildren(QToolBar)],
    viewer.window._qt_window.menuBar().setVisible(False),
    viewer.window._qt_window.statusBar().setVisible(False),
    [btn.setVisible(False) for btn in viewer.window._qt_window.findChildren(QPushButton) 
     if btn.objectName() not in ["nav_prev_btn", "nav_next_btn", "submit_btn"]],  # 过滤保留的按钮
])
# buttons = viewer.window._qt_window.findChildren(QPushButton)
# print("\n[Visible Buttons]")
# for btn in buttons:
#     if btn.isVisible():
#         print(f"{btn.objectName()} | {btn.text()} | {btn.toolTip()}")

image_layer = viewer.add_image(image_array, **metadata, visible=False)


# Get initial slice positions
initial_z, initial_y, initial_x = viewer.dims.current_step

# Add orthogonal 2D slice layers
axial_slice = np.fliplr(np.rot90(image_array[initial_z, :, :], k=2))
coronal_slice = np.fliplr(np.rot90(image_array[:, initial_y, :], k=2))
sagittal_slice = np.fliplr(np.rot90(image_array[:, :, initial_x], k=2))
print('axial_slice:', axial_slice.shape)
print('coronal_slice:', coronal_slice.shape)
print('sagittal_slice:', sagittal_slice.shape)
axial_layer = viewer.add_image(axial_slice, name='Axial')
coronal_layer = viewer.add_image(coronal_slice, name='Coronal', visible=False)
sagittal_layer = viewer.add_image(sagittal_slice, name='Sagittal')


# add text color definition at the beginning of the file
TEXT_COLOR_WHITE = 1000  # white text
VIEWER_TEXT_POSITION = (10, 10) # coordinates of the text

# add font initialization at the beginning of the file
viewer_font = ImageFont.truetype(FONT_PATH, 15) # font size

def add_text_to_slice(slice_data, text):
    """add text annotation to the slice"""
    pil_img = Image.fromarray(slice_data)
    draw = ImageDraw.Draw(pil_img)
    draw.text(VIEWER_TEXT_POSITION, 
             text,
             fill=TEXT_COLOR_WHITE, 
             font=viewer_font)
    return np.array(pil_img)

# Set grid layout
axial_layer = viewer.layers['Axial'] # get the target layer
axial_layer.translate = (-50, -100)  # move the layer to the specified position
axial_layer.scale = [0.4, 0.4] 
sagittal_layer = viewer.layers['Sagittal'] 
sagittal_layer.translate = (-20, -60)  
sagittal_layer.scale = [0.2, 0.2] 
coronal_layer = viewer.layers['Coronal'] 
coronal_layer.translate = (-110, 90) 
coronal_layer.scale = [0.4, 0.4] 

# Create line layer
def create_line_layer(color, line_data, layer, name, visible):
    return viewer.add_shapes(
        line_data,
        shape_type='line',
        edge_color=color,
        edge_width=1.5,
        scale=layer.scale,  # maintain the same scale as the corresponding view
        translate=layer.translate,  # align with the axial view
        name=name,
        visible=visible
    )


def update_slices(event):
    """Update the slices with rotation and text annotation"""
    # z, y, x = viewer.dims.current_step
    z = np.clip(viewer.dims.current_step[0], 0, image_array.shape[0]-1) # add bounder check
    y = np.clip(viewer.dims.current_step[1], 0, image_array.shape[1]-1)
    x = np.clip(viewer.dims.current_step[2], 0, image_array.shape[2]-1)
    
    # axial view (rotate 90 degrees counterclockwise)
    axial_slice = np.fliplr(np.rot90(image_array[z, :, :], k=2))
    
    # coronal view (rotate 180 degrees counterclockwise)
    coronal_slice = np.fliplr(np.rot90(image_array[:, y, :], k=2))
    
    # sagittal view
    sagittal_slice = np.fliplr(np.rot90(image_array[:, :, x], k=2))
    
    # update the layer data
    axial_layer.data = axial_slice
    coronal_layer.data = coronal_slice
    sagittal_layer.data = sagittal_slice
    
    # refresh the display
    axial_layer.refresh()
    coronal_layer.refresh()
    sagittal_layer.refresh()

    # according to the current slice update the visibility of the points
    if len(points_layer.data) > 0:
        current_z, current_y, current_x = viewer.dims.current_step
        visible = []
        for point in points_layer.data:
            p_z = int(round(point[0]))
            p_y = int(round(point[1]))
            p_x = int(round(point[2]))
            # check if on any of the current slice planes
            if p_z == current_z or p_y == current_y or p_x == current_x:
                visible.append(True)
            else:
                visible.append(False)
        points_layer.visible = visible
        points_layer.refresh()  # refresh the point layer display


# Connect dimension updates
viewer.dims.events.current_step.connect(update_slices)

# Add points layer and other existing logic
points_layer = viewer.add_points(
    name='3d corresponding points',
    ndim=3,
    size=3,
    face_color='red'
)

# logics for recording the points
previous_length = 0

def on_points_changed(event):
    global previous_length
    current_data = points_layer.data
    current_length = len(current_data)
    
    if current_length > previous_length:
        new_points = current_data[previous_length:current_length]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        current_step = viewer.dims.current_step
        spacing = image_layer.scale
        translate = image_layer.translate
        
        log_info = []
        for pt in new_points:
            physical_coord = np.array(pt) * spacing + translate
            log_entry = (
                f"time: {timestamp}\n"
                f"spatial coordinates: {physical_coord}\n"
                # f"volumes coordinates: {pt}\n"
                f"current slice: [dim0:{current_step[0]}, dim1:{current_step[1]}, dim2:{current_step[2]}]\n"
                "------------------------\n"
            )
            log_info.append(log_entry)
            print(log_entry.strip())
        
        if recorder.is_recording:
            with open(recorder.log_path, "a") as f:
                f.writelines(log_info)
        
        previous_length = current_length

points_layer.events.data.connect(on_points_changed)

# set the recording callback
@viewer.bind_key('R')  # press 'R' to start/stop recording
def toggle_recording(viewer):
    global status_label
    if not recorder.is_recording:
        recorder.start_recording(viewer)
        viewer3d.get_status_label().setText("Recording status: recording...")  
        viewer3d.get_status_label().setStyleSheet("color: red;")
        print("Start recording...")
    else:
        recorder.stop_recording()
        viewer3d.get_status_label().setText("Recording status: Not recording")
        viewer3d.get_status_label().setStyleSheet("color: green;")
        print("Stop recording...")


# automatically stop recording when the window is closed
def on_close(event):
    if recorder.is_recording:
        recorder.stop_recording()
viewer.window._qt_window.closeEvent = on_close

napari.run()

