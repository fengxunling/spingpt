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
        """迁移原tmp.py中滑块控件的完整创建逻辑"""
        self.slider_container = QWidget()
        self.slider_container.setMinimumWidth(300)
        self.slider_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 创建主布局和滑块布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 5, 10, 5)  # 需要保留原tmp.py的边距设置
        slider_layout = QVBoxLayout()
        # 创建并添加三个轴向滑块 
        slider_layout.addWidget(self._create_axis_slider('x', 2))  # 添加X轴滑块容器
        slider_layout.addWidget(self._create_axis_slider('y', 1))  # 添加Y轴滑块容器
        slider_layout.addWidget(self._create_axis_slider('z', 0))  # 添加Z轴滑块容器
        
        # 将滑块布局加入主布局
        main_layout.addLayout(slider_layout)  # 这是原tmp.py中的关键布局结构
        self.slider_container.setLayout(main_layout)  # 设置容器布局

        # 设置样式表
        self.slider_container.setStyleSheet("""
            QWidget { alignment: left; margin-left: 5px; }
            QSlider { min-width: 120px; }
        """)

    def _create_axis_slider(self, axis, dim_index):
        """创建单个轴向的滑块（重构后的通用方法）"""
        container = QWidget()
        layout = QVBoxLayout()
        slider = QSlider()
        slider.setOrientation(1)
        
        # 设置滑块范围（原tmp.py中X/Y/Z滑块设置逻辑）
        max_value = self.image_array.shape[dim_index] - 1
        slider.setRange(0, max_value)
        slider.setValue(max_value // 2)
        
        # 创建标签和更新函数
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
        
        # 保存引用
        setattr(self, f'{axis}_slider', slider)
        setattr(self, f'{axis}_label', label)
        return container

    def _setup_toolbar(self, filepath):
        """迁移原tmp.py中工具栏相关逻辑"""
        # 状态标签和图像名称标签
        self.status_label = QLabel("Recording status: Not recording")
        self.image_name_label = QLabel(f"Current Image: {os.path.basename(filepath)}")
        
        # 导航按钮（原tmp.py中prev_btn/next_btn逻辑）
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        
        # 输入框和提交按钮（原tmp.py中input_layout逻辑）
        self.annotation_input = QLineEdit()
        self.submit_btn = QPushButton("Submit")
        
        # 获取主布局引用
        main_layout = self.slider_container.layout()
        # 在滑块上方插入状态标签和图片名称
        main_layout.insertWidget(0, self.status_label)  # 插入到布局顶部
        main_layout.insertWidget(1, self.image_name_label)
        
        # 在滑块下方添加导航按钮和输入框
        main_layout.addLayout(self._create_nav_buttons_layout())
        main_layout.addLayout(self._create_input_layout())
        
        
        # 添加dock控件（原axis_controls_dock逻辑）
        self.viewer.window.add_dock_widget(
            self.slider_container,
            name="Axis Controls",
            area='left',
            allowed_areas=['left', 'right']
        )

    def _create_nav_buttons_layout(self):
        """创建导航按钮布局"""
        layout = QHBoxLayout()
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)
        return layout

    def _create_input_layout(self):
        """创建输入框布局"""
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