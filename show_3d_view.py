import os
import sys
sys.path.append(os.path.dirname(__file__)+'/napari-nifti-main/src/')
import numpy as np
from napari_nifti._reader import napari_get_reader
import napari
from napari import Viewer
import nibabel as nib
from qtpy.QtWidgets import QApplication

def show_3d_view(filepath):
    """显示NIFTI文件的3D视图"""
    # 读取图像数据
    reader = napari_get_reader(filepath)
    if not reader:
        print("无法找到文件的读取器")
        sys.exit(1)
        
    layer_data = reader(filepath)
    if not layer_data:
        print("无法读取图层数据")
        sys.exit(1)
        
    # 提取图像数据
    image_array = layer_data[0][0]
    metadata = layer_data[0][1]
    
    # 创建查看器
    viewer = Viewer(title="3D file")
    viewer.window._qt_window.resize(800, 600)
    
    # 添加体积渲染
    volume_layer = viewer.add_image(
        image_array,
        rendering='mip',  # 最大强度投影
        name='3D render image',
        blending='additive',
        opacity=0.7
    )
    
    # 设置相机为3D模式
    viewer.dims.ndisplay = 3
    
    # 显示文件信息
    print(f"文件: {os.path.basename(filepath)}")
    print(f"数据形状: {image_array.shape}")
    
    # 运行napari
    napari.run()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 使用默认文件
        default_file = "T2G002_MRI_Spine_t2_space_sag_p2_iso_20240820161941_19001.nii.gz"
        print(f"未指定文件，使用默认文件: {default_file}")
        file_name = default_file
    else:
        file_name = sys.argv[1].strip('"')  # 移除潜在的引号
        
    # 构建文件路径
    IMAGE_PATH = os.path.join(os.path.dirname(__file__), 'data')
    filepath = os.path.join(IMAGE_PATH, file_name)
    
    # 验证路径
    if not os.path.exists(filepath):
        print(f"文件路径不存在: {filepath}")
        sys.exit(1)
        
    # 显示3D视图
    show_3d_view(filepath)