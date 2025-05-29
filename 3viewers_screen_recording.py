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

FONT_PATH = os.path.dirname(__file__)+'/assets/arial.ttf'  # font file path
# FONT_PATH = None
FONT_SIZE = 30
TEXT_COLOR = 255  
TEXT_POSITION = (10, 10)  # text position
MAX_TEXT_DURATION = 5  # seconds of text duration
RECTANGLE_COLOR = 'lime'  # rectangle color (green)
RECTANGLE_WIDTH = 1 # rectangle line width
RECORD_PATH = os.path.dirname(__file__)+'/recorded_materials/'

# Initialize recorder
recorder = ScreenRecorder(FONT_PATH=FONT_PATH, FONT_SIZE=FONT_SIZE, RECORD_PATH=RECORD_PATH, FPS=FPS, MAX_TEXT_DURATION=MAX_TEXT_DURATION)
recorder.text_color = TEXT_COLOR

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
        default_file = "T2G002_MRI_Spine_t2_space_sag_p2_iso_20240820161941_19001.nii.gz"
        print(f"No file specified, using default file: {default_file}")
        file_name = default_file
    else:
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
        
    viewer = viewer3d.get_viewer()
    # points_layer = viewer3d.get_points_layer()

    QTimer.singleShot(50, lambda: [
        [tb.setVisible(False) for tb in viewer.window._qt_window.findChildren(QToolBar)],
        viewer.window._qt_window.menuBar().setVisible(False),
        viewer.window._qt_window.statusBar().setVisible(False),
        [btn.setVisible(False) for btn in viewer.window._qt_window.findChildren(QPushButton) 
         if btn.objectName() not in ["audio_record_btn", "ai_submit_btn", "toggle_rect_btn"]],  # add audio_record_btn
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

    # # Add points layer and other existing logic
    # points_layer = viewer.add_points(
    #     name='3d corresponding points',
    #     ndim=3,
    #     size=3,
    #     face_color='red'
    # )

    # points_layer = viewer3d.get_points_layer()
    # # 初始化previous_point_count为当前点数
    # previous_point_count = len(points_layer.data)

    # def on_points_changed(event):
    #     nonlocal previous_point_count
    #     current_points = event.source.data   # 所有点的坐标数组
    #     current_count = len(current_points)

    #     # 如果当前点数大于之前存储的点数，说明新增了点
    #     if current_count > previous_point_count:
    #         # 新增的点就是current_points[previous_point_count: current_count]
    #         new_points = current_points[previous_point_count: current_count]
    #         for point in new_points:
    #             # 对每个新增的点，记录日志
    #             current_z, current_y, current_x = viewer.dims.current_step
    #             timestamp_log = datetime.now().strftime('%H:%M:%S')
    #             # 点坐标顺序：point[0]是z, point[1]是y, point[2]是x -> 转换为x, y, z
    #             x, y, z = point[2], point[1], point[0]
    #             log_text = f"[Point Annotation] {timestamp_log}\n"
    #             log_text += f"Point coordinate (data): (x={x}, y={y}, z={z})\n"
    #             log_text += f"Current slice index: (z={current_z}, y={current_y}, x={current_x})\n"
    #             log_text += "------------------------\n"
    #             if recorder.is_recording:
    #                 recorder.add_annotation(log_text)
    #         # 更新previous_point_count
    #         previous_point_count = current_count

    #     # 如果点数减少，则更新previous_point_count，但不记录
    #     else:
    #         previous_point_count = current_count

    # # 绑定事件
    # points_layer.events.data.connect(on_points_changed)

    # @viewer.bind_key('P')
    # def add_new_points_layer(viewer):
    #     # Create a more unique name using both timestamp and microseconds
        
    #     # Get current image layer for scale and translate properties
    #     image_layer = viewer.layers['Sagittal']
        
    #     # Create new points layer with the same scale and translate as the image
    #     new_points_layer = viewer.add_points(
    #         name='points_layer',
    #         ndim=3,
    #         size=3,
    #         face_color='red',
    #         scale=image_layer.scale,
    #         translate=image_layer.translate
    #     )
        
    #     # Make the new layer the active layer and ensure it's selected
    #     # viewer.layers.selection.clear()
    #     # viewer.layers.selection.add(new_points_layer)
    #     viewer.layers.selection.active = new_points_layer
        
    #     # Add points change event handler for the new layer
    #     def on_points_changed(event):
    #         current_points = event.source.data
    #         if len(current_points) > 0:
    #             # Get the most recently added point
    #             new_point = current_points[-1]
    #             current_z, current_y, current_x = viewer.dims.current_step
    #             timestamp_log = datetime.now().strftime('%H:%M:%S')
                
    #             # Convert point coordinates (z,y,x format to x,y,z format)
    #             x, y, z = new_point[2], new_point[1], new_point[0]
    #             log_text = f"[Point Annotation\n"
    #             log_text += f"Point coordinate (data): (x={x}, y={y}, z={z})\n"
    #             log_text += f"Current slice index: (z={current_z}, y={current_y}, x={current_x})\n"
    #             log_text += "------------------------\n"
                
    #             if recorder.is_recording:
    #                 recorder.add_annotation(log_text)
        
    #     # Connect the event handler
    #     new_points_layer.events.data.connect(on_points_changed)
        
    #     # Update status label to show current active layer
    #     viewer3d.get_status_label().setText(f"Active Layer: {layer_name}")
    #     viewer3d.get_status_label().setStyleSheet("color: blue;")

    def on_shape_added(event):
        print(f'====on_shape_added')
        """Shape addition event handler"""

        if not event.source.data:
            print("Warning: Received empty shape data event")
            return

        try:
            latest_rect = event.source.data[-1]
            print(f'==viewer3d.rect_metadata={viewer3d.rect_metadata}')
            
            # Get physical coordinates
            image_layer = viewer.layers['Sagittal']
            origin_point = np.array([[0, 0]])  
            origin_physical = origin_point * image_layer.scale + image_layer.translate
            physical_coord = latest_rect - origin_physical
            coord_str = f"Physical coordinates: {np.round(physical_coord, 2).tolist()}"

            # Define rect_id before metadata initialization
            rect_id = len(viewer3d.rect_metadata)  # Add rect_id definition
            # audio_path = f"{recorder.image_name}_rect{rect_id}_annotation.wav"
            # Get current slice position
            current_z, current_y, current_x = viewer.dims.current_step
            print(f'current_z, current_y, current_x: {current_z, current_y, current_x}')
            
            # 只保存元数据，不立即写入日志
            timestamp_log = datetime.now().strftime('%H:%M:%S')
            viewer3d.rect_metadata[rect_id] = {
                "text": "",
                # "audio": audio_path,  # save the audio_filename
                "coords": physical_coord.tolist(),
                "slice_indices": (current_z, current_y, current_x),
                "timestamp": timestamp_log,
                "coord_str": coord_str
            }

            # Create list item with user data (rect_id)
            # item = QListWidgetItem(f"Rectangle {rect_id+1} - {audio_path}")
            item = QListWidgetItem(f"Rectangle {rect_id+1}")
            item.setData(Qt.UserRole, rect_id)  # Store corresponding metadata ID
            # viewer3d.rect_list.addItem(item)

        except IndexError as e:
            print(f"Error processing shape data: {str(e)}")
        except KeyError as e:
            print(f"Sagittal layer not found: {str(e)}")
        
        # Connect double-click event (should be set during ViewerUI initialization)
        viewer3d.rect_list.itemDoubleClicked.connect(viewer3d.on_rect_item_clicked)

    def save_all_annotations():
        """Save all rectangle annotations to log at once"""
        if not viewer3d.rect_metadata:
            return
        
        # check for duplicate coordinates
        unique_coords = {}
        duplicate_ids = set()
        
        # first: find all duplicate coordinates
        for rect_id, metadata in viewer3d.rect_metadata.items():
            coords_tuple = tuple(map(tuple, metadata.get("coords", [])))
            if coords_tuple in unique_coords:
                duplicate_ids.add(rect_id)
            else:
                unique_coords[coords_tuple] = rect_id
        
        # second: remove duplicate coordinates
        for dup_id in duplicate_ids:
            if dup_id in viewer3d.rect_metadata:
                print(f"remove duplicated rectangle ID: {dup_id}")
                del viewer3d.rect_metadata[dup_id]
        
        # third: update rect_id and rect_metadata
        old_to_new_id = {}
        new_metadata = {}
        
        for new_id, (old_id, metadata) in enumerate(sorted(viewer3d.rect_metadata.items())):
            old_to_new_id[old_id] = new_id
            new_metadata[new_id] = metadata
        
        viewer3d.rect_metadata = new_metadata
        
        # update rectangle_list
        viewer3d.rect_list.clear()
        for rect_id, metadata in viewer3d.rect_metadata.items():
            audio_path = metadata.get("audio", "")
            # item = QListWidgetItem(f"Rectangle {rect_id+1} - {audio_path}")
            item = QListWidgetItem(f"Rectangle {rect_id+1}")
            item.setData(Qt.UserRole, rect_id)
            viewer3d.rect_list.addItem(item)
        
        # generate all annotations
        all_annotations = []
        for rect_id, metadata in viewer3d.rect_metadata.items():
            timestamp_log = metadata.get("timestamp", datetime.now().strftime('%H:%M:%S'))
            coord_str = metadata.get("coord_str", "")
            audio_path = metadata.get("audio", "")
            current_z, current_y, current_x = metadata.get("slice_indices", (0, 0, 0))
            
            log_text = f"[Rectangle {rect_id} Annotation] {timestamp_log}\n{coord_str}\nNote: Audio: {audio_path}\n(x={current_x}, y={current_y}, z={current_z})\n------------------------\n"
            all_annotations.append(log_text)
        
        # Add all annotations to the log at once
        if all_annotations and recorder.is_recording:
            try:
                recorder.add_annotation("".join(all_annotations))
                print(f"Added {len(all_annotations)} annotations to the log")
            except Exception as e:
                print(f"Error writing annotations: {str(e)}")


    # ================= bind with key ======================
    @viewer.bind_key('R')  # press to start/stop recording
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
            save_all_annotations() 
            recorder.stop_recording()
        viewer.window.close()


    @viewer.bind_key('M')
    def toggle_rectangle_mode(viewer):
        global shapes_layer, image_layer

        # Hide previous annotation layers
        for layer in viewer.layers:
            if isinstance(layer, napari.layers.Shapes) and layer.name.startswith('add rectangle'):
                layer.visible = False

        # Create a layer with unique name each time
        import time
        layer_name = f'add rectangle {int(time.time())}'

        # Get current Sagittal layer
        image_layer = viewer.layers['Sagittal']

        # Check if current Z-axis slice is valid
        current_z = viewer.dims.current_step[0]
        max_z = viewer3d.image_array.shape[0] - 1
        if not (0 <= current_z <= max_z):
            viewer3d.get_status_label().setText("Please select a valid Z-axis slice")
            viewer3d.get_status_label().setStyleSheet("color: red;")
            return

        # Create new rectangle layer
        shapes_layer = viewer.add_shapes(
            name=layer_name,
            shape_type='rectangle',
            edge_color=RECTANGLE_COLOR,
            edge_width=RECTANGLE_WIDTH,
            face_color=[0,0,0,0],
            ndim=2,
            scale=image_layer.scale,
            translate=image_layer.translate
        )
        viewer.layers.move(len(viewer.layers)-1, -1)
        shapes_layer._event_connected = False  # Initialize flag

        # Only bind event once
        if not getattr(shapes_layer, '_event_connected', False):
            shapes_layer.events.data.connect(viewer3d.on_shape_added)
            shapes_layer._event_connected = True

        # Disable interaction with other layers
        with shapes_layer.events.data.blocker():
            for layer in viewer.layers:
                layer.mouse_pan = False
                layer.mouse_zoom = False
            viewer.layers.move(viewer.layers.index(shapes_layer), -1)

        viewer3d.get_status_label().setText(f"Mode: Rectangle Annotation ({layer_name})")
        viewer3d.get_status_label().setStyleSheet("color: blue;")


    @viewer.bind_key('C')  
    def refresh_polygons(viewer):
        # print('===type C key===')
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

    @viewer.bind_key('D')  # Press R key to open 3D view
    def open_3d_view(viewer):
        """Open 3D view window"""
        import subprocess
        try:
            subprocess.Popen([
                sys.executable,
                os.path.join(os.path.dirname(__file__), 'show_3d_view.py'),
                file_name  # Use current opened file
            ], shell=False)
            print("Opening 3D view...")
        except Exception as e:
            print(f"Failed to launch 3D view: {str(e)}")

    # automatically stop recording when the window is closed
    def on_close(event):
        if recorder.is_recording:
            save_all_annotations() 
            recorder.stop_recording()
    viewer.window._qt_window.closeEvent = on_close

    napari.run()

if __name__ == "__main__":
    main()
    # plot()