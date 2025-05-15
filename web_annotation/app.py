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

def process_nifti(filepath, output_dir, slice_x=None, slice_y=None, slice_z=None):
    """处理NIfTI文件并生成图像"""
    # 加载NIfTI文件
    img = nib.load(filepath)
    data = img.get_fdata()
    
    # 如果没有提供切片索引，则使用中间切片
    if slice_x is None:
        slice_x = data.shape[0] // 2
    if slice_y is None:
        slice_y = data.shape[1] // 2
    if slice_z is None:
        slice_z = data.shape[2] // 2
    
    # 确保切片索引在有效范围内
    slice_x = max(0, min(slice_x, data.shape[0] - 1))
    slice_y = max(0, min(slice_y, data.shape[1] - 1))
    slice_z = max(0, min(slice_z, data.shape[2] - 1))
    
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
    
    return image_paths, slice_indices, [data.shape[0], data.shape[1], data.shape[2]]

@app.route('/update_slice', methods=['POST'])
def update_slice():
    """更新切片索引并返回新图像"""
    data = request.json
    filename = data.get('filename')
    slice_x = int(data.get('slice_x'))
    slice_y = int(data.get('slice_y'))
    slice_z = int(data.get('slice_z'))
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': '文件不存在'})
    
    # 处理NIfTI文件并生成新图像
    image_paths, slice_indices, _ = process_nifti(
        filepath, 
        app.config['IMAGES_FOLDER'],
        slice_x=slice_x,
        slice_y=slice_y,
        slice_z=slice_z
    )
    
    return jsonify({
        'images': image_paths,
        'slice_indices': slice_indices
    })

@app.route('/process_prompt', methods=['POST'])
def process_prompt():
    """处理用户提交的prompt"""
    data = request.json
    filename = data.get('filename')
    prompt = data.get('prompt')
    slice_x = int(data.get('slice_x'))
    slice_y = int(data.get('slice_y'))
    slice_z = int(data.get('slice_z'))
    
    # 这里您可以根据需要实现prompt的处理逻辑
    # 例如：分析图像、调用AI模型等
    
    result = 'hello world'
    
    # 在实际应用中，您可能需要：
    # 1. 调用AI模型处理prompt和图像
    # 2. 生成标注或分析结果
    # 3. 返回处理后的图像或文本结果
    
    return jsonify({
        'result': result
    })

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
            image_paths, slice_indices, dimensions = process_nifti(filename, app.config['IMAGES_FOLDER'])
            
            # 返回包含图像路径的HTML页面
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>医学影像查看</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; text-align: center; }
                    h1 { color: #333; }
                    .container { margin: 30px auto; max-width: 1200px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    .image-container { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; }
                    .image-box { flex: 1; margin: 0 10px; text-align: center; }
                    .image-box img { max-width: 100%; height: auto; border: 1px solid #ddd; }
                    .back-btn { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-top: 20px; text-decoration: none; display: inline-block; }
                    .back-btn:hover { background-color: #45a049; }
                    .slice-info { font-weight: bold; color: #555; margin-top: 5px; }
                    .slider-container { margin: 20px 0; }
                    .slider-label { display: inline-block; width: 80px; text-align: right; margin-right: 10px; }
                    .slider { width: 300px; }
                    .loading { display: none; margin: 20px auto; }
                    .controls-container { display: flex; justify-content: space-around; flex-wrap: wrap; }
                    .control-group { margin: 10px; min-width: 350px; }
                </style>
                <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
            </head>
            <body>
                <h1>医学影像查看</h1>
                <div class="container">
                    <h2>文件: {{ filename }}</h2>
                    
                    <div class="controls-container">
                        <div class="control-group">
                            <div class="slider-container">
                                <label class="slider-label">X轴切片:</label>
                                <input type="range" id="slice-x" class="slider" min="0" max="{{ dimensions[0]-1 }}" value="{{ dimensions[0]//2 }}">
                                <span id="slice-x-value">{{ dimensions[0]//2 }}</span>
                            </div>
                            
                            <div class="slider-container">
                                <label class="slider-label">Y轴切片:</label>
                                <input type="range" id="slice-y" class="slider" min="0" max="{{ dimensions[1]-1 }}" value="{{ dimensions[1]//2 }}">
                                <span id="slice-y-value">{{ dimensions[1]//2 }}</span>
                            </div>
                            
                            <div class="slider-container">
                                <label class="slider-label">Z轴切片:</label>
                                <input type="range" id="slice-z" class="slider" min="0" max="{{ dimensions[2]-1 }}" value="{{ dimensions[2]//2 }}">
                                <span id="slice-z-value">{{ dimensions[2]//2 }}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="loading">更新中...</div>
                    
                    <div class="image-container" id="image-container">
                        {% for i in range(images|length) %}
                        <div class="image-box">
                            <h3>{{ images[i].split('_')[-1].split('.')[0] }}</h3>
                            <div class="slice-info" id="slice-info-{{ i }}">{{ slice_indices[i] }}</div>
                            <img src="{{ url_for('static', filename='images/' + images[i]) }}" alt="{{ images[i] }}" id="image-{{ i }}">
                        </div>
                        {% endfor %}
                        
                        <!-- 新增的Prompt文本框 -->
                        <div class="prompt-box">
                            <h3>输入Prompt</h3>
                            <textarea id="prompt-text" placeholder="请在此输入您的prompt..."></textarea>
                            <button id="submit-prompt">提交</button>
                            <div class="prompt-result" id="prompt-result">
                                <p>结果将显示在这里...</p>
                            </div>
                        </div>
                    </div>
                    <a href="/" class="back-btn">返回上传页面</a>
                </div>
                
                <script>
                    // 防抖函数
                    function debounce(func, wait) {
                        let timeout;
                        return function() {
                            const context = this;
                            const args = arguments;
                            clearTimeout(timeout);
                            timeout = setTimeout(() => {
                                func.apply(context, args);
                            }, wait);
                        };
                    }
                    
                    // 更新切片显示
                    const updateSlices = debounce(function() {
                        $('.loading').show();
                        
                        const sliceX = $('#slice-x').val();
                        const sliceY = $('#slice-y').val();
                        const sliceZ = $('#slice-z').val();
                        
                        $.ajax({
                            url: '/update_slice',
                            type: 'POST',
                            contentType: 'application/json',
                            data: JSON.stringify({
                                filename: '{{ filename }}',
                                slice_x: sliceX,
                                slice_y: sliceY,
                                slice_z: sliceZ
                            }),
                            success: function(response) {
                                // 更新图像
                                for (let i = 0; i < response.images.length; i++) {
                                    const imgPath = '/static/images/' + response.images[i] + '?t=' + new Date().getTime();
                                    $('#image-' + i).attr('src', imgPath);
                                    $('#slice-info-' + i).text(response.slice_indices[i]);
                                }
                                $('.loading').hide();
                            },
                            error: function() {
                                alert('更新切片失败');
                                $('.loading').hide();
                            }
                        });
                    }, 100);
                    
                    // 监听滑块变化
                    $('#slice-x').on('input', function() {
                        $('#slice-x-value').text($(this).val());
                        updateSlices();
                    });
                    
                    $('#slice-y').on('input', function() {
                        $('#slice-y-value').text($(this).val());
                        updateSlices();
                    });
                    
                    $('#slice-z').on('input', function() {
                        $('#slice-z-value').text($(this).val());
                        updateSlices();
                    });
                    
                </script>
            </body>
            </html>
            ''', filename=file.filename, images=image_paths, slice_indices=slice_indices, dimensions=dimensions)
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