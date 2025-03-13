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


import sounddevice as sd 
from scipy.io.wavfile import write as write_wav

import cv2

# set the parameters
RECORD_PATH = os.path.dirname(__file__)+'/recorded_materials/'  # recording file path
VIDEO_PATH = RECORD_PATH+"operation_recording.mp4"  # video file path
FPS = 15  # frames per second
RECORD_REGION = None  # set the recording region to default

class ScreenRecorder:
    def __init__(self):
        self.is_recording = False
        self.writer = None
        self.monitor = None
        self.capture_thread = None
        self.audio_thread = None
        self.audio_frames = []
        self.fs = 44100  # sampling rate for the audio
        self.audio_filename = None

        self.start_time = None
        self.end_time = None
        self.text_queue = queue.Queue()  # (thread-safe text queue)
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
            with open(self.log_path, "a") as f:
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
        # win = viewer.window._qt_window
        # win.moveEvent = lambda event: self._update_region(win)  # update the region when the window moves
        # self._update_region(win)
        win = viewer.window._qt_window
        time.sleep(0.5)  # 添加延迟确保窗口完成布局
        self._update_region(win)
        win.moveEvent = lambda event: self._update_region(win)
        
        # intialize the video writer
        self.writer = get_writer(self.video_path, format='FFMPEG', fps=FPS)
        
        # start the screen capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.start()

        # initialize the audio recording
        self.audio_filename = os.path.join(RECORD_PATH, f"{base_name}_temp.wav")
        self.audio_frames = []
        self.audio_thread = threading.Thread(target=self._record_audio)
        self.audio_thread.start()

    def _record_audio(self):
        """audio recording thread"""
        try:
            with sd.InputStream(samplerate=self.fs, channels=2, callback=self._audio_callback):
                while self.is_recording:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Audio recording error: {str(e)}")

    def _audio_callback(self, indata, frames, time, status):
        """audio callback function"""
        if status:
            print(status)
        self.audio_frames.append(indata.copy())


    def _update_region(self, window):
        # update the napari window coordinates
        # geo = window.geometry()
        geo = window.frameGeometry() 
        self.monitor = {
            "left": geo.x(),
            "top": geo.y(),
            "width": geo.width()+1300,
            "height": geo.height()+900
        }

    def _capture_loop(self):
        # get the screen capture object
        with mss() as sct:
            while self.is_recording:
                try:
                    # capture the screen region
                    img = np.array(sct.grab(self.monitor))
                    # transfrom to RGB format
                    img = cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2RGB)

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
        with open(self.log_path, "a") as f:
            f.write(
                f"[Video Recording Ended] {timestamp_end}\n"
                f"[Duration] {duration.total_seconds():.2f} seconds\n\n"
            )

        if self.capture_thread:
            self.capture_thread.join()
        if self.writer:
            self.writer.close()
        print(f"The video is saved at: {os.path.abspath(VIDEO_PATH)}")

        # stop audio recording and save
        if self.audio_thread:
            self.audio_thread.join()
            if self.audio_frames:
                audio_data = np.concatenate(self.audio_frames)
                write_wav(self.audio_filename, self.fs, audio_data)


# initialize the screen recorder
recorder = ScreenRecorder()

# set the file path
IMAGE_LIST = [
    "D:/projects/spingpt/data/T2G003_Spine_NIFTI/Dicoms_Spine_MRI_t2_space_sag_p2_iso_2050122160508_5001.nii.gz",
    "D:/projects/spingpt/data/T2G002_MRI_Spine_Nifti/T2G002_MRI_Spine_t2_gre_sag_sergio_mat384_TR428_06x06_5min47_20240820161941_4001.nii.gz"
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
slider_container.setMinimumWidth(300)  # 设置最小宽度
slider_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 允许水平扩展
main_layout = QVBoxLayout()
main_layout.setContentsMargins(10, 5, 10, 5)  # 添加布局边距
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
image_name_label.setWordWrap(True)  # 新增自动换行功能
image_name_label.setStyleSheet("QLabel { margin: 5px 20px; }")  # 添加边距
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
# axial_slice = image_array[initial_z, :, :]
# coronal_slice = image_array[:, initial_y, :]
# sagittal_slice = image_array[:, :, initial_x]
print('axial_slice:', axial_slice.shape)
print('coronal_slice:', coronal_slice.shape)
print('sagittal_slice:', sagittal_slice.shape)
sagittal_layer = viewer.add_image(sagittal_slice, name='Sagittal')
axial_layer = viewer.add_image(axial_slice, name='Axial')
# coronal_layer = viewer.add_image(coronal_slice, name='Coronal', visible=False)

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
sagittal_layer = viewer.layers['Sagittal'] 
sagittal_layer.translate = (-50, -100)  
sagittal_layer.scale = [0.3, 0.3] 

axial_layer = viewer.layers['Axial'] # get the target layer
axial_layer.translate = (-20, -60)  # move the layer to the specified position
axial_layer.scale = [0.4, 0.4] 
# coronal_layer = viewer.layers['Coronal'] 
# coronal_layer.translate = (-110, 90) 
# coronal_layer.scale = [0.4, 0.4] 
# viewer.grid.enabled = True
# viewer.grid.stride = 2  


def update_slices(event):
    """Update the slices with rotation and text annotation"""
    # z, y, x = viewer.dims.current_step
    z = np.clip(viewer.dims.current_step[0], 0, image_array.shape[0]-1) # add bounder check
    y = np.clip(viewer.dims.current_step[1], 0, image_array.shape[1]-1)
    x = np.clip(viewer.dims.current_step[2], 0, image_array.shape[2]-1)
    
    # axial view (rotate 90 degrees counterclockwise)
    axial_slice = np.fliplr(np.rot90(image_array[z, :, :], k=2))
    # axial_slice = image_array[z, :, :]
    
    # coronal view (rotate 180 degrees counterclockwise)
    # coronal_slice = np.fliplr(np.rot90(image_array[:, y, :], k=2))
    
    # sagittal view
    sagittal_slice = np.fliplr(np.rot90(image_array[:, :, x], k=2))
    # sagittal_slice = image_array[:, :, x]
    
    # update the layer data
    axial_layer.data = axial_slice
    # coronal_layer.data = coronal_slice
    sagittal_layer.data = sagittal_slice
    
    # refresh the display
    axial_layer.refresh()
    # coronal_layer.refresh()
    sagittal_layer.refresh()

    # according to the current slice update the visibility of the points
    if len(points_layer.data) > 0:
        current_z, current_y, current_x = viewer.dims.current_step
        visibility = []
        for point in points_layer.data:
            p_z = int(round(point[0]))
            p_y = int(round(point[1]))
            p_x = int(round(point[2]))
            # 检查是否在当前切片平面
            if p_z == current_z or p_y == current_y or p_x == current_x:
                visibility.append(True)
            else:
                visibility.append(False)
        
        # 使用正确的属性名设置可见性（确保使用布尔值列表）
        points_layer.shown = visibility  # 替换原来的visible属性
        points_layer.refresh()


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

