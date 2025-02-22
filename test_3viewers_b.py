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
image_layer = viewer.add_image(image_array, **metadata, visible=False)

from qtpy.QtWidgets import QSlider, QWidget, QVBoxLayout

# 在创建viewer后添加以下代码
slider_container = QWidget()
slider_layout = QVBoxLayout()

# Z轴滑块
z_slider = QSlider()
z_slider.setOrientation(1)  # 垂直滑块
z_slider.setMinimum(0)
z_slider.setMaximum(image_array.shape[0]-1)  # 使用第一个维度
def update_z(value):
    current_step = list(viewer.dims.current_step)
    current_step[0] = value  # 修改第一个维度
    viewer.dims.current_step = tuple(current_step)
z_slider.valueChanged.connect(update_z)

# Y轴滑块
y_slider = QSlider()
y_slider.setOrientation(1)  # 垂直滑块
y_slider.setMinimum(0)
y_slider.setMaximum(image_array.shape[1]-1)
def update_y(value):
    current_step = list(viewer.dims.current_step)
    current_step[1] = value
    viewer.dims.current_step = tuple(current_step)
y_slider.valueChanged.connect(update_y)

# X轴滑块
x_slider = QSlider()
x_slider.setOrientation(1)  # 垂直滑块
x_slider.setMinimum(0)
x_slider.setMaximum(image_array.shape[2]-1)
def update_x(value):
    current_step = list(viewer.dims.current_step)
    current_step[2] = value
    viewer.dims.current_step = tuple(current_step)
x_slider.valueChanged.connect(update_x)

# 将滑块添加到界面（按Z-Y-X顺序）
slider_layout.addWidget(z_slider)
slider_layout.addWidget(y_slider)
slider_layout.addWidget(x_slider)
slider_container.setLayout(slider_layout)
viewer.window.add_dock_widget(slider_container, name="Axis Controls")

# 同步滑块位置
def sync_sliders(event):
    z_slider.setValue(viewer.dims.current_step[0])  # 同步Z轴
    y_slider.setValue(viewer.dims.current_step[1])
    x_slider.setValue(viewer.dims.current_step[2])
viewer.dims.events.current_step.connect(sync_sliders)

# Get initial slice positions
initial_z, initial_y, initial_x = viewer.dims.current_step

# Add orthogonal 2D slice layers
axial_slice = np.rot90(image_array[initial_z, :, :], k=1)
coronal_slice = np.rot90(image_array[:, initial_y, :], k=1)
sagittal_slice = image_array[:, :, initial_x]

axial_layer = viewer.add_image(axial_slice, name='Axial')
coronal_layer = viewer.add_image(coronal_slice, name='Coronal')
sagittal_layer = viewer.add_image(sagittal_slice, name='Sagittal')
axial_layer.scale = [2.5, 2.5]  # 调整缩放因子
coronal_layer.scale = [1.5, 1.5]  # 调整缩放因子
sagittal_layer.scale = [2.5, 2.5]  # 调整缩放因子

# Set grid layout
viewer.grid.enabled = True
viewer.grid.shape = (1, 3)  # 1 row, 3 columns

# 在文件开头添加字体颜色定义
TEXT_COLOR_WHITE = 800  # 白色文字
VIEWER_TEXT_POSITION = (0, 0)     # 视图文字位置

# 在ScreenRecorder类外添加字体初始化（或类内添加）
viewer_font = ImageFont.truetype(FONT_PATH, 20) # 字体大小

def add_text_to_slice(slice_data, text):
    """在切片上添加文字标注"""
    pil_img = Image.fromarray(slice_data)
    draw = ImageDraw.Draw(pil_img)
    draw.text(VIEWER_TEXT_POSITION, 
             text,
             fill=TEXT_COLOR_WHITE, 
             font=viewer_font)
    
    # 添加白色边框
    border_width = 2
    draw.rectangle(
        [(0, 0), (pil_img.width-1, pil_img.height-1)],  # 边框范围
        outline=TEXT_COLOR_WHITE, 
        width=border_width
    )
    
    return np.array(pil_img)

def update_slices(event):
    """带旋转和文字标注的切片更新"""
    z, y, x = viewer.dims.current_step
    
    # 轴向视图（绕逆时针旋转90度）
    axial_slice = np.rot90(image_array[z, :, :], k=1)
    axial_slice = add_text_to_slice(axial_slice, f"Axial (Z={z})\nY={y}\nX={x}")
    
    # 冠状视图（保持原方向，添加转置）
    coronal_slice = np.rot90(image_array[:, y, :], k=1)
    coronal_slice = add_text_to_slice(coronal_slice, f"Coronal (Y={y})\nZ={z}\nX={x}")
    
    # 矢状视图（绕逆时针旋转90度）
    sagittal_slice = image_array[:, :, x]
    sagittal_slice = add_text_to_slice(sagittal_slice, f"Sagittal (X={x})\nZ={z}\nY={y}")

    # 更新图层数据
    axial_layer.data = axial_slice
    coronal_layer.data = coronal_slice
    sagittal_layer.data = sagittal_slice
    
    # 刷新显示
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