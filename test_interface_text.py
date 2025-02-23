import os
import sys

import napari
from napari import Viewer
from magicgui import magicgui
from typing import Optional
import nibabel as nib
import numpy as np
import re

    
class MultiViewer:
    def __init__(self, file_path: str):
        # 加载数据
        self.img = nib.load(file_path)
        self.data = self.img.get_fdata()
        print(f"Data shape: {self.data.shape}")
        
        # 创建主 viewer
        self.viewer = Viewer()
        
        # 初始化显示
        self._show_all_views()

    def _show_all_views(self, slice_idx: Optional[int] = None):
        # 默认显示中间层
        if slice_idx is None:
            slice_idx = self.data.shape[0] // 2

        # 添加主视图
        self.viewer.add_image(self.data, name='3D Volume')
        

    def _switch_view(self, command: str):
        print(f"Switching view to: {command}")
        command = command.lower().strip()
        
        # 清除所有现有图层（避免图层叠加）
        self.viewer.layers.clear()

        match = re.search(r'\d+', command)
        number = 1
        if match:
            number = int(match.group())  # 提取并转为整数
            print(number)  # 输出: 123
        else:
            print("未找到数字")
        
        # 获取对应切片的二维数据
        if "sagittal" in command:
            slice_data = self.data[number, :, :]
        elif "coronal" in command:
            slice_data = self.data[:, number, :]
        elif "axial" in command:
            slice_data = self.data[:, :, number]
        else:
            print(f"未知命令: {command}")
            return
        
        # 添加新的二维图层到Viewer
        self.viewer.add_image(slice_data, name=command)


    def _show_all_views(self, slice_idx: Optional[int] = None):
        # 默认显示中间层
        if slice_idx is None:
            slice_idx = self.data.shape[0] // 2

        # 添加主视图
        self.viewer.add_image(self.data, name='3D Volume')

    def add_control_panel(self):
        @magicgui(
            command={"label": "输入指令:", "tooltip": "例如: show coronal, switch to axial"},
            call_button="执行"
        )
        def control_panel(command: str = ""):
            if "view" in command or "show" in command:
                self._switch_view(self, command)

        # 将控制面板添加到主窗口
        self.viewer.window.add_dock_widget(control_panel, area='right')


if __name__ == "__main__":
    file_path = "D:/projects/spingpt/data/Dicom_t2_trufi3d_cor_0.6_20230123141752_3.nii/Dicom_t2_trufi3d_cor_0.6_20230123141752_3.nii"
    
    # 初始化查看器
    mv = MainViewer(file_path)
    
    # 添加控制面板
    mv.add_control_panel()
    
    # 启动 napari
    napari.run()
