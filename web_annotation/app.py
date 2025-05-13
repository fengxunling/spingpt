from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import nibabel as nib
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64

app = Flask(__name__)

# 确保上传目录存在
UPLOAD_FOLDER = 'uploads'
IMAGES_FOLDER = 'static/images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER

def process_nifti(filepath, output_dir):
    """处理NIfTI文件并生成图像"""
    # 加载NIfTI文件
    img = nib.load(filepath)
    data = img.get_fdata()
    
    # 获取中间切片
    slice_x = data.shape[0] // 2
    slice_y = data.shape[1] // 2
    slice_z = data.shape[2] // 2
    
    # 生成三个方向的切片图像
    slices = [
        ('axial', data[:, :, slice_z], f"z={slice_z}"),
        ('coronal', data[:, slice_y, :], f"y={slice_y}"),
        ('sagittal', data[slice_x, :, :], f"x={slice_x}")
    ]
    
    image_paths = []
    slice_indices = []
    
    for name, slice_data, slice_index in slices:
        # 归一化数据以便显示
        slice_data = slice_data.T  # 转置以获得正确的方向
        if slice_data.max() > 0:
            slice_data = (slice_data / slice_data.max()) * 255
        
        # 创建图像
        plt.figure(figsize=(10, 10))
        plt.imshow(slice_data, cmap='gray')
        plt.axis('off')
        
        # 保存图像
        filename = f"{os.path.basename(filepath).split('.')[0]}_{name}.png"
        output_path = os.path.join(output_dir, filename)
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
        plt.close()
        
        image_paths.append(filename)
        slice_indices.append(slice_index)
    
    return image_paths, slice_indices

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': '没有文件部分'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'})
        
        if file and file.filename.endswith('.nii.gz'):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            
            # 处理NIfTI文件并生成图像
            image_paths, slice_indices = process_nifti(filename, app.config['IMAGES_FOLDER'])
            
            # 返回包含图像路径的HTML页面
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>医学影像查看</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; text-align: center; }
                    h1 { color: #333; }
                    .container { margin: 30px auto; max-width: 900px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    .image-container { display: flex; flex-wrap: wrap; justify-content: center; }
                    .image-box { margin: 10px; text-align: center; }
                    .image-box img { max-width: 100%; height: auto; border: 1px solid #ddd; }
                    .back-btn { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-top: 20px; text-decoration: none; display: inline-block; }
                    .back-btn:hover { background-color: #45a049; }
                    .slice-info { font-weight: bold; color: #555; margin-top: 5px; }
                </style>
            </head>
            <body>
                <h1>医学影像查看</h1>
                <div class="container">
                    <h2>文件: {{ filename }}</h2>
                    <div class="image-container">
                        {% for i in range(images|length) %}
                        <div class="image-box">
                            <h3>{{ images[i].split('_')[-1].split('.')[0] }}</h3>
                            <div class="slice-info">{{ slice_indices[i] }}</div>
                            <img src="{{ url_for('static', filename='images/' + images[i]) }}" alt="{{ images[i] }}">
                        </div>
                        {% endfor %}
                    </div>
                    <a href="/" class="back-btn">返回上传页面</a>
                </div>
            </body>
            </html>
            ''', filename=file.filename, images=image_paths, slice_indices=slice_indices)
        else:
            return jsonify({'error': '请上传.nii.gz格式的文件'})
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>医学影像上传</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; text-align: center; }
            h1 { color: #333; }
            .upload-container { margin: 30px auto; max-width: 500px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .upload-btn { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px; }
            .upload-btn:hover { background-color: #45a049; }
            .file-input { margin: 20px 0; }
            .note { color: #666; font-size: 0.9em; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>医学影像上传系统</h1>
        <div class="upload-container">
            <p>请选择您要上传的医学影像文件</p>
            <form method="post" enctype="multipart/form-data">
                <div class="file-input">
                    <input type="file" name="file" id="file" accept=".nii.gz">
                </div>
                <button type="submit" class="upload-btn">上传文件</button>
            </form>
            <p class="note">注意：仅支持.nii.gz格式的文件</p>
        </div>
    </body>
    </html>
    '''

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)