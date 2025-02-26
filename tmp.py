import os
import sys
sys.path.append(os.path.dirname(__file__)+'/napari-nifti/src/')

# ... [保留原有导入和ScreenRecorder类] ...

# 修改轴向视图的旋转方式并调整布局
# ========== 修改切片生成方式 ==========
axial_slice = np.rot90(image_array[initial_z, :, :], k=1)  # 逆时针旋转90度
coronal_slice = np.fliplr(np.rot90(image_array[:, initial_y, :], k=2))
sagittal_slice = np.fliplr(np.rot90(image_array[:, :, initial_x], k=2))

# ========== 调整视图布局 ==========
# 轴向视图和矢状视图并排显示
axial_layer = viewer.add_image(axial_slice, name='Axial')
sagittal_layer = viewer.add_image(sagittal_slice, name='Sagittal')
coronal_layer = viewer.add_image(coronal_slice, name='Coronal', visible=False)  # 默认隐藏冠状视图

# 设置新布局参数
view_scale = 0.25
axial_layer.translate = (-300, -150)  # 左半部分
axial_layer.scale = [view_scale, view_scale] 
sagittal_layer.translate = (100, -150)    # 右半部分 
sagittal_layer.scale = [view_scale, view_scale]
coronal_layer.translate = (-300, 200)     # 下方区域
coronal_layer.scale = [view_scale, view_scale]

# ========== 添加冠状视图切换按钮 ==========
from qtpy.QtWidgets import QPushButton

# 在滑块容器中添加按钮
coronal_btn = QPushButton("Toggle Coronal View")
def toggle_coronal():
    coronal_layer.visible = not coronal_layer.visible
    coronal_btn.setText("Hide Coronal" if coronal_layer.visible else "Show Coronal")
coronal_btn.clicked.connect(toggle_coronal)

# 将按钮添加到布局
main_layout.insertWidget(1, coronal_btn)  # 在滑块下方添加按钮

# ========== 更新切片更新逻辑 ==========
def update_slices(event):
    z, y, x = viewer.dims.current_step
    
    # 更新轴向视图（旋转90度）
    axial_slice = np.rot90(image_array[z, :, :], k=1)
    axial_slice = add_text_to_slice(axial_slice, f"Axial (Z={z})\nY={y}\nX={x}")
    
    # 更新冠状视图
    coronal_slice = np.fliplr(np.rot90(image_array[:, y, :], k=2))
    coronal_slice = add_text_to_slice(coronal_slice, f"Coronal (Y={y})\nZ={z}\nX={x}")
    
    # 更新矢状视图
    sagittal_slice = np.fliplr(np.rot90(image_array[:, :, x], k=2))
    sagittal_slice = add_text_to_slice(sagittal_slice, f"Sagittal (X={x})\nZ={z}\nY={y}")

    # 更新图层数据
    axial_layer.data = axial_slice
    sagittal_layer.data = sagittal_slice
    coronal_layer.data = coronal_slice  # 即使不可见也更新数据
    
    # ... [保留原有的线框更新逻辑] ...

# ... [保留其余原有代码] ...