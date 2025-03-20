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
from qtpy.QtWidgets import (
    QLineEdit, QPushButton, QHBoxLayout, QToolBar, QSlider, 
    QWidget, QLabel, QSizePolicy, QInputDialog, QListWidgetItem, QListWidget 
)
from recorder import ScreenRecorder
from viewer_module import ViewerUI
# 在现有导入后添加
from qtpy.QtWidgets import QListWidgetItem  # 新增导入

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
RECTANGLE_COLOR = 'lime'  # 新增：矩形框颜色（绿色）
RECTANGLE_WIDTH = 1           # 新增：矩形框线宽

# 初始化录制器
recorder = ScreenRecorder(FONT_PATH=FONT_PATH, FONT_SIZE=FONT_SIZE, RECORD_PATH=RECORD_PATH, FPS=FPS, MAX_TEXT_DURATION=MAX_TEXT_DURATION)

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
def update_slices(event):
    viewer3d._update_slices(event)
def on_points_changed(event):
    viewered._on_points_changed(event)
viewer = viewer3d.get_viewer()
points_layer = viewer3d.get_points_layer()


# viewer.window._qt_window.showFullScreen() # full screen
QTimer.singleShot(100, lambda: [
    [tb.setVisible(False) for tb in viewer.window._qt_window.findChildren(QToolBar)],
    viewer.window._qt_window.menuBar().setVisible(False),
    viewer.window._qt_window.statusBar().setVisible(False),
    [btn.setVisible(False) for btn in viewer.window._qt_window.findChildren(QPushButton) 
     if btn.objectName() not in ["nav_prev_btn", "nav_next_btn", "submit_btn"]],  # 过滤保留的按钮
])


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

points_layer.events.data.connect(on_points_changed)

def on_shape_added(event):
    """Shape addition event handler"""
    if not event.source.data:
        print("Warning: Received empty shape data event")
        return

    try:
        latest_rect = event.source.data[-1]
        rect_info = f"Rectangle coordinates: {np.round(latest_rect, 2).tolist()}"
        
        # Get physical coordinates
        image_layer = viewer.layers['Sagittal']
        physical_coord = latest_rect * image_layer.scale + image_layer.translate
        coord_str = f"Physical coordinates: {np.round(physical_coord, 2).tolist()}"
        
        # Write information to log file
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_text = f"[Rectangle Annotation] {timestamp}\n{rect_info}\n{coord_str}\n------------------------\n"
        recorder.add_annotation(log_text)  # Call recorder's recording method

    except IndexError as e:
        print(f"Error processing shape data: {str(e)}")
    except KeyError as e:
        print(f"Sagittal layer not found: {str(e)}")

    # 初始化元数据
    rect_id = len(viewer3d.rect_metadata)
    viewer3d.rect_metadata[rect_id] = {
        "text": "",  # 初始化为空字符串
        "audio": "",
        "coords": physical_coord.tolist()
    }
    # 创建带用户数据（rect_id）的列表项
    item = QListWidgetItem(f"矩形 {rect_id+1} [Sagittal]")
    item.setData(Qt.UserRole, rect_id)  # 存储对应的元数据ID
    viewer3d.rect_list.addItem(item)
    
    # 连接双击事件（应在 ViewerUI 初始化时设置）
    viewer3d.rect_list.itemDoubleClicked.connect(viewer3d.on_rect_item_clicked)


# ================= bind with key ======================
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


@viewer.bind_key('B')
def toggle_rectangle_mode(viewer):
    global shapes_layer, image_layer
    
    # Get current axial view layer
    image_layer = viewer.layers['Sagittal']
    
    # Check if current dimension is axial view (third dimension)
    current_z = viewer.dims.current_step[0]  
    max_z = viewer3d.image_array.shape[0] - 1
    if not (0 <= current_z <= max_z):
            viewer3d.get_status_label().setText("Please select a valid Z-axis slice")
            viewer3d.get_status_label().setStyleSheet("color: red;")
            return
    
    # Create or get rectangle layer
    if 'add rectangle' not in viewer.layers:
        shapes_layer = viewer.add_shapes(
            name='add rectangle',
            shape_type='rectangle',
            edge_color=RECTANGLE_COLOR,
            edge_width=RECTANGLE_WIDTH,
            face_color=[0,0,0,0],
            ndim=2,
            scale=image_layer.scale,
            translate=image_layer.translate
        )
        viewer.layers.move(len(viewer.layers)-1, -1)
        # Set flag immediately during initialization
        shapes_layer._event_connected = False  # Add initialization flag
    else:
        shapes_layer = viewer.layers['add rectangle']
        # Precisely disconnect the specified event handler
        shapes_layer.events.data.disconnect(on_shape_added)  # Modified for precise disconnection

    # Ensure single event binding
    if not getattr(shapes_layer, '_event_connected', False):
        shapes_layer.events.data.connect(on_shape_added)
        shapes_layer._event_connected = True  # Update flag

    # Disable interaction with other layers
    with shapes_layer.events.data.blocker():
        for layer in viewer.layers:
            layer.mouse_pan = False
            layer.mouse_zoom = False
        viewer.layers.move(viewer.layers.index(shapes_layer), -1)
    
    viewer3d.get_status_label().setText("Mode: Rectangle Annotation")
    viewer3d.get_status_label().setStyleSheet("color: blue;")

@viewer.bind_key('C')  
def refresh_polygons(viewer):
    print('===type C key===')
    # 获取所有标注数据
    annotation_count, annotations = viewer3d.count_polygons()
    # print(f'====annotation_count={annotation_count}, annotations={annotations}')

    # 获取多边形数据
    polygon_count, polygons = viewer3d.count_polygons()
    # print(f'polygon_count:{polygon_count}')
    # print(f'polygons:{polygons}')
    
    # 清空并更新右侧列表
    rect_list = viewer3d.side_panel.findChild(QListWidget)
    rect_list.clear()

    for idx, ann in enumerate(annotations, 1):
        item_text = f"矩形 {idx} [Sagittal] - 注释: {ann.get('text','')}" + \
            f"多边形 {idx} [{ann['layer']}] - {len(ann['coordinates'])}顶点"
            
        item = QListWidgetItem(item_text)
        rect_list.addItem(item)


# automatically stop recording when the window is closed
def on_close(event):
    if recorder.is_recording:
        recorder.stop_recording()
viewer.window._qt_window.closeEvent = on_close

napari.run()


 