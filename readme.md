# Multi-View Screen Recording System (for NIFTI files)


## Project Overview
A Python-based multi-view screen recording system that supports simultaneous monitoring and recording of .nifti files.

### Basic functions:
This is the main view of the interface. It loads the image and displays the axial and sagittal viewers. You can drag or scroll up/down to control the X, Y, and Z index slices.

Parameters like opacity and contrast can be changed. Additionally, the image can be zoomed in or out using the mouse scroll wheel.
<video controls width="80%">
  <source src="assets/basic_functions.mp4" type="video/mp4">
</video>
![Main Viewer](assets/main_viewer.png)
After pressing the 'M' key, the recording tool starts working. The full screen will be recorded, along with the audio. Additionally, all operations will be logged in a file named **log.txt**, formatted as follows:
![[Pasted image 20250327161234.png]]
The audio can also be transcribed into English and saved in the same folder (referred to as 'temp' here).
![[Pasted image 20250327161457.png]]
### New feature1: Rectangle (Polygon) annotation on sagittal viewer
1. The user can resize the annotation and adjust its vertices:
![[add rectangle annotation.mp4]]
2. The user can add annotations to this rectangle or polygon either by writing or speaking. Notably, if you press the button to start speaking, the audio will be recorded, transcribed into English text, and updated in the annotation:
![[edit annotation.mp4]]
3. If the user change the slice index, double-clicking the rectangle annotation will activate it and return to the specific layer corresponding to the annotation.
![[activate annotation.mp4]]
### New feature2: Quick change between different image files
Previously, the interface could only load one image at a time, and to switch to a different image file, I had to manually change the path in the code.

Now, a batch of files can be preloaded, allowing the user to switch between them using the 'Next' and 'Previous' buttons. The current filename is displayed on the interface.

I’ve noticed that many files have completely different image shapes, which makes it a bit tricky to ensure each image auto-scales and fits optimally in the viewer. However, I will look into improving this.
### New features3: AI response
I used Ollama to deploy a test version of the `deepseek-r1:7b` model locally on my computer.

Now, the user can interact with it through the text.

1. **For pre-coded instructions**: Currently, it supports commands like changing the slice index. (So far, this is the only type I’ve implemented, but in the future, maybe we could add other pre-coded commands, such as removing artifacts or enhancing images?)
![[ai command-1.mp4]]
2. **For general chat:** 

## Quick Start
1. Set up the environment.
```bash
conda env create -f environment.yml
```
2. Run the environment.
```bash
conda activate spinGPT
```

3. cd to the project and run the python file.
```bash
python 3viewers_screen_recording_new.py
```
## Operation Demo
</video>
https://github.com/user-attachments/assets/258d57bf-af5a-4323-929d-e351842611ad

## Project Structure
```
spingpt/
├── assets/                           # Resource files
├── literatures/                      # Some references    
├── data/
├── recorded_materials/               # Output recordings
├── utils/                            # Utility functions
├── test/                             # Test files
├── readme.md                         # Project documentation
├── environment.yml                   # Conda environment configuration
├── 3dviwer.py                        # 3-D viewer of the .nifti file
└── 3viewers_screen_recording_new.py  # 3viwer(sagittal, coronal, axial) screen recording file
```