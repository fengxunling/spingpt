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

# set the parameters
RECORD_PATH = os.path.dirname(__file__)+'/recorded_materials/'  # recording file path
VIDEO_PATH = RECORD_PATH+"operation_recording.mp4"  # video file path
FPS = 15  # frames per second
RECORD_REGION = None  # set the recording region to default

FONT_PATH = "arial.ttf"  # font file path
FONT_SIZE = 20
TEXT_COLOR = (255, 0, 0)  # red text
TEXT_POSITION = (10, 10)  # text position
MAX_TEXT_DURATION = 5  # seconds of text duration

class ScreenRecorder:
    def __init__(self):
        self.is_recording = False
        self.writer = None
        self.monitor = None
        self.capture_thread = None
        self.start_time = None
        self.end_time = None
        self.text_queue = queue.Queue()  # (thread-safe text queue)
        self.font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        self.lock = threading.Lock()

        # add dynamic path for the image and video
        self.image_name = None
        self.video_path = None
        self.log_path = None
    
    def add_annotation(self, text):
        """Add text annotation"""
        timestamp = datetime.now()
        with self.lock:
            self.text_queue.put({
                "text": text,
                "timestamp": timestamp,
                "expire_time": timestamp.timestamp() + MAX_TEXT_DURATION
            })
        
        # write the annotation to the log
        if self.is_recording:
            log_entry = (
                f"[Annotation] {timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n"
                f"Content: {text}\n"
                "------------------------\n"
            )
            with open(RECORD_PATH+"3d_points_log.txt", "a") as f:
                f.write(log_entry)
    
    def _draw_text(self, img_np):
        """Draw text on the image"""
        current_time = time.time()
        
        # transfer the numpy array to PIL image
        pil_img = Image.fromarray(img_np)
        draw = ImageDraw.Draw(pil_img)
        
        # deal with all text annotations
        temp_queue = queue.Queue()
        while not self.text_queue.empty():
            annotation = self.text_queue.get()
            if current_time < annotation["expire_time"]:
                draw.text(TEXT_POSITION, 
                         f"{annotation['text']} ({annotation['timestamp'].strftime('%H:%M:%S')})",
                         fill=TEXT_COLOR, 
                         font=self.font)
                temp_queue.put(annotation)
        
        # update the text queue
        with self.lock:
            while not temp_queue.empty():
                self.text_queue.put(temp_queue.get())
        
        return np.array(pil_img)


    def start_recording(self, viewer):
        # auto detect the recording region and start recording
        self.is_recording = True
        self.start_time = datetime.now()

        # generate the file name
        timestamp_str = self.start_time.strftime("%Y%m%d_%H%M_%S")
        base_name = f"{timestamp_str}_{self.image_name}"
        self.video_path = os.path.join(RECORD_PATH, f"{base_name}.mp4")
        self.log_path = os.path.join(RECORD_PATH, f"{base_name}_log.txt")

        # write the start time to the log
        timestamp_start = self.start_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.log_path, "a") as f:
            f.write(f"\n[Video Recording Started] {timestamp_start}\n")
        
        # get the napari window coordinates
        win = viewer.window._qt_window
        win.moveEvent = lambda event: self._update_region(win)  # update the region when the window moves
        self._update_region(win)
        
        # intialize the video writer
        self.writer = get_writer(self.video_path, format='FFMPEG', fps=FPS)
        
        # start the screen capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.start()

    def _update_region(self, window):
        # update the napari window coordinates
        geo = window.geometry()
        self.monitor = {
            "left": geo.x(),
            "top": geo.y(),
            "width": geo.width(),
            "height": geo.height()
        }

    def _capture_loop(self):
        # get the screen capture object
        with mss() as sct:
            while self.is_recording:
                try:
                    # capture the screen region
                    img = np.array(sct.grab(self.monitor))
                    # transfrom to RGB format
                    img = img[..., :3]

                    # draw the text on the image
                    if not self.text_queue.empty():
                        img = self._draw_text(img)

                    # write the video frame
                    self.writer.append_data(img)
                    time.sleep(1/FPS)
                except Exception as e:
                    print(f"capture error: {str(e)}")
                    break

    def stop_recording(self):
        # stop the recording
        self.is_recording = False
        self.end_time = datetime.now()

        # write the end time to the log
        timestamp_end = self.end_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        duration = self.end_time - self.start_time
        with open(RECORD_PATH+"3d_points_log.txt", "a") as f:
            f.write(
                f"[Video Recording Ended] {timestamp_end}\n"
                f"[Duration] {duration.total_seconds():.2f} seconds\n\n"
            )

        if self.capture_thread:
            self.capture_thread.join()
        if self.writer:
            self.writer.close()
        print(f"The video is saved at: {os.path.abspath(VIDEO_PATH)}")

# initialize the screen recorder
recorder = ScreenRecorder()

# set the file path
filepath = "D:/projects/spingpt/data/Dicom_t2_trufi3d_cor_0.6_20230123141752_3.nii/Dicom_t2_trufi3d_cor_0.6_20230123141752_3.nii"
image_name = os.path.splitext(os.path.basename(filepath))[0]
recorder.image_name = image_name  # set the image name

img = nib.load(filepath)
header = img.header

# image dimensions
dimensions = header.get_data_shape()  
print(dimensions)
# voxel dimensions (in mm)
voxel_sizes = header.get_zooms()    
print(voxel_sizes) 

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
image_layer = viewer.add_image(image_array, **metadata, visible=False)

from qtpy.QtWidgets import QSlider, QWidget, QVBoxLayout

slider_container = QWidget()
slider_layout = QVBoxLayout()

# z axis slider
z_slider = QSlider()
z_slider.setOrientation(1)  # vertical slider
z_slider.setMinimum(0)
z_slider.setMaximum(image_array.shape[0]-1)  # use the first dimension
def update_z(value):
    current_step = list(viewer.dims.current_step)
    current_step[0] = value  # change the first dimension
    viewer.dims.current_step = tuple(current_step)
z_slider.valueChanged.connect(update_z)

# y axis slider
y_slider = QSlider()
y_slider.setOrientation(1)  # vertical slider
y_slider.setMinimum(0)
y_slider.setMaximum(image_array.shape[1]-1)
def update_y(value):
    current_step = list(viewer.dims.current_step)
    current_step[1] = value
    viewer.dims.current_step = tuple(current_step)
y_slider.valueChanged.connect(update_y)

# x axis slider
x_slider = QSlider()
x_slider.setOrientation(1)  # vertical slider
x_slider.setMinimum(0)
x_slider.setMaximum(image_array.shape[2]-1)
def update_x(value):
    current_step = list(viewer.dims.current_step)
    current_step[2] = value
    viewer.dims.current_step = tuple(current_step)
x_slider.valueChanged.connect(update_x)

# add sliders to the layout (in X-Y-Z order)
slider_layout.addWidget(x_slider)
slider_layout.addWidget(y_slider)
slider_layout.addWidget(z_slider)
slider_container.setLayout(slider_layout)
viewer.window.add_dock_widget(slider_container, name="Axis Controls")

# Sync sliders with the viewer
def sync_sliders(event):
    z_slider.setValue(viewer.dims.current_step[0]) 
    y_slider.setValue(viewer.dims.current_step[1])
    x_slider.setValue(viewer.dims.current_step[2])
viewer.dims.events.current_step.connect(sync_sliders)

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
coronal_layer = viewer.add_image(coronal_slice, name='Coronal')
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
axial_layer.translate = (130, -150)  # move the layer to the specified position
axial_layer.scale = [0.25, 0.25] 
sagittal_layer = viewer.layers['Sagittal'] 
sagittal_layer.translate = (-110, 90)  
sagittal_layer.scale = [0.25, 0.25] 
coronal_layer = viewer.layers['Coronal'] 
coronal_layer.translate = (-110, -150) 
coronal_layer.scale = [0.25, 0.25] 

# Create line layer
def create_line_layer(color, line_data, layer, name):
    return viewer.add_shapes(
        line_data,
        shape_type='line',
        edge_color=color,
        edge_width=1.5,
        scale=layer.scale,  # maintain the same scale as the corresponding view
        translate=layer.translate,  # align with the axial view
        visible=True,
        name=name
    )

# create line layers for each view
axial_h_line_data = np.array([[axial_slice.shape[1]-initial_y+1, 0], [axial_slice.shape[1]-initial_y+1, axial_slice.shape[1]]])
axial_v_line_data = np.array([[0, initial_x], [axial_slice.shape[0], initial_x]])
axial_h_line = create_line_layer('yellow', axial_h_line_data, axial_layer, 'axial_line1')  
axial_v_line = create_line_layer('skyblue', axial_v_line_data, axial_layer, 'axial_line2')  

coronal_h_line_data = np.array([[initial_z, 0], [initial_z, coronal_slice.shape[1]]])
coronal_v_line_data = np.array([[0, initial_x], [coronal_slice.shape[0], initial_x]])
coronal_h_line = create_line_layer('tomato', coronal_h_line_data, coronal_layer, 'coronal_line1')  
coronal_v_line = create_line_layer('skyblue', coronal_v_line_data, coronal_layer, 'coronal_line2')

sagittal_h_line_data = np.array([[initial_z, 0], [initial_z, sagittal_slice.shape[1]]])
sagittal_v_line_data = np.array([[0, initial_y], [sagittal_slice.shape[0], initial_y]])
sagittal_h_line = create_line_layer('tomato', sagittal_h_line_data, sagittal_layer, 'sagittal_line1') 
sagittal_v_line = create_line_layer('yellow', sagittal_v_line_data, sagittal_layer, 'saagittal_line2')


def update_slices(event):
    """Update the slices with rotation and text annotation"""
    z, y, x = viewer.dims.current_step
    
    # axial view (rotate 90 degrees counterclockwise)
    axial_slice = np.fliplr(np.rot90(image_array[z, :, :], k=2))
    axial_slice = add_text_to_slice(axial_slice, f"Axial (Z={z})\nY={y}\nX={x}")
    
    # coronal view (rotate 180 degrees counterclockwise)
    coronal_slice = np.fliplr(np.rot90(image_array[:, y, :], k=2))
    coronal_slice = add_text_to_slice(coronal_slice, f"Coronal (Y={y})\nZ={z}\nX={x}")
    
    # sagittal view
    sagittal_slice = np.fliplr(np.rot90(image_array[:, :, x], k=2))
    sagittal_slice = add_text_to_slice(sagittal_slice, f"Sagittal (X={x})\nZ={z}\nY={y}")

    # update the line positions
    axial_h_line.data = np.array([[y, 0], [y, axial_slice.shape[1]]])
    axial_v_line.data = np.array([[0, x], [axial_slice.shape[0], x]])

    coronal_h_line.data = np.array([[z, 0], [z, coronal_slice.shape[1]]])
    coronal_v_line.data = np.array([[0, x], [coronal_slice.shape[0], x]])

    sagittal_h_line.data = np.array([[z, 0], [z, sagittal_slice.shape[1]]])
    sagittal_v_line.data = np.array([[0, y], [sagittal_slice.shape[0], y]])

    axial_h_line.refresh()
    axial_v_line.refresh()
    coronal_h_line.refresh()
    coronal_v_line.refresh()
    sagittal_h_line.refresh()
    sagittal_v_line.refresh()
    
    # update the layer data
    axial_layer.data = axial_slice
    coronal_layer.data = coronal_slice
    sagittal_layer.data = sagittal_slice
    
    # refresh the display
    axial_layer.refresh()
    coronal_layer.refresh()
    sagittal_layer.refresh()


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
    if not recorder.is_recording:
        recorder.start_recording(viewer)
        print("start recording...")
    else:
        recorder.stop_recording()
        print("stop recording")

@viewer.bind_key('T')
def add_annotation(viewer):
    from qtpy.QtWidgets import QInputDialog, QMessageBox
    
    # create an input dialog
    text, ok = QInputDialog.getText(
        viewer.window._qt_window,
        'Add text',
        'Type in:',
    )
    
    if ok and text:
        recorder.add_annotation(text)
        print(f"Already add text: {text}")
    elif not ok:
        QMessageBox.information(
            viewer.window._qt_window,
            'Operation cancelled',
            'User cancelled the text input operation'
        )


# auto start the recording (if you want to start recording automatically, uncomment the following code)
# viewer.window._qt_window.showEvent = lambda event: recorder.start_recording(viewer)

# automatically stop recording when the window is closed
def on_close(event):
    if recorder.is_recording:
        recorder.stop_recording()
viewer.window._qt_window.closeEvent = on_close

napari.run()