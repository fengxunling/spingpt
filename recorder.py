import os
import threading 
import time
from datetime import datetime
import numpy as np
from imageio import get_writer
from mss import mss
import queue
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
import cv2
from PIL import Image, ImageDraw, ImageFont

class ScreenRecorder:
    def __init__(self, FONT_PATH, FONT_SIZE, RECORD_PATH, FPS, MAX_TEXT_DURATION):
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
        self.font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        self.lock = threading.Lock()
        self.text_color = 255

        # add dynamic path for the image and video
        self.image_name = None
        self.video_path = None
        self.log_path = None

        self.RECORD_PATH = RECORD_PATH
        self.FPS = FPS
        self.MAX_TEXT_DURATION = MAX_TEXT_DURATION
    
    def add_annotation(self, text):
        """Add text annotation"""
        try:
            timestamp = datetime.now()
            with self.lock:
                self.text_queue.put({
                    "text": text,
                    "timestamp": timestamp,
                    "expire_time": timestamp.timestamp() + self.MAX_TEXT_DURATION  
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
        except Exception as e:
            print(f"Annotation error: {str(e)}")
        
    
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
                draw.text((0, 0), 
                         f"{annotation['text']} ({annotation['timestamp'].strftime('%H:%M:%S')})",
                         fill=self.text_color, 
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
        self.video_path = os.path.join(self.RECORD_PATH, f"{base_name}.mp4")
        self.log_path = os.path.join(self.RECORD_PATH, f"{base_name}_log.txt")

        # write the start time to the log
        timestamp_start = self.start_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.log_path, "a") as f:
            f.write(f"\n[Video Recording Started] {timestamp_start}\n")
        
        win = viewer.window._qt_window
        time.sleep(0.5)  # add delay
        self._update_region(win)
        win.moveEvent = lambda event: self._update_region(win)
        
        # intialize the video writer
        self.writer = get_writer(self.video_path, format='FFMPEG', fps=self.FPS)
        
        # start the screen capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.start()

        # # initialize the audio recording
        # self.audio_filename = os.path.join(self.RECORD_PATH, f"{base_name}_temp.wav")
        # self.audio_frames = []
        # self.audio_thread = threading.Thread(target=self._record_audio)
        # self.audio_thread.start()

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
            # "width": geo.width(),
            # "height": geo.height()
            "width": geo.width()+1300,
            "height": geo.height()+900
        }

    def _capture_loop(self):
        with mss() as sct:
            last_capture_time = time.perf_counter()
            while self.is_recording:
                try:
                    elapsed = time.perf_counter() - last_capture_time
                    sleep_time = max(0, (1/self.FPS) - elapsed)
                    time.sleep(sleep_time)
                    
                    last_capture_time = time.perf_counter()
                    
                    # 优化图像捕获流程
                    img = np.array(sct.grab(self.monitor))
                    img = cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2RGB)
                    
                    # 分离文字绘制到独立线程
                    if not self.text_queue.empty():
                        img = self._draw_text(img)
                    
                    # 使用线程锁写入视频
                    with threading.Lock():
                        self.writer.append_data(img)

                except Exception as e:
                    print(f"capture error: {str(e)}")
                    continue

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
        print(f"The video is saved at: {os.path.abspath(self.video_path)}")

        # # stop audio recording and save
        # if self.audio_thread:
        #     self.audio_thread.join()
        #     if self.audio_frames:
        #         audio_data = np.concatenate(self.audio_frames)
        #         write_wav(self.audio_filename, self.fs, audio_data) 