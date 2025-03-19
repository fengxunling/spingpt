from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QSlider, QLineEdit, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                           QPushButton, QSizePolicy)
import numpy as np
import napari
from napari import Viewer
from napari.layers import Image, Points
import os

class ViewerUI:
    def __init__(self, image_array, metadata, filepath):
        self.viewer = Viewer()
        self.image_array = image_array
        self.metadata = metadata
        self._init_ui(filepath)
        self._setup_layers()
        self._connect_events()

    def _init_ui(self, filepath):
        """Initialize viewer interface components"""
        self.viewer.window._qt_window.showFullScreen()
        self._create_sliders()
        self._setup_toolbar(filepath)
        
    def _create_sliders(self):
        self.slider_container = QWidget()
        self.slider_container.setMinimumWidth(300)
        self.slider_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Create main layout and slider layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 5, 10, 5)  # Keep the margin settings from original tmp.py
        slider_layout = QVBoxLayout()
        # Create and add three axis sliders
        slider_layout.addWidget(self._create_axis_slider('x', 2))  # Add X-axis slider container
        slider_layout.addWidget(self._create_axis_slider('y', 1))  # Add Y-axis slider container
        slider_layout.addWidget(self._create_axis_slider('z', 0))  # Add Z-axis slider container
        
        # Add slider layout to main layout
        main_layout.addLayout(slider_layout)  # This is the key layout structure from original tmp.py
        self.slider_container.setLayout(main_layout)  # Set container layout

        # Set stylesheet
        self.slider_container.setStyleSheet("""
            QWidget { alignment: left; margin-left: 5px; }
            QSlider { min-width: 120px; }
        """)

    def _create_axis_slider(self, axis, dim_index):
        """Create a single axis slider (refactored generic method)"""
        container = QWidget()
        layout = QVBoxLayout()
        slider = QSlider()
        slider.setOrientation(1)
        
        # Set slider range (X/Y/Z slider setting logic from original tmp.py)
        max_value = self.image_array.shape[dim_index] - 1
        slider.setRange(0, max_value)
        slider.setValue(max_value // 2)
        
        # Create label and update function
        label = QLabel(f"{axis.upper()}: {slider.value()}/{max_value}")
        def update_value(value):
            current_step = list(self.viewer.dims.current_step)
            current_step[dim_index] = value
            self.viewer.dims.current_step = tuple(current_step)
            label.setText(f"{axis.upper()}: {value}/{max_value}")
        
        slider.valueChanged.connect(update_value)
        layout.addWidget(slider)
        layout.addWidget(label)
        container.setLayout(layout)
        
        # Save references
        setattr(self, f'{axis}_slider', slider)
        setattr(self, f'{axis}_label', label)
        return container

    def _setup_toolbar(self, filepath):
        # Status label and image name label
        self.status_label = QLabel("Recording status: Not recording")
        self.image_name_label = QLabel(f"Current Image: {os.path.basename(filepath)}")
        
        # Navigation buttons (prev_btn/next_btn logic from original tmp.py)
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        
        # Input field and submit button (input_layout logic from original tmp.py)
        self.annotation_input = QLineEdit()
        self.submit_btn = QPushButton("Submit")
        
        # Get main layout reference
        main_layout = self.slider_container.layout()
        # Insert status label and image name above sliders
        main_layout.insertWidget(0, self.status_label)  # Insert at top of layout
        main_layout.insertWidget(1, self.image_name_label)
        
        # Add navigation buttons and input field below sliders
        main_layout.addLayout(self._create_nav_buttons_layout())
        main_layout.addLayout(self._create_input_layout())
        
        
        # Add dock widget (original axis_controls_dock logic)
        self.viewer.window.add_dock_widget(
            self.slider_container,
            name="Axis Controls",
            area='left',
            allowed_areas=['left', 'right']
        )

    def _create_nav_buttons_layout(self):
        """Create navigation buttons layout"""
        layout = QHBoxLayout()
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        return layout

    def _create_input_layout(self):
        """Create input field layout"""
        layout = QHBoxLayout()
        layout.addWidget(self.annotation_input)
        layout.addWidget(self.submit_btn)
        return layout

    def _setup_layers(self):
        """Initialize image and points layers"""
        self.image_layer = self.viewer.add_image(self.image_array, **self.metadata, visible=False)
        self._setup_ortho_views()
        self.points_layer = self.viewer.add_points(
            name='3d corresponding points',
            ndim=3,
            size=3,
            face_color='red'
        )

    def _setup_ortho_views(self):
        """Initialize orthogonal views"""
        # [保留原有tmp.py中创建正交视图层的完整代码]

    def _connect_events(self):
        """Connect event handlers"""
        self.viewer.dims.events.current_step.connect(self._update_slices)
        self.points_layer.events.data.connect(self._on_points_changed)

    def _update_slices(self, event):
        """Slice update logic"""
        # [保留原有tmp.py中update_slices的完整代码]

    def _on_points_changed(self, event):
        """Points layer change handler"""
        # [保留原有tmp.py中on_points_changed的完整代码]

    def get_viewer(self):
        return self.viewer

    def get_points_layer(self):
        return self.points_layer
    
    def get_status_label(self):
        return self.status_label