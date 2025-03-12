# Multi-View Screen Recording System (for NIFTI files)

![Main Viewer](assets/main_viewer.png)

## Project Overview
A Python-based multi-view screen recording system that supports simultaneous monitoring and recording of .nifti files.
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
<video controls width="100%">
  <source src="assets/demo.mp4" type="video/mp4">
</video>

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