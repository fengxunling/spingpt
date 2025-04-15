import whisper
from moviepy import VideoFileClip
import tempfile
import os
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

def transcribe_audio(input_audio_path, output_txt_path="transcription_en.txt"):
    # load the Whisper model
    model = whisper.load_model("medium")
    
    # perform speech recognition (directly using audio files)
    result = model.transcribe(input_audio_path, task="transcribe", language="en")
    
    # save the English subtitles
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])


def transcribe_video(input_path, output_txt_path="transcription_en.txt"):
    # extract the audio from the video
    video = VideoFileClip(input_path)
    audio = video.audio
    
    # create a temporary audio file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_path = temp_audio.name
        audio.write_audiofile(temp_path)
    
    model = whisper.load_model("base")
    result = model.transcribe(temp_path, task="transcribe", language="en")
    
    # save the English subtitles
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    
    os.remove(temp_path)
    audio.close()
    video.close()
    

if __name__ == "__main__":
    input_dir = os.path.join(os.path.dirname(__file__), 'recorded_materials')
    output_dir = input_dir 
    
    for filename in os.listdir(input_dir):
        if filename.endswith('.wav'):
            input_path = os.path.join(input_dir, filename)
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(output_dir, f"{base_name}.txt")
            
            transcribe_audio(input_path, output_path)