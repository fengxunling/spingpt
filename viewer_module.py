import numpy as np
from qtpy.QtWidgets import QSlider, QWidget, QVBoxLayout, QLabel
from qtpy.QtCore import Qt

def create_slider_controls(viewer, image_array):
    slider_container = QWidget()
    slider_container.setMinimumWidth(300)  # set minimum width
    slider_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # allow horizontal expansion
    slider_layout = QVBoxLayout()

    x_container = QWidget()
    x_layout = QVBoxLayout()
    x_slider = QSlider()
    x_slider.setOrientation(1)
    x_slider.setMinimum(0)
    x_slider.setMaximum(image_array.shape[2]-1)
    x_slider.setValue(image_array.shape[2] // 2)
    max_x = image_array.shape[2]-1
    x_label = QLabel(f"X: {x_slider.value()}/{max_x}")
    def update_x(value):
        current_step = list(viewer.dims.current_step)
        current_step[2] = value
        viewer.dims.current_step = tuple(current_step)
        x_label.setText(f"X: {value}/{max_x}")
    x_slider.valueChanged.connect(update_x)
    x_layout.addWidget(x_slider)
    x_layout.addWidget(x_label)
    x_container.setLayout(x_layout)

    y_container = QWidget()
    y_layout = QVBoxLayout()
    y_slider = QSlider()
    y_slider.setOrientation(1)
    y_slider.setMinimum(0)
    y_slider.setMaximum(image_array.shape[1]-1)
    y_slider.setValue(image_array.shape[1] // 2)
    max_y = image_array.shape[1]-1  
    y_label = QLabel(f"Y: {y_slider.value()}/{max_y}")
    def update_y(value):
        current_step = list(viewer.dims.current_step)
        current_step[1] = value
        viewer.dims.current_step = tuple(current_step)
        y_label.setText(f"Y: {value}/{max_y}") 
    y_slider.valueChanged.connect(update_y)
    y_layout.addWidget(y_slider)
    y_layout.addWidget(y_label)
    y_container.setLayout(y_layout)

    z_container = QWidget()
    z_layout = QVBoxLayout()
    z_slider = QSlider()
    z_slider.setOrientation(1)
    z_slider.setMinimum(0)
    z_slider.setMaximum(image_array.shape[0]-1)
    z_slider.setValue(image_array.shape[0] // 2)
    max_z = image_array.shape[0]-1 
    z_label = QLabel(f"Z: {z_slider.value()}/{max_z}")
    def update_z(value):
        current_step = list(viewer.dims.current_step)
        current_step[0] = value
        viewer.dims.current_step = tuple(current_step)
        z_label.setText(f"Z: {value}/{max_z}")
    z_slider.valueChanged.connect(update_z)
    z_layout.addWidget(z_slider)
    z_layout.addWidget(z_label)
    z_container.setLayout(z_layout)

    slider_layout.addWidget(x_container) 
    slider_layout.addWidget(y_container)
    slider_layout.addWidget(z_container)

    return slider_container

def setup_viewer_ui(viewer, image_array):
    # 设置UI布局相关代码
    slider_container = create_slider_controls(viewer, image_array)
    
    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(10, 5, 10, 5)  # add margin
    
    # create the recording mode annotation
    status_label = QLabel("Recording status: Not recording")
    status_label.setStyleSheet("color: green;")  
    status_label.setAlignment(Qt.AlignCenter)
    image_name_label = QLabel("Current Image: ")
    image_name_label.setAlignment(Qt.AlignCenter)
    image_name_label.setWordWrap(True)  # add auto wrap
    image_name_label.setStyleSheet("QLabel { margin: 5px 20px; }")  # add margin
    main_layout.addWidget(status_label)
    main_layout.addWidget(image_name_label)

    # create button for loading images
    nav_buttons_layout = QHBoxLayout()
    prev_btn = QPushButton("Previous")
    prev_btn.setObjectName("nav_prev_btn") 
    next_btn = QPushButton("Next")
    next_btn.setObjectName("nav_next_btn") 
    nav_buttons_layout.addWidget(prev_btn)
    nav_buttons_layout.addWidget(next_btn)

    prev_btn.clicked.connect(prev_image)
    next_btn.clicked.connect(next_image)

    return slider_container
