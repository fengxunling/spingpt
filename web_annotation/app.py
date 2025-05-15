from flask import Flask, request, jsonify, send_from_directory, render_template_string
import os
import nibabel as nib
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64

app = Flask(__name__)

app = Flask(__name__)
# Ensure upload directories exist
UPLOAD_FOLDER = 'uploads'
IMAGES_FOLDER = 'static/images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER

def process_nifti(filepath, output_dir, slice_x=None, slice_y=None, slice_z=None):
    """Process NIfTI file and generate images"""
    # Load NIfTI file
    img = nib.load(filepath)
    data = img.get_fdata()
    
    # Use middle slice if no slice index is provided
    if slice_x is None:
        slice_x = data.shape[0] // 2
    if slice_y is None:
        slice_y = data.shape[1] // 2
    if slice_z is None:
        slice_z = data.shape[2] // 2
    
    # Ensure slice indices are within valid range
    slice_x = max(0, min(slice_x, data.shape[0] - 1))
    slice_y = max(0, min(slice_y, data.shape[1] - 1))
    slice_z = max(0, min(slice_z, data.shape[2] - 1))
    
    # Generate slice images in three directions
    slices = [
        ('axial', np.rot90(data[:, :, slice_z], 2), f"z={slice_z}"),
        ('coronal', np.rot90(data[:, slice_y, :], 2), f"y={slice_y}"),
        ('sagittal', np.rot90(data[slice_x, :, :], 2), f"x={slice_x}")
    ]
    
    image_paths = []
    slice_indices = []
    
    for name, slice_data, slice_index in slices:
        # Normalize data for display
        slice_data = slice_data.T  # Transpose for correct orientation
        if slice_data.max() > 0:
            slice_data = (slice_data / slice_data.max()) * 255
        
        # Create image
        plt.figure(figsize=(10, 10))
        plt.imshow(slice_data, cmap='gray')
        plt.axis('off')
        
        # Save image
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
    
    # 加载NIfTI文件
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': '文件不存在'})
    
    # 获取当前切片的图像
    img = nib.load(filepath)
    data_array = img.get_fdata()
    
    # 获取三个方向的切片
    slices = [
        ('axial', np.rot90(data_array[:, :, slice_z], 2)),
        ('coronal', np.rot90(data_array[:, slice_y, :], 2)),
        ('sagittal', np.rot90(data_array[slice_x, :, :], 2))
    ]
    
    # 将图像转换为base64编码，以便发送给Ollama
    encoded_images = []
    for name, slice_data in slices:
        # 归一化数据用于显示
        if slice_data.max() > 0:
            slice_data = (slice_data / slice_data.max()) * 255
        
        # 创建图像
        plt.figure(figsize=(10, 10))
        plt.imshow(slice_data, cmap='gray')
        plt.axis('off')
        
        # 保存到内存缓冲区
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0)
        plt.close()
        
        # 转换为base64
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        encoded_images.append((name, img_base64))
    
    # 调用Ollama API
    try:
        import requests
        
        # 构建提示词，结合用户输入的prompt和图像信息
        if not prompt:
            prompt = "请描述这张医学影像中可见的解剖结构和可能的病理发现。"
        
        # 分析所有三个方向的切片
        results = []
        for view_name, img_base64 in encoded_images:
            # 构建Ollama API请求
            ollama_url = "http://localhost:11434/api/generate"  # 默认Ollama地址
            
            # 为每个视图构建特定的提示词
            view_prompt = f"{prompt}\n这是一张{view_name}视图的医学影像。"
            if view_name == "axial":
                view_prompt += "（轴向切面，从头到脚的水平切面）"
            elif view_name == "coronal":
                view_prompt += "（冠状切面，从前到后的垂直切面）"
            elif view_name == "sagittal":
                view_prompt += "（矢状切面，从左到右的垂直切面）"
            
            payload = {
                "model": "rohithbojja/llava-med-v1.6:latest",  # 使用完整的模型名称
                "prompt": view_prompt,
                "images": [img_base64],
                "stream": False
            }
            
            response = requests.post(ollama_url, json=payload)
            
            if response.status_code == 200:
                view_result = response.json().get('response', '无法获取模型响应')
                results.append(f"<h3>{view_name}视图分析</h3><p>{view_result}</p>")
            else:
                results.append(f"<h3>{view_name}视图分析</h3><p>Ollama API调用失败: {response.status_code} - {response.text}</p>")
        
        # 合并所有结果
        result = "".join(results)
    
    except Exception as e:
        result = f"处理过程中出错: {str(e)}\n\n请确保Ollama服务已启动，并安装了LLaVA模型。您可以使用以下命令安装模型：\n\nollama pull llava"
    
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
                    .image-container { display: flex; justify-content: space-between; align-items: flex-start; margin-top: 20px; }
                    .image-section { flex: 2; display: flex; flex-wrap: wrap; justify-content: space-between; }
                    .image-box { width: 32%; margin-bottom: 15px; text-align: center; }
                    .image-box img { max-width: 100%; height: auto; border: 1px solid #ddd; }
                    .prompt-section { flex: 1; margin-left: 20px; border-left: 1px solid #ddd; padding-left: 20px; text-align: left; }
                    .back-btn { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-top: 20px; text-decoration: none; display: inline-block; }
                    .back-btn:hover { background-color: #45a049; }
                    .slice-info { font-weight: bold; color: #555; margin-top: 5px; }
                    .slider-container { margin: 20px 0; }
                    .slider-label { display: inline-block; width: 80px; text-align: right; margin-right: 10px; }
                    .slider { width: 300px; }
                    .loading { display: none; margin: 20px auto; }
                    .controls-container { display: flex; justify-content: space-around; flex-wrap: wrap; }
                    .control-group { margin: 10px; min-width: 350px; }
                    .prompt-box { width: 100%; }
                    #prompt-text { width: 100%; height: 150px; margin: 10px 0; padding: 8px; box-sizing: border-box; }
                    #submit-prompt { background-color: #4CAF50; color: white; padding: 8px 15px; border: none; border-radius: 4px; cursor: pointer; }
                    #submit-prompt:hover { background-color: #45a049; }
                    .prompt-result { margin-top: 15px; padding: 10px; background-color: #f9f9f9; border-radius: 4px; min-height: 100px; }
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
                        <div class="image-section">
                            {% for i in range(images|length) %}
                            <div class="image-box">
                                <h3>{{ images[i].split('_')[-1].split('.')[0] }}</h3>
                                <div class="slice-info" id="slice-info-{{ i }}">{{ slice_indices[i] }}</div>
                                <img src="{{ url_for('static', filename='images/' + images[i]) }}" alt="{{ images[i] }}" id="image-{{ i }}">
                            </div>
                            {% endfor %}
                        </div>
                        
                        <!-- 新增的Prompt文本框，占比1/3 -->
                        <div class="prompt-section">
                            <h3>输入Prompt</h3>
                            <div class="prompt-box">
                                <textarea id="prompt-text" placeholder="请在此输入您的prompt..."></textarea>
                                <button id="submit-prompt">提交</button>
                                <div class="prompt-result" id="prompt-result">
                                    <p>结果将显示在这里...</p>
                                </div>
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
                    
                    // 添加提交prompt的功能
                    $('#submit-prompt').on('click', function() {
                        const promptText = $('#prompt-text').val();
                        if (!promptText.trim()) {
                            alert('请输入prompt内容');
                            return;
                        }
                        
                        const sliceX = $('#slice-x').val();
                        const sliceY = $('#slice-y').val();
                        const sliceZ = $('#slice-z').val();
                        
                        $.ajax({
                            url: '/process_prompt',
                            type: 'POST',
                            contentType: 'application/json',
                            data: JSON.stringify({
                                filename: '{{ filename }}',
                                prompt: promptText,
                                slice_x: sliceX,
                                slice_y: sliceY,
                                slice_z: sliceZ
                            }),
                            success: function(response) {
                                $('#prompt-result').html('<p>' + response.result + '</p>');
                            },
                            error: function() {
                                alert('处理prompt失败');
                            }
                        });
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