import os
import sys
sys.path.append(os.path.dirname(__file__)+'/napari-nifti-main/src/')
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
from qtpy.QtWidgets import QListWidgetItem 

import sounddevice as sd 
from scipy.io.wavfile import write as write_wav

# set the parameters
FPS = 15  # frames per second
RECORD_REGION = None  # set the recording region to default

FONT_PATH = "arial.ttf"  # font file path
FONT_SIZE = 30
TEXT_COLOR = 255  
TEXT_POSITION = (10, 10)  # text position
MAX_TEXT_DURATION = 5  # seconds of text duration
RECTANGLE_COLOR = 'lime'  # rectangle color (green)
RECTANGLE_WIDTH = 1 # rectangle line width
RECORD_PATH = os.path.dirname(__file__)+'/recorded_materials/'

# Initialize recorder
recorder = ScreenRecorder(FONT_PATH=FONT_PATH, FONT_SIZE=FONT_SIZE, RECORD_PATH=RECORD_PATH, FPS=FPS, MAX_TEXT_DURATION=MAX_TEXT_DURATION)

# set the file path
IMAGE_PATH = os.path.dirname(__file__)+'/data/'
IMAGE_NAME = ["/T2G003_Spine_NIFTI/Dicoms_Spine_MRI_t2_space_sag_p2_iso_2050122160508_5001.nii.gz"]

def plot():
    for file in IMAGE_LIST:
        img = nib.load(file)
        print(f"File: {os.path.basename(file)}")
        print(f"Data shape: {img.header.get_data_shape()}")
        print(f"Voxel size (mm): {img.header.get_zooms()}")
        print(f"Orientation: {nib.orientations.aff2axcodes(img.affine)}\n")

def main():
    previous_length = 0

    if len(sys.argv) < 2:
        print("Please select a NIfTI file through file navigator")  # More specific prompt
        sys.exit(1)
        
    file_name = sys.argv[1].strip('"')  # Remove potential quotes
    IMAGE_PATH = os.path.join(os.path.dirname(__file__), 'data')  # Standardize path format
    filepath = os.path.join(IMAGE_PATH, file_name)
    
    # Add path validation
    if not os.path.exists(filepath):
        print(f"File path does not exist: {filepath}")
        sys.exit(1)

    rel_path = os.path.relpath(filepath, IMAGE_PATH)
    image_name = os.path.splitext(rel_path)[0].replace('/', '_').replace('\\', '_')
    recorder.image_name = image_name
    recorder.image_name = image_name

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

    viewer3d = ViewerUI(image_array=image_array, metadata=metadata, filepath=filepath, \
                    recorder=recorder, RECORD_PATH=RECORD_PATH)
    viewer = viewer3d.get_viewer()

    # 在初始化时添加(0, 0)点进行测试
    image_layer = viewer.layers['Sagittal']
    origin_point = np.array([[0, 0]]) 
    origin_physical = origin_point * image_layer.scale + image_layer.translate
    viewer.add_points(
        origin_physical,
        name='Origin Point',
        size=2,
        face_color='blue',
        edge_color='black'
    )

    def calculate_base_scale(image_shape, screen_size):
        """Calculate base scaling ratio based on image dimensions and screen space"""
        screen_width = screen_size[0] // 2  
        screen_height = screen_size[1] // 2  
        
        base_scale_z = screen_width / image_shape[0]
        base_scale_xy = min(
            screen_width / image_shape[1], 
            screen_height / image_shape[2]
        )
        return (base_scale_z, base_scale_xy, base_scale_xy)

    def calculate_translate_offset(data_shape):
        return {
            'sagittal': (-data_shape[1]//2, -data_shape[2]//2),  
            'axial': (-data_shape[1]//2, 0)                      
        }

    # # Apply scaling parameters to view
    # viewer3d.apply_layout_settings()

    def update_slices(event):
        viewer3d._update_slices(event)
    def on_points_changed(event):
        viewer3d._on_points_changed(event)
    viewer = viewer3d.get_viewer()
    points_layer = viewer3d.get_points_layer()

    QTimer.singleShot(50, lambda: [
        [tb.setVisible(False) for tb in viewer.window._qt_window.findChildren(QToolBar)],
        viewer.window._qt_window.menuBar().setVisible(False),
        viewer.window._qt_window.statusBar().setVisible(False),
        [btn.setVisible(False) for btn in viewer.window._qt_window.findChildren(QPushButton) 
         if btn.objectName() not in ["audio_record_btn", "ai_submit_btn"]],  # add audio_record_btn
    ])
    
    # Add timer for auto-start recording after UI loading completes
    QTimer.singleShot(500, lambda: [
        recorder.start_recording(viewer),
        viewer3d.get_status_label().setText("Recording status: recording..."),
        viewer3d.get_status_label().setStyleSheet("color: red;"),
        print("start recording automatically...")
    ])
    
    # Connect dimension updates
    viewer.dims.events.current_step.connect(update_slices)

    # Add points layer and other existing logic
    points_layer = viewer.add_points(
        name='3d corresponding points',
        ndim=3,
        size=3,
        face_color='red'
    )

    def on_points_changed(event):
        nonlocal previous_length

        """Points layer change handler"""
        current_data = points_layer.data
        current_length = len(current_data)
        
        if current_length > previous_length:
            new_points = current_data[previous_length:current_length]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            current_step = viewer.dims.current_step
            print(f'current_step={current_step}')
            image_layer = viewer.layers['Sagittal']
            image_bias = np.array([0, 0]) * image_layer.scale + image_layer.translate
            
            log_info = []
            for pt in new_points:
                pt_modified = np.array(pt)
                pt_modified[1] = current_step[1]
                physical_coord = pt_modified - np.array([image_bias[1], 0, image_bias[0]])
                log_entry = (
                    f"[Point Annotation] {timestamp}\n"
                    f"Spatial coordinates: {np.round(physical_coord, 0)}\n"
                    f"Current slice: [dim0:{current_step[0]}, dim1:{current_step[1]}, dim2:{current_step[2]}]\n"
                    "------------------------\n"
                )
                log_info.append(log_entry)
            
            if recorder.is_recording: 
                recorder.add_annotation(log_info)
            
            previous_length = current_length

    points_layer.events.data.connect(on_points_changed)

    def on_shape_added(event):
        """Shape addition event handler"""

        if not event.source.data:
            print("Warning: Received empty shape data event")
            return

        try:
            latest_rect = event.source.data[-1]
            
            # Get physical coordinates
            image_layer = viewer.layers['Sagittal']
            origin_point = np.array([[0, 0]])  
            origin_physical = origin_point * image_layer.scale + image_layer.translate
            physical_coord = latest_rect - origin_physical
            coord_str = f"Physical coordinates: {np.round(physical_coord, 2).tolist()}"
            
            # Write information to log file
            timestamp_log = datetime.now().strftime('%H:%M:%S')
            try:
                log_text = f"[Rectangle Annotation] {timestamp_log}\n{coord_str}\nNote: Audio: {audio_filename}\n------------------------\n"
                recorder.add_annotation(log_text)  # Call recorder's recording method
            except Exception as e:
                print(f"Error writing annotation: {str(e)}")
                if recorder.is_recording:
                    recorder.stop_recording()
                    print("Recording stopped due to annotation error")

            # Get current slice position
            current_z, current_y, current_x = viewer.dims.current_step
            print(f'current_z, current_y, current_x: {current_z, current_y, current_x}')
            
            # Define rect_id before metadata initialization
            rect_id = len(viewer3d.rect_metadata)  # Add rect_id definition
            audio_path = f"{recorder.image_name}_annotation.wav"
            viewer3d.rect_metadata[rect_id] = {
                "text": "",
                "audio": audio_path,  # save the audio_filename
                "coords": physical_coord.tolist(),
                "slice_indices": (current_z, current_y, current_x)
            }

            # Create list item with user data (rect_id)
            item = QListWidgetItem(f"Rectangle {rect_id+1} - {audio_path}")
            item.setData(Qt.UserRole, rect_id)  # Store corresponding metadata ID
            viewer3d.rect_list.addItem(item)

        except IndexError as e:
            print(f"Error processing shape data: {str(e)}")
        except KeyError as e:
            print(f"Sagittal layer not found: {str(e)}")
        
        # Connect double-click event (should be set during ViewerUI initialization)
        viewer3d.rect_list.itemDoubleClicked.connect(viewer3d.on_rect_item_clicked)


    # ================= bind with key ======================
    @viewer.bind_key('M')  # press to start/stop recording
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
    
    @viewer.bind_key('Escape') # need to exit the B editing mode
    def close_window(viewer):
        """close current window"""
        if recorder.is_recording:
            recorder.stop_recording()
        viewer.window.close()


    @viewer.bind_key('B')
    def toggle_rectangle_mode(viewer):
        global shapes_layer, image_layer
        
        # Check if already in rectangle annotation mode
        if 'add rectangle' in viewer.layers and viewer.layers['add rectangle'].visible:
            # Exit rectangle annotation mode
            shapes_layer = viewer.layers['add rectangle']
            shapes_layer.visible = False
            
            # Restore mouse interaction for all layers
            for layer in viewer.layers:
                layer.mouse_pan = True
                layer.mouse_zoom = True
            
            viewer3d.get_status_label().setText("Mode: Normal")
            viewer3d.get_status_label().setStyleSheet("color: green;")
            return
        
        # Enter rectangle annotation mode
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
            shapes_layer.visible = True
            # Precisely disconnect the specified event handler
            try:
                shapes_layer.events.data.disconnect(on_shape_added)
            except:
                pass

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
        # Get all annotation data
        annotation_count, annotations = viewer3d.count_polygons()
        
        # Clear and update right side list
        rect_list = viewer3d.side_panel.findChild(QListWidget)
        rect_list.clear()

        for idx, ann in enumerate(annotations, 1):
            item_text = f"Rectangle {idx} [Sagittal]\nAnnotation: {ann.get('text','')}\n" + \
                f"[{ann['layer']}]\nVertices: {len(ann['coordinates'])}\n" 
                
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.TextWordWrap)  # Enable text wrapping
            rect_list.addItem(item)


    # automatically stop recording when the window is closed
    def on_close(event):
        if recorder.is_recording:
            recorder.stop_recording()
    viewer.window._qt_window.closeEvent = on_close

    napari.run()

if __name__ == "__main__":
    main()
    # plot()