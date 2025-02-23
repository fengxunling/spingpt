import napari
from napari import Viewer
from magicgui import magicgui
from typing import Optional
import nibabel as nib
import numpy as np
import re

class SwitchViewer:

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
