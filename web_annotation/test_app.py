from flask import Flask, request, jsonify, render_template, url_for
import os
import nibabel as nib
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
import re
from datetime import datetime

app = Flask(__name__)

# Ensure upload directories exist
UPLOAD_FOLDER = 'uploads'
IMAGES_FOLDER = 'static/images'
SCREENSHOTS_FOLDER = 'static/screenshots'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER
app.config['SCREENSHOTS_FOLDER'] = SCREENSHOTS_FOLDER

def process_nifti(filepath, output_dir, slice_x=None, slice_y=None, slice_z=None):
    """Process NIfTI file and generate images"""
    # Load NIfTI file
    img = nib.load(filepath)
    data = img.get_fdata()
    
    # Use middle slice if no slice index provided
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
    """Update slice index and return new images"""
    data = request.json
    filename = data.get('filename')
    slice_x = int(data.get('slice_x'))
    slice_y = int(data.get('slice_y'))
    slice_z = int(data.get('slice_z'))
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File does not exist'})
    
    # Process NIfTI file and generate new images
    image_paths, slice_indices, _ = process_nifti(
        filepath, 
        app.config['IMAGES_FOLDER'],
        slice_x=slice_x,
        slice_y=slice_y,
        slice_z=slice_z
    )
    
    # 仍然返回所有图像路径，前端会选择性使用
    return jsonify({
        'images': image_paths,
        'slice_indices': slice_indices
    })



@app.route('/process_prompt', methods=['POST'])
def process_prompt():
    """Process user submitted prompt"""
    data = request.json
    filename = data.get('filename')
    prompt = data.get('prompt')
    slice_x = int(data.get('slice_x'))
    slice_y = int(data.get('slice_y'))
    slice_z = int(data.get('slice_z'))
    
    # Load NIfTI file
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File does not exist'})
    
    # Get current slice images
    img = nib.load(filepath)
    data_array = img.get_fdata()
    
    # Get slices in three directions
    slices = [
        ('axial', data_array[:, :, slice_z]),
        ('coronal', data_array[:, slice_y, :]),
        ('sagittal', data_array[slice_x, :, :])
    ]
    
    # Convert images to base64 for sending to Ollama
    encoded_images = []
    for name, slice_data in slices:
        # Normalize data for display
        if slice_data.max() > 0:
            slice_data = (slice_data / slice_data.max()) * 255
        
        plt.figure(figsize=(20, 20), dpi=300)
        plt.imshow(slice_data, cmap='gray', interpolation='none')
        plt.axis('off')
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0, dpi=300)
        plt.close()
        
        # Convert to base64
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        encoded_images.append((name, img_base64))
    
    # Call Ollama API
    try:
        import requests
        
        # Build prompt combining user input and image information
        if not prompt:
            prompt = "Please describe the visible anatomical structures and possible pathological findings in this spine MRI medical image (could be cervical, thoracic, lumbar, sacral, or coccygeal spine)."
        
        # Analyze three views separately but collect all results
        view_results = []
        for view_name, img_base64 in encoded_images:
            # Build Ollama API request
            ollama_url = "http://localhost:11434/api/generate"  # Default Ollama address
            
            # Build specific prompt for each view
            view_prompt = f"{prompt}\nThis is a {view_name} view medical image."
            if view_name == "axial":
                view_prompt += "Axial MRI image: (axial plane, horizontal section from head to foot)"
            elif view_name == "coronal":
                view_prompt += "Coronal MRI image: (coronal plane, vertical section from front to back)"
            elif view_name == "sagittal":
                view_prompt += "Sagittal MRI image: (sagittal plane, vertical section from left to right)"
            
            payload = {
                "model": "rohithbojja/llava-med-v1.6:latest",  # Use full model name
                "prompt": view_prompt,
                "images": [img_base64],
                "stream": False
            }
            
            response = requests.post(ollama_url, json=payload)
            
            if response.status_code == 200:
                view_result = response.json().get('response', 'Unable to get model response')
                view_results.append((view_name, view_result))
            else:
                view_results.append((view_name, f"Ollama API call failed: {response.status_code} - {response.text}"))
        
        # Use all collected view analysis results to call model again for comprehensive analysis
        if all(result for _, result in view_results):
            combined_prompt = f"""Based on the following view analyses, please first distinguish whether the image is T1 or T2.

            Then determine if it's from cervical, thoracic, lumbar, sacral, or coccygeal spine.
            
            Then describe the structures and possible pathological findings in the spine MRI medical image:
            
            Sagittal view analysis: {view_results[2][1]}
            
            """
            
            payload = {
                "model": "rohithbojja/llava-med-v1.6:latest",  # Can also use text-only model like llama3
                "prompt": combined_prompt,
                "stream": False
            }
            
            response = requests.post(ollama_url, json=payload)
            
            if response.status_code == 200:
                result = f"<h3>Comprehensive Analysis Results</h3><p>{response.json().get('response', 'Unable to get model response')}</p>"
            else:
                # If comprehensive analysis fails, show results for each view
                result = "<h3>Comprehensive Analysis Results</h3><p>Unable to generate comprehensive analysis. Here are the analyses for each view:</p>"
                for view_name, view_result in view_results:
                    result += f"<h4>{view_name} View</h4><p>{view_result}</p>"
        else:
            # If any view analysis fails, show available results
            result = "<h3>Partial View Analysis Results</h3>"
            for view_name, view_result in view_results:
                result += f"<h4>{view_name} View</h4><p>{view_result}</p>"

    except Exception as e:
        result = f"Error during processing: {str(e)}\n\nPlease ensure Ollama service is running and LLaVA model is installed. You can install the model using:\n\nollama pull llava"

    return jsonify({
        'result': result
    })

# 添加音频上传处理路由
@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    """Handle audio upload from the browser"""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file part'})
    
    audio_file = request.files['audio']
    filename = request.form.get('filename', 'unknown')
    
    # Create audio directory if it doesn't exist
    audio_dir = os.path.join('static', 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    
    # 添加时间戳到文件名中
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"{os.path.splitext(filename)[0]}_recording_{timestamp}.wav"
    audio_path = os.path.join(audio_dir, audio_filename)
    audio_file.save(audio_path)
    
    return jsonify({'success': True, 'filename': audio_filename})

# 添加音频转录路由
@app.route('/transcribe_audio', methods=['POST'])
def transcribe_audio():
    """Transcribe the uploaded audio file"""
    data = request.json
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'success': False, 'error': 'No filename provided'})
    
    # 直接使用提供的完整文件名
    audio_path = os.path.join('static', 'audio', filename)
    
    if not os.path.exists(audio_path):
        return jsonify({'success': False, 'error': 'Audio file not found'})
    
    try:
        # 使用Whisper模型进行音频转录
        import whisper
        model = whisper.load_model("medium")
        result = model.transcribe(audio_path, language="en")
        transcript = result['text']
        
        # 保存转录文本
        transcript_path = os.path.join('static', 'audio', f"{os.path.splitext(filename)[0]}_transcript.txt")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
        
        return jsonify({
            'success': True,
            'transcript': transcript
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/save_screenshot', methods=['POST'])
def save_screenshot():
    """保存截图到服务器"""
    try:
        data = request.json
        image_data = data.get('image')
        filename = data.get('filename')
        view_type = data.get('view_type', 'unknown')
        
        # 从Base64数据中提取图像数据
        image_data = image_data.split(',')[1] if ',' in image_data else image_data
        image_bytes = base64.b64decode(image_data)
        
        # 生成唯一的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"{os.path.splitext(filename)[0]}_{view_type}_{timestamp}.png"
        screenshot_path = os.path.join(app.config['SCREENSHOTS_FOLDER'], screenshot_filename)
        
        # 保存图像
        with open(screenshot_path, 'wb') as f:
            f.write(image_bytes)
        
        return jsonify({
            'success': True,
            'path': f"/static/screenshots/{screenshot_filename}",
            'filename': screenshot_filename
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 添加图像音频注释关联路由
@app.route('/associate_audio_with_image', methods=['POST'])
def associate_audio_with_image():
    """Associate an audio annotation with a screenshot"""
    data = request.json
    screenshot_filename = data.get('screenshot_filename')
    audio_filename = data.get('audio_filename')
    annotation_text = data.get('annotation_text', '')
    
    if not screenshot_filename or not audio_filename:
        return jsonify({'success': False, 'error': 'Missing required filenames'})
    
    # 创建注释目录（如果不存在）
    annotations_dir = os.path.join('static', 'annotations')
    os.makedirs(annotations_dir, exist_ok=True)
    
    # 生成唯一的注释ID
    annotation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 创建注释记录
    annotation = {
        'id': annotation_id,
        'screenshot': screenshot_filename,
        'audio': audio_filename,
        'text': annotation_text,
        'timestamp': datetime.now().isoformat()
    }
    
    # 保存注释记录到JSON文件
    annotation_file = os.path.join(annotations_dir, f"annotation_{annotation_id}.json")
    try:
        import json
        with open(annotation_file, 'w', encoding='utf-8') as f:
            json.dump(annotation, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'annotation_id': annotation_id,
            'annotation_file': annotation_file
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_screenshots', methods=['GET'])
def get_screenshots():
    """获取与特定文件相关的所有截图"""
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'success': False, 'error': '未提供文件名'})
    
    base_filename = os.path.splitext(filename)[0]
    screenshots = []
    
    try:
        for file in os.listdir(app.config['SCREENSHOTS_FOLDER']):
            if file.startswith(base_filename) and file.endswith('.png'):
                screenshots.append({
                    'filename': file,
                    'path': f"/static/screenshots/{file}",
                    'timestamp': os.path.getmtime(os.path.join(app.config['SCREENSHOTS_FOLDER'], file))
                })
        
        # 按时间戳排序，最新的在前
        screenshots.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'screenshots': screenshots
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_annotations', methods=['GET'])
def get_annotations():
    """Get all annotations for a specific file"""
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'success': False, 'error': 'No filename provided'})
    
    annotations_dir = os.path.join('static', 'annotations')
    if not os.path.exists(annotations_dir):
        return jsonify({'success': True, 'annotations': []})
    
    try:
        import json
        import glob
        
        annotations = []
        annotation_files = glob.glob(os.path.join(annotations_dir, "annotation_*.json"))
        
        for annotation_file in annotation_files:
            with open(annotation_file, 'r', encoding='utf-8') as f:
                annotation = json.load(f)
                if filename in annotation['screenshot']:
                    annotations.append(annotation)
        
        return jsonify({
            'success': True,
            'annotations': annotations
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 修改首页路由，只显示两个视图
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'})
        
        if file and file.filename.endswith('.nii.gz'):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            
            # Process NIfTI file and generate images
            image_paths, slice_indices, dimensions = process_nifti(filename, app.config['IMAGES_FOLDER'])
            
            # 返回模板时仍然传递所有图像，但前端会选择性显示
            return render_template('viewer.html', 
                                  filename=file.filename, 
                                  images=image_paths, 
                                  slice_indices=slice_indices, 
                                  dimensions=dimensions)
        else:
            return jsonify({'error': 'Please upload a .nii.gz format file'})
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)