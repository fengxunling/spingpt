import time
import threading
import numpy as np
import sounddevice as sd
import pyautogui
import cv2
from pynput import keyboard, mouse
import pandas as pd

class ActivityRecorder:
    def __init__(self):
        self.operations = []
        self.recording = False
        self.start_time = None

    def start_recording(self):
        self.recording = True
        self.start_time = time.time()
        
        # Start keyboard and mouse listeners
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.mouse_listener = mouse.Listener(on_click=self.on_mouse_click)
        self.keyboard_listener.start()
        self.mouse_listener.start()
        
        # Start screen recording thread
        self.screen_thread = threading.Thread(target=self.record_screen)
        self.screen_thread.start()
        
        # Start audio recording
        self.audio_recording = []
        self.audio_stream = sd.InputStream(
            callback=self.audio_callback, 
            channels=2, 
            samplerate=44100
        )
        self.audio_stream.start()

    def stop_recording(self):
        self.recording = False
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        self.screen_thread.join()
        self.audio_stream.stop()
        
        # Save data
        self.save_data()

    def on_key_press(self, key):
        self.operations.append({
            'type': 'keyboard',
            'action': 'press',
            'key': str(key),
            'timestamp': time.time() - self.start_time
        })

    def on_mouse_click(self, x, y, button, pressed):
        self.operations.append({
            'type': 'mouse',
            'action': 'click' if pressed else 'release',
            'button': str(button),
            'x': x,
            'y': y,
            'timestamp': time.time() - self.start_time
        })

    def record_screen(self):
        screen_size = pyautogui.size()
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        out = cv2.VideoWriter(f'screen_{timestamp}.avi', fourcc, 10.0, screen_size)
        while self.recording:
            img = pyautogui.screenshot()
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(frame)
        out.release()

    def audio_callback(self, indata, frames, time, status):
        self.audio_recording.append(indata.copy())

    def save_data(self):
        # save operations
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        pd.DataFrame(self.operations).to_csv(f'operations_{timestamp}.csv', index=False)
        # save audio
        audio_data = np.concatenate(self.audio_recording, axis=0)
        sd.write('audio.wav', audio_data, 44100)

recorder = ActivityRecorder()
recorder.start_recording()
input("Press Enter to stop recording...")
recorder.stop_recording()
