import whisper
from moviepy import VideoFileClip
import tempfile
import os
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

def transcribe_audio(input_audio_path, output_txt_path="transcription_en.txt"):
    # load the Whisper model
    model = whisper.load_model("base")
    
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
    file_path = os.path.dirname(__file__)+'/record_materials/'
    transcribe_audio("test.wav", "output_audio.txt")