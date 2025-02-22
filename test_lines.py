import napari
import numpy as np

# 创建 Viewer 并添加初始线段
viewer = napari.Viewer()
initial_line = np.array([[50, 50], [200, 200]])
shapes_layer = viewer.add_shapes(
    initial_line,
    shape_type='line',
    edge_color='blue',
    edge_width=2,
    name='my_line'  # 为图层命名便于后续操作
)

# 定义新坐标的函数（例如：将线段移动到新位置）
def update_line_position():
    new_line_data = np.array([[100, 100], [300, 300]])  # 新的端点坐标
    shapes_layer.data = new_line_data  # 直接更新图层数据
    shapes_layer.refresh()  

# 调用函数更新线段位置（例如绑定到按钮或定时器）
update_line_position()

napari.run()
