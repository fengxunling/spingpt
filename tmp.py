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


# Create Viewer and add 3D image layer (hidden)
viewer = Viewer()
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

from qtpy.QtWidgets import QSlider, QWidget, QVBoxLayout

slider_container = QWidget()
slider_container.setMinimumWidth(300)  # set minimum width
slider_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # allow horizontal expansion
main_layout = QVBoxLayout()
main_layout.setContentsMargins(10, 5, 10, 5)  # add margin
slider_layout = QVBoxLayout()

x_container = QWidget()
x_layout = QVBoxLayout()
x_slider = QSlider()
x_slider.setOrientation(1)
x_slider.setMinimum(0)
x_slider.setMaximum(image_array.shape[2]-1)
x_slider.setValue(image_array.shape[2] // 2)
max_x = image_array.shape[2]-1
x_label = QLabel(f"X: {x_slider.value()}/{max_x}")
def update_x(value):
    current_step = list(viewer.dims.current_step)
    current_step[2] = value
    viewer.dims.current_step = tuple(current_step)
    x_label.setText(f"X: {value}/{max_x}")
x_slider.valueChanged.connect(update_x)
x_layout.addWidget(x_slider)
x_layout.addWidget(x_label)
x_container.setLayout(x_layout)

y_container = QWidget()
y_layout = QVBoxLayout()
y_slider = QSlider()
y_slider.setOrientation(1)
y_slider.setMinimum(0)
y_slider.setMaximum(image_array.shape[1]-1)
y_slider.setValue(image_array.shape[1] // 2)
max_y = image_array.shape[1]-1  
y_label = QLabel(f"Y: {y_slider.value()}/{max_y}")
def update_y(value):
    current_step = list(viewer.dims.current_step)
    current_step[1] = value
    viewer.dims.current_step = tuple(current_step)
    y_label.setText(f"Y: {value}/{max_y}") 
y_slider.valueChanged.connect(update_y)
y_layout.addWidget(y_slider)
y_layout.addWidget(y_label)
y_container.setLayout(y_layout)

z_container = QWidget()
z_layout = QVBoxLayout()
z_slider = QSlider()
z_slider.setOrientation(1)
z_slider.setMinimum(0)
z_slider.setMaximum(image_array.shape[0]-1)
z_slider.setValue(image_array.shape[0] // 2)
max_z = image_array.shape[0]-1 
z_label = QLabel(f"Z: {z_slider.value()}/{max_z}")
def update_z(value):
    current_step = list(viewer.dims.current_step)
    current_step[0] = value
    viewer.dims.current_step = tuple(current_step)
    z_label.setText(f"Z: {value}/{max_z}")
z_slider.valueChanged.connect(update_z)
z_layout.addWidget(z_slider)
z_layout.addWidget(z_label)
z_container.setLayout(z_layout)

slider_layout.addWidget(x_container) 
slider_layout.addWidget(y_container)
slider_layout.addWidget(z_container)

# create the recording mode annotation
status_label = QLabel("Recording status: Not recording")
status_label.setStyleSheet("color: green;")  
status_label.setAlignment(Qt.AlignCenter)
image_name_label = QLabel("Current Image: ")
image_name_label.setAlignment(Qt.AlignCenter)
image_name_label.setWordWrap(True)  # add auto wrap
image_name_label.setStyleSheet("QLabel { margin: 5px 20px; }")  # add margin
main_layout.addWidget(status_label)
main_layout.addWidget(image_name_label)

# create button for loading images
nav_buttons_layout = QHBoxLayout()
prev_btn = QPushButton("Previous")
prev_btn.setObjectName("nav_prev_btn") 
next_btn = QPushButton("Next")
next_btn.setObjectName("nav_next_btn") 
nav_buttons_layout.addWidget(prev_btn)
nav_buttons_layout.addWidget(next_btn)

def load_image(idx):
    global image_array, metadata, image_layer, dimensions, voxel_sizes
    filepath = IMAGE_LIST[idx]
    img = nib.load(filepath)
    image_name = os.path.splitext(os.path.basename(filepath))[0]
    recorder.image_name = image_name
    image_name_label.setText(f"Current Image: {image_name}")
    
    layer_data = napari_get_reader(filepath)(filepath)
    image_array = layer_data[0][0]
    metadata = layer_data[0][1]
    
    image_layer.data = image_array
    image_layer.refresh()
    
    x_slider.setMaximum(image_array.shape[2]-1)
    y_slider.setMaximum(image_array.shape[1]-1)
    z_slider.setMaximum(image_array.shape[0]-1)

def prev_image():
    global current_image_idx
    if current_image_idx > 0:
        current_image_idx -= 1
        load_image(current_image_idx)

def next_image():
    global current_image_idx
    if current_image_idx < len(IMAGE_LIST)-1:
        current_image_idx += 1
        load_image(current_image_idx)

prev_btn.clicked.connect(prev_image)
next_btn.clicked.connect(next_image)

# create input box
input_layout = QHBoxLayout()
annotation_input = QLineEdit()
annotation_input.setPlaceholderText("Input...")
submit_btn = QPushButton("Submit")
submit_btn.setObjectName("submit_btn") 
input_layout.addWidget(annotation_input)
input_layout.addWidget(submit_btn)

def submit_annotation():
    text = annotation_input.text()
    if text:
        recorder.add_annotation(text)
        annotation_input.clear()
        print(f"Already add: {text}")
submit_btn.clicked.connect(submit_annotation)
annotation_input.returnPressed.connect(submit_btn.click)

# add the slider and input box to the main layout
main_layout.addLayout(slider_layout)  # add the slider first
main_layout.addLayout(nav_buttons_layout) # add the navigation buttons
main_layout.addLayout(input_layout)   # then add the input box
slider_container.setLayout(main_layout)  # set the main layout to the container

# Sync sliders with the viewer
def sync_sliders(event):
    current_z = np.clip(viewer.dims.current_step[0], 0, image_array.shape[0]-1) # add bounder check
    current_y = np.clip(viewer.dims.current_step[1], 0, image_array.shape[1]-1) 
    current_x = np.clip(viewer.dims.current_step[2], 0, image_array.shape[2]-1)

# add the whole container to the dock 
axis_controls_dock = viewer.window.add_dock_widget(
    slider_container, 
    name="Axis Controls",
    area='left', 
    allowed_areas=['left', 'right'], 
)
slider_container.setStyleSheet("""
    QWidget {
        alignment: left;
        margin-left: 5px;
    }
    QSlider {
        min-width: 120px;
    }
""")


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
        status_label.setText("Recording status: recording...")
        status_label.setStyleSheet("color: red;")  
        print("Start recording...")
    else:
        recorder.stop_recording()
        status_label.setText("Recording status: Not recording")
        status_label.setStyleSheet("color: green;")  
        print("Stop recording...")


# automatically stop recording when the window is closed
def on_close(event):
    if recorder.is_recording:
        recorder.stop_recording()
viewer.window._qt_window.closeEvent = on_close

napari.run()

