import whisper
from moviepy import VideoFileClip
import tempfile
import os
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

def transcribe_audio(input_audio_path, output_txt_path="transcription_en.txt"):
    # 加载Whisper模型
    model = whisper.load_model("base")
    
    # 进行语音识别（直接使用音频文件）
    result = model.transcribe(input_audio_path, task="transcribe", language="en")
    
    # 保存英文字幕
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])


def transcribe_video(input_path, output_txt_path="transcription_en.txt"):
    # 提取视频中的音频
    video = VideoFileClip(input_path)
    audio = video.audio
    
    # 创建临时音频文件
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_path = temp_audio.name
        audio.write_audiofile(temp_path)
    
    # 加载Whisper模型
    model = whisper.load_model("base")
    
    # 进行语音识别
    result = model.transcribe(temp_path, task="transcribe", language="en")
    
    # 保存英文字幕
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    
    # 清理临时文件
    os.remove(temp_path)
    audio.close()
    video.close()
    

# 使用示例
if __name__ == "__main__":
    file_path = os.path.dirname(__file__)+'/record_materials/'
    transcribe_audio("test.wav", "output_audio.txt")