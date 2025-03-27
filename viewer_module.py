from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QSlider, QLineEdit, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                           QPushButton, QSizePolicy)
from qtpy.QtWidgets import QInputDialog
import numpy as np
import napari 
from napari import Viewer
from napari.layers import Image, Points
import os
from qtpy.QtWidgets import QListWidget 
from datetime import datetime 
import sounddevice as sd 
import threading 
import time
from scipy.io.wavfile import write
from utils.transcribe import transcribe_audio  
from utils.llm import generate_napari_code 
import re

class ViewerUI:
    def __init__(self, image_array, metadata, filepath, RECORD_PATH, visible_views=['sagittal', 'axial']):
        self.viewer = Viewer()
        self.image_array = image_array
        self.metadata = metadata
        self.RECORD_PATH = RECORD_PATH
        self.visible_views = visible_views
        self.translate_offset = None
        self.sagittal_base_scale = None
        self.axial_base_scale = None
        self.apply_layout_settings()
        self._init_ui(filepath)
        self._setup_layers()
        self._connect_events()
        self._init_side_panel()
        self.audio_recording = False 
        self.audio_frames = []
        

    def _init_ui(self, filepath):
        """Initialize viewer interface components"""
        self.viewer.window._qt_window.showFullScreen()
        self._create_sliders()
        self._setup_toolbar(filepath)
    
    def _init_side_panel(self):
        """Initialize right-side annotation panel"""
        self.side_panel = QWidget()
        layout = QVBoxLayout()
        
        # rectangle list
        self.rect_list = QListWidget()
        self.rect_list.itemClicked.connect(self._on_rect_selected)
        layout.addWidget(QLabel("Rectangle List"))
        layout.addWidget(self.rect_list)

        # audio button
        audio_layout = QHBoxLayout()
        self.record_btn = QPushButton("start recording")
        self.record_btn.setObjectName("audio_record_btn")  # add object name
        self.record_btn.clicked.connect(self.toggle_audio_recording)
        self.record_btn.setMinimumWidth(120)
        audio_layout.addStretch()
        audio_layout.addWidget(self.record_btn)
        audio_layout.addStretch()
        audio_layout.setContentsMargins(0, 10, 0, 10)
        layout.addLayout(audio_layout)

        # Text annotation input box
        self.annotation_edit = QLineEdit()
        self.annotation_edit.setPlaceholderText("Enter rectangle annotation...")
        self.annotation_edit.textChanged.connect(self._update_current_rect_annotation)
        layout.addWidget(QLabel("Annotation Text"))
        layout.addWidget(self.annotation_edit)

        # +++ Add AI interaction components +++
        ai_layout = QVBoxLayout()
        
        # Command input box
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Enter command (e.g.: Adjust X slice to 22)")
        ai_layout.addWidget(QLabel("AI Command:"))
        ai_layout.addWidget(self.ai_input)

        # Submit button
        self.ai_submit_btn = QPushButton("Submit Command")
        self.ai_submit_btn.setObjectName("ai_submit_btn")  # Add object name
        self.ai_submit_btn.clicked.connect(self._handle_ai_command)
        ai_layout.addWidget(self.ai_submit_btn)

        # Result display
        self.ai_response_label = QLabel("Model Response:")
        self.ai_response = QLabel()
        self.ai_response.setWordWrap(True)  # add auto wrap
        ai_layout.addWidget(self.ai_response_label)
        ai_layout.addWidget(self.ai_response)

        layout.addLayout(ai_layout)

        # Add annotation list
        self.side_panel.setLayout(layout)
        self.viewer.window.add_dock_widget(self.side_panel, name="Annotation Panel", area='right')

        # Add metadata storage
        self.rect_metadata = {}  # {rect_id: {"text": "", "audio": ""}}

    def apply_layout_settings(self):
        """Apply layout settings based on interface dimensions"""
        # Modify layout direction determination logic
        z, y, x = self.image_array.shape[:3]
        print(f'x={x}, y={y}, z={z}')
        aspect_ratio = (z + x) / y  # Determine layout based on ratio of Z+X axis total length to Y axis
        layout_setting = 'vertical' if aspect_ratio > 1.2 else 'horizontal'
        print(f'Auto layout direction: {layout_setting}')

        # Get actual Qt view rendering size
        canvas = self.viewer.window.qt_viewer.canvas.size
        window_width = canvas[1] - 200  # Reserve space for sidebar
        window_height = canvas[0] - 100  # Reserve space for toolbar
        print(f'window_width={window_width}, window_height={window_height}')

        # Calculate base scaling ratio (maintain aspect ratio)
        if layout_setting == 'vertical':
            # Vertical layout: stacked vertically, same width
            viewport_height = window_height // 2
            viewport_width = window_width
            
            # Sagittal plane scaling calculation (display X-Y plane)
            sagittal_scale_x = viewport_width / x
            sagittal_scale_y = viewport_height / z
            sagittal_scale = min(sagittal_scale_x, sagittal_scale_y)
            print(f'sagittal_scale={sagittal_scale}')
            
            # Axial plane scaling calculation (display Z-Y plane)
            axial_scale_x = viewport_width / y
            axial_scale_y = viewport_height / x
            axial_scale = min(axial_scale_x, axial_scale_y)
            print(f'axial_scale={axial_scale}')
            
            # Use minimum scaling to ensure display
            final_scale = min(sagittal_scale, axial_scale)
            print(f'final_scale={final_scale}')
            self.sagittal_base_scale = (final_scale, final_scale, final_scale)
            self.axial_base_scale = (final_scale, final_scale, final_scale)
            
            # Auto calculate offset (vertical layout)
            self.translate_offset = {
                'sagittal': (x * final_scale / 2, -y * final_scale / 2 - 100),
                'axial': (-y * final_scale / 2, -y * final_scale / 2 - 100)
            }
            
        elif layout_setting == 'horizontal':  # Horizontal layout
            # Horizontal layout: side by side, same height
            viewport_width = window_width // 2
            viewport_height = window_height
            
            # Sagittal plane scaling calculation
            sagittal_scale_x = viewport_width / x
            sagittal_scale_y = viewport_height / z
            sagittal_scale = min(sagittal_scale_x, sagittal_scale_y)
            print(f'sagittal_scale={sagittal_scale}')
            # Axial plane scaling calculation
            axial_scale_x = viewport_width / y
            axial_scale_y = viewport_height / x
            axial_scale = min(axial_scale_x, axial_scale_y)
            print(f'axial_scale={axial_scale}')
            
            final_scale = min(sagittal_scale, axial_scale)/2
            print(f'final_scale={final_scale}')
            self.sagittal_base_scale = (final_scale, final_scale, final_scale)
            self.axial_base_scale = (final_scale, final_scale, final_scale)
            
            # Horizontal layout offset calculation
            self.translate_offset = {
                'sagittal': (-x * sagittal_scale / 2, -50),
                'axial': (-x * axial_scale / 2, -100)
            }

        for view in ['sagittal', 'axial']:
            layer = getattr(self, f'{view}_layer', None)
            if layer:
                # Use 2D scaling and translation (ignore Z axis)
                layer.scale = self.sagittal_base_scale[1:] if view == 'sagittal' else self.axial_base_scale[1:]
                layer.translate = self.translate_offset[view]


        
        
    # Add annotation update method
    def _update_current_rect_annotation(self):
        """Update text annotation of currently selected rectangle"""
        print(f'==self.annotation={self.annotation_edit.text()}')
        current_rect = self.rect_list.currentRow()
        if current_rect != -1 and self.annotation_edit.text():
            print(f'annotation_edit={self.annotation_edit.text()}')
            self.rect_metadata[current_rect]["text"] = self.annotation_edit.text()
            # Update list item display
            item = self.rect_list.item(current_rect)
            # item.setText(f"Rectangle {current_rect+1} [Sagittal] - {self.annotation_edit.text()}")

    def _on_rect_selected(self, item):
        """Rectangle selection event"""
        rect_id = self.rect_list.row(item)
        self.annotation_edit.setText(self.rect_metadata.get(rect_id, {}).get("text", ""))

    def on_rect_item_clicked(self, item):
        """Handle list item double click event"""
        rect_id = self.rect_list.row(item)
        if rect_id < 0 or rect_id >= len(self.rect_metadata):
            print(f"Error: Invalid rect_id {rect_id}")
            return
            
        try:
            # Get saved slice indices
            z_index, y_index, x_index = self.rect_metadata[rect_id]["slice_indices"]
            
            # Safely switch slices
            z_index = np.clip(z_index, 0, self.image_array.shape[0]-1)
            y_index = np.clip(y_index, 0, self.image_array.shape[1]-1)
            x_index = np.clip(x_index, 0, self.image_array.shape[2]-1)
            
            # Update slice position
            self.viewer.dims.current_step = (z_index, y_index, x_index)
            # Sync slider positions
            self.z_slider.setValue(z_index)
            self.y_slider.setValue(y_index)
            self.x_slider.setValue(x_index)
        except KeyError as e:
            print(f"Metadata missing: {str(e)}")
            
        
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
        self.prev_btn.setObjectName("prev_btn")  
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("next_btn")  
        
        # Get main layout reference
        main_layout = self.slider_container.layout()
        # Insert status label and image name above sliders
        main_layout.insertWidget(0, self.status_label)  # Insert at top of layout
        main_layout.insertWidget(1, self.image_name_label)
        
        # Add navigation buttons and input field below sliders
        main_layout.addLayout(self._create_nav_buttons_layout())
        
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
        # Get initial slice positions
        initial_z, initial_y, initial_x = self.viewer.dims.current_step

        # Add orthogonal 2D slice layers
        # axial_slice = np.fliplr(np.rot90(self.image_array[initial_z, :, :], k=2))
        # coronal_slice = np.fliplr(np.rot90(self.image_array[:, initial_y, :], k=2))
        # sagittal_slice = np.fliplr(np.rot90(self.image_array[:, :, initial_x], k=2))
        axial_slice = self.image_array[initial_z, :, :]
        coronal_slice = self.image_array[:, initial_y, :]
        sagittal_slice = self.image_array[:, :, initial_x]

        # 动态设置图层参数
        if 'sagittal' in self.visible_views:
            self.sagittal_layer = self.viewer.add_image(sagittal_slice, name='Sagittal')
            self.sagittal_layer.scale = self.sagittal_base_scale[1:]  # 使用动态缩放
            self.sagittal_layer.translate = self.translate_offset['sagittal']
        
        if 'axial' in self.visible_views:
            self.axial_layer = self.viewer.add_image(axial_slice, name='Axial')
            self.axial_layer.scale = self.axial_base_scale[1:]     # 使用动态缩放
            self.axial_layer.translate = self.translate_offset['axial']

        # 设置水平布局
        self.canvas = self.viewer.window.qt_viewer.canvas
        self.canvas.layout = QHBoxLayout()

    def _connect_events(self):
        """Connect event handlers"""
        self.viewer.dims.events.current_step.connect(self._update_slices)
        self.points_layer.events.data.connect(self._on_points_changed)

    def _update_slices(self, event):
        """Slice update logic"""
        # z, y, x = viewer.dims.current_step
        z = np.clip(self.viewer.dims.current_step[0], 0, self.image_array.shape[0]-1) # add bounder check
        y = np.clip(self.viewer.dims.current_step[1], 0, self.image_array.shape[1]-1)
        x = np.clip(self.viewer.dims.current_step[2], 0, self.image_array.shape[2]-1)
        
        # # axial view (rotate 90 degrees counterclockwise)
        # axial_slice = np.fliplr(np.rot90(self.image_array[z, :, :], k=2))
        # # coronal view (rotate 180 degrees counterclockwise)
        # coronal_slice = np.fliplr(np.rot90(self.image_array[:, y, :], k=2))
        # # sagittal view
        # sagittal_slice = np.fliplr(np.rot90(self.image_array[:, :, x], k=2))

        if 'sagittal' in self.visible_views:
            sagittal_slice = np.fliplr(np.rot90(self.image_array[:, :, x], k=2))
            self.sagittal_layer.data = sagittal_slice
            print(f'sagittal_slice.shape={sagittal_slice.shape}')
        
        if 'axial' in self.visible_views:
            axial_slice = np.fliplr(np.rot90(self.image_array[z, :, :], k=2))
            self.axial_layer.data = axial_slice
            print(f'axial_slice.shape={axial_slice.shape}')
        
        # refresh the display
        self.axial_layer.refresh()  
        # self.coronal_layer.refresh()
        self.sagittal_layer.refresh()

        # according to the current slice update the visibility of the points
        if len(self.points_layer.data) > 0:
            current_z, current_y, current_x = self.viewer.dims.current_step
            visible = []
            for point in self.points_layer.data:
                p_z = int(round(point[0]))
                p_y = int(round(point[1]))
                p_x = int(round(point[2]))
                # check if on any of the current slice planes
                if p_z == current_z or p_y == current_y or p_x == current_x:
                    visible.append(True)
                else:
                    visible.append(False)
            self.points_layer.visible = visible
            self.points_layer.refresh()  # refresh the point layer display

    def _on_points_changed(self, event):
        """Points layer change handler"""
        global previous_length
        current_data = self.points_layer.data
        current_length = len(current_data)
        
        if current_length > previous_length:
            new_points = current_data[previous_length:current_length]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            current_step = viewer.dims.current_step
            spacing = image_layer.scale
            translate = image_layer.translate
            
            log_info = []
            for pt in new_points:
                physical_coord = np.array(pt) * spacing + translate
                log_entry = (
                    f"time: {timestamp}\n"
                    f"spatial coordinates: {physical_coord}\n"
                    # f"volumes coordinates: {pt}\n"
                    f"current slice: [dim0:{current_step[0]}, dim1:{current_step[1]}, dim2:{current_step[2]}]\n"
                    "------------------------\n"
                )
                log_info.append(log_entry)
                print(log_entry.strip())
            
            if recorder.is_recording:
                with open(recorder.log_path, "a") as f:
                    f.writelines(log_info)
            
            previous_length = current_length
    
    def toggle_audio_recording(self):
        """Toggle audio recording status"""
        if not self.audio_recording:
            # Start recording
            self.audio_frames = []
            self.audio_recording = True
            self.record_btn.setText("Stop Recording")
            self.fs = 44100  # Sample rate
            
            # Create recording thread
            self.audio_thread = threading.Thread(target=self._record_audio)
            self.audio_thread.start()
        else:
            # Stop recording
            self.audio_recording = False
            self.record_btn.setText("Start Recording")
            self.save_and_transcribe_audio()

    def _record_audio(self):
        """Recording thread"""
        with sd.InputStream(samplerate=self.fs, channels=1, callback=self.audio_callback):
            while self.audio_recording:
                time.sleep(0.1)

    def audio_callback(self, indata, frames, time, status):
        """Audio callback"""
        if status:
            print(status)
        self.audio_frames.append(indata.copy())

    def save_and_transcribe_audio(self):
        """Save audio and transcribe"""
        if not self.audio_frames:
            return
        
        # Concatenate audio data
        audio_data = np.concatenate(self.audio_frames, axis=0)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = os.path.join(self.RECORD_PATH, f"recording_{timestamp}.wav")
        
        # Save WAV file
        write(audio_path, self.fs, audio_data)
        
        # Call transcription function
        txt_path = audio_path.replace('.wav', '.txt')
        transcribe_audio(audio_path, txt_path)
        
        # Load result to text box
        with open(txt_path, 'r', encoding='utf-8') as f:
            self.annotation_edit.setText(f.read())

    def _handle_ai_command(self):
        """Handle AI commands"""
        command = self.ai_input.text()
        if not command:
            return
        
        try:
            # Get new dictionary format result
            result = generate_napari_code(command)
            
            if result['type'] == 'slice_adjustment':
                # Handle slice adjustment
                number = result['number']
                axis = result['axis']
                self.ai_response.setText(f"Slice position: {number}, Axis: {axis.upper()}")
                
                # Set slider based on axis
                if axis == 'x':
                    self.x_slider.setValue(number)
                elif axis == 'y':
                    self.y_slider.setValue(number)
                elif axis == 'z':
                    self.z_slider.setValue(number)
                    
            elif result['type'] == 'general_response':
                # Display complete model response
                self.ai_response.setText(f"Model response:\n{result['content']}")
                
            elif result['type'] == 'error':
                self.ai_response.setText(f"Error: {result['message']}")
                
        except KeyError as e:
            self.ai_response.setText(f"Response format error: Missing key field {str(e)}")
        except Exception as e:
            self.ai_response.setText(f"Command processing failed: {str(e)}")
        

    def get_viewer(self):
        return self.viewer

    def get_points_layer(self):
        return self.points_layer
    
    def get_status_label(self):
        return self.status_label

    def count_polygons(self):
        """Count polygons and rectangle annotations"""
        polygons = []
        print(f'metadata={self.rect_metadata}')
        # Add rectangle annotation processing
        for layer in self.viewer.layers:
            if isinstance(layer, napari.layers.Shapes):
                for i, shape in enumerate(layer.data):
                    # Process rectangle annotations
                    if layer.shape_type == 'rectangle':
                        rect_id = len(self.rect_metadata)  # Get current rectangle ID
                        item_text = f"Rectangle {rect_id+1} [{layer.name}] - Annotation: {self.rect_metadata.get(rect_id,{}).get('text','')}"
                        polygons.append({
                            "layer": "Rectangle Annotation",
                            "coordinates": shape,
                            "text": self.rect_metadata.get(rect_id,{}).get('text','')
                        })
            if isinstance(layer, napari.layers.Shapes) and layer.ndim == 2:
                for shape in layer.data:
                    # Check if it's a polygon with at least 3 vertices
                    if len(shape) >= 3:
                        # print('=is polygen')
                        # Convert coordinates (considering layer scaling and translation) TODO: This coordinate system calculation is questionable
                        scaled_coords = [
                            (coord * layer.scale + layer.translate).tolist()
                            for coord in shape
                        ]
                        polygons.append({
                            "layer": layer.name,
                            "coordinates": scaled_coords
                        })
        
        return len(polygons), polygons