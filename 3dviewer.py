import os
import sys
sys.path.append(os.path.dirname(__file__)+'/napari-nifti/src/')
print(os.path.dirname(__file__)+'/../')

import threading
import time
from datetime import datetime
import numpy as np
from imageio import get_writer
from mss import mss  # cross-platform screen capture library
from napari_nifti._reader import napari_get_reader
import napari
from napari import Viewer

# set the parameters
VIDEO_PATH = "operation_recording.mp4"  # video file path
FPS = 15  # frames per second
RECORD_REGION = None  # set the recording region to default

class ScreenRecorder:
    def __init__(self):
        self.is_recording = False
        self.writer = None
        self.monitor = None
        self.capture_thread = None

    def start_recording(self, viewer):
        # auto detect the recording region and start recording
        self.is_recording = True
        
        # get the napari window coordinates
        win = viewer.window._qt_window
        win.moveEvent = lambda event: self._update_region(win)  # update the region when the window moves
        self._update_region(win)
        
        # intialize the video writer
        self.writer = get_writer(VIDEO_PATH, format='FFMPEG', fps=FPS)
        
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
                    # write the video frame
                    self.writer.append_data(img)
                    time.sleep(1/FPS)
                except Exception as e:
                    print(f"capture error: {str(e)}")
                    break

    def stop_recording(self):
        # stop the recording
        self.is_recording = False
        if self.capture_thread:
            self.capture_thread.join()
        if self.writer:
            self.writer.close()
        print(f"The video is saved at: {os.path.abspath(VIDEO_PATH)}")

# initialize the screen recorder
recorder = ScreenRecorder()

# set the file path
filepath = "D:/projects/spingpt/data/Dicom_t2_trufi3d_cor_0.6_20230123141752_3.nii/Dicom_t2_trufi3d_cor_0.6_20230123141752_3.nii"
print("The file exist:", os.path.exists(filepath))

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

# create Viewer
viewer = Viewer()
image_layer = viewer.add_image(image_array, **metadata)

# add 3D points layer
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
                f"volumes coordinates: {pt}\n"
                f"current slice: [dim0:{current_step[0]}, dim1:{current_step[1]}, dim2:{current_step[2]}]\n"
                "------------------------\n"
            )
            log_info.append(log_entry)
            print(log_entry.strip())
        
        with open("3d_points_log.txt", "a") as f:
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

# auto start the recording (if you want to start recording automatically, uncomment the following code)
# viewer.window._qt_window.showEvent = lambda event: recorder.start_recording(viewer)

# automatically stop recording when the window is closed
def on_close(event):
    if recorder.is_recording:
        recorder.stop_recording()
viewer.window._qt_window.closeEvent = on_close

napari.run()