# Multi-View Screen Recording System (for NIFTI files)


## Project Overview
A Python-based multi-view screen recording system that supports simultaneous monitoring and recording of .nifti files.

### Basic functions:
This is the main view of the interface. It loads the image and displays the axial and sagittal viewers. You can drag or scroll up/down to control the X, Y, and Z index slices.

Parameters like opacity and contrast can be changed. Additionally, the image can be zoomed in or out using the mouse scroll wheel.
[basic_function.mp4](https://github.com/user-attachments/assets/bc0b26df-d9d9-4a8d-955e-bdac06bd2aaa)

### Quick change between different image files
Now, a batch of files can be preloaded, allowing the user to select freely the file to display.
[select files.mp4](https://github.com/user-attachments/assets/17906a83-e6a5-45a8-aac8-6140d42a9ad1)


### Rectangle (Polygon) annotation mode on sagittal viewer
1. The user can resize the annotation and adjust its vertices:
[add rectangle annotation.mp4](https://github.com/user-attachments/assets/be7fa3f6-d483-40df-b2b2-1d84eacc1084)

2. The user can add annotations to this rectangle or polygon either by writing or speaking. Notably, if you press the button to start speaking, the audio will be recorded, transcribed into English text, and updated in the annotation:
[edit annotation.mp4](https://github.com/user-attachments/assets/f9dc0992-dbd1-437c-8916-c60647402d4b)
3. If the user change the slice index, double-clicking the rectangle annotation will activate it and return to the specific layer corresponding to the annotation.
[activate annotation.mp4](https://github.com/user-attachments/assets/f418c60e-48f1-49cf-bd2a-e3c29aae5ba6)

### On testing mode: AI response
I used Ollama to deploy a test version of the `deepseek-r1:7b` model locally on my computer.

Now, the user can interact with it through the text.

1. **For pre-coded instructions**: Currently, it supports commands like changing the slice index. (So far, this is the only type I’ve implemented, but in the future, maybe we could add other pre-coded commands, such as removing artifacts or enhancing images?)
[ai command-1.mp4](https://github.com/user-attachments/assets/c35e6203-3c80-4322-b516-aa41eb660b91)
2. **For general chat:** 
[ai command-1.mp4](https://github.com/user-attachments/assets/4e65143c-7e46-43ad-b172-29db5f7632f1)

## Quick Start
1. Set up the environment.
```bash
conda env create -f environment.yml
```
2. Run the environment.
```bash
conda activate <name of your environment>
```

3. cd to the project and run the python file.
```bash
python navigate_gui.py
```

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