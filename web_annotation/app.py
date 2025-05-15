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
    """Update slice indices and return new images"""
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
    
    # Convert images to base64 encoding for sending to Ollama
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
            prompt = "Please describe the visible anatomical structures and possible pathological findings in this spine MRI medical image (it could be cervical spine, thoracic spine, lumbar spine, sacral spine, coccygeal spine)."
        
        # 分别分析三个视图，但收集所有结果
        view_results = []
        for view_name, img_base64 in encoded_images:
            # Build Ollama API request
            ollama_url = "http://localhost:11434/api/generate"  # Default Ollama address
            
            # Build specific prompt for each view
            view_prompt = f"{prompt}\nThis is a {view_name} view medical image."
            if view_name == "axial":
                view_prompt += "axial MRI image: (Axial plane, horizontal section from head to foot)"
            elif view_name == "coronal":
                view_prompt += "coronal MRI image: (Coronal plane, vertical section from front to back)"
            elif view_name == "sagittal":
                view_prompt += "sagittal MRI image: (Sagittal plane, vertical section from left to right)"
            
            payload = {
                "model": "rohithbojja/llava-med-v1.6:latest",  # Use complete model name
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
        
        # Use all collected view analysis results to call the model again for comprehensive analysis
        if all(result for _, result in view_results):
            combined_prompt = f"""Based on the analysis of the following views, please first distinguish if the image is T1 or T2 image.

            Then distinguish if it is from cervical spine, thoracic spine, lumbar spine, sacral spine, or coccygeal spine.
            
            Then describe the structures and possible pathological findings in the spine MRI medical image.:
            
            Sagittal view analysis: {view_results[2][1]}
            
            """
            
            payload = {
                "model": "rohithbojja/llava-med-v1.6:latest",  # Can also use text-only models like llama3
                "prompt": combined_prompt,
                "stream": False
            }
            
            response = requests.post(ollama_url, json=payload)
            
            if response.status_code == 200:
                result = f"<h3>Comprehensive Analysis Results</h3><p>{response.json().get('response', 'Unable to get model response')}</p>"
            else:
                # If comprehensive analysis fails, display results from individual views
                result = "<h3>Comprehensive Analysis Results</h3><p>Unable to generate comprehensive analysis. Here are the individual view analyses:</p>"
                for view_name, view_result in view_results:
                    result += f"<h4>{view_name} View</h4><p>{view_result}</p>"
        else:
            # If any view analysis fails, display available results
            result = "<h3>Partial View Analysis Results</h3>"
            for view_name, view_result in view_results:
                result += f"<h4>{view_name} View</h4><p>{view_result}</p>"

    except Exception as e:
        result = f"Error during processing: {str(e)}\n\nPlease ensure Ollama service is running and LLaVA model is installed. You can install the model using the command:\n\nollama pull llava"

    return jsonify({
        'result': result
    })

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    """接收前端上传的音频文件"""
    if 'audio' not in request.files:
        return jsonify({'error': '没有音频文件'}), 400
    audio = request.files['audio']
    filename = request.form.get('filename', 'unknown')
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_record.wav")
    audio.save(save_path)
    return jsonify({'success': True, 'message': '音频已保存'})

@app.route('/transcribe_audio', methods=['POST'])
def transcribe_audio():
    """音频转文字并保存"""
    data = request.json
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': '缺少文件名'}), 400
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_record.wav")
    if not os.path.exists(audio_path):
        return jsonify({'error': '音频文件不存在'}), 404

    try:
        import whisper
        model = whisper.load_model("medium")
        result = model.transcribe(audio_path, language="en")
        transcript = result['text']
        # 保存转录文本
        transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}_transcript.txt")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
        return jsonify({'success': True, 'transcript': transcript})
    except Exception as e:
        return jsonify({'error': f'转录失败: {str(e)}'}), 500

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
            
            # Return HTML page with image paths
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Medical Image Viewer</title>
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
                <h1>Medical Image Viewer</h1>
                <div class="container">
                    <h2>File: {{ filename }}</h2>
                    
                    <div class="controls-container">
                        <div class="control-group">
                            <div class="slider-container">
                                <label class="slider-label">X-axis slice:</label>
                                <input type="range" id="slice-x" class="slider" min="0" max="{{ dimensions[0]-1 }}" value="{{ dimensions[0]//2 }}">
                                <span id="slice-x-value">{{ dimensions[0]//2 }}</span>
                            </div>
                            
                            <div class="slider-container">
                                <label class="slider-label">Y-axis slice:</label>
                                <input type="range" id="slice-y" class="slider" min="0" max="{{ dimensions[1]-1 }}" value="{{ dimensions[1]//2 }}">
                                <span id="slice-y-value">{{ dimensions[1]//2 }}</span>
                            </div>
                            
                            <div class="slider-container">
                                <label class="slider-label">Z-axis slice:</label>
                                <input type="range" id="slice-z" class="slider" min="0" max="{{ dimensions[2]-1 }}" value="{{ dimensions[2]//2 }}">
                                <span id="slice-z-value">{{ dimensions[2]//2 }}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="loading">Updating...</div>
                    
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
                        
                        <!-- Prompt textbox taking 1/3 of space -->
                        <div class="prompt-section">
                            <h3>Enter Prompt</h3>
                            <div class="prompt-box">
                                <textarea id="prompt-text" placeholder="Enter your prompt here..."></textarea>
                                <button id="submit-prompt">Submit</button>
                                <div style="margin-top:15px;">
                                    <button id="record-btn">🎤 开始录音</button>
                                    <button id="stop-btn" disabled>停止录音</button>
                                    <button id="transcribe-btn" disabled>转录</button>
                                    <audio id="audio-playback" controls style="display:none;margin-top:10px;"></audio>
                                    <div id="transcript-result" style="margin-top:10px;color:#333;"></div>
                                </div>
                                <div class="prompt-result" id="prompt-result">
                                    <p>Results will be shown here...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <a href="/" class="back-btn">Back to Upload Page</a>
                </div>
                
                <script>
                    // Debounce function
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
                    
                    // Update slice display
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
                                // Update images
                                for (let i = 0; i < response.images.length; i++) {
                                    const imgPath = '/static/images/' + response.images[i] + '?t=' + new Date().getTime();
                                    $('#image-' + i).attr('src', imgPath);
                                    $('#slice-info-' + i).text(response.slice_indices[i]);
                                }
                                $('.loading').hide();
                            },
                            error: function() {
                                alert('Failed to update slices');
                                $('.loading').hide();
                            }
                        });
                    }, 100);
                    
                    // Listen for slider changes
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
                    
                    // Add prompt submission functionality
                    $('#submit-prompt').on('click', function() {
                        const promptText = $('#prompt-text').val();
                        if (!promptText.trim()) {
                            alert('Please enter prompt content');
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
                                alert('Failed to process prompt');
                            }
                        });
                    });

                    let audioBlob = null;
                    let filename = "{{ filename }}"; // 用于音频文件名
                    let mediaRecorder;
                    let audioChunks = [];

                    $('#record-btn').on('click', function() {
                        navigator.mediaDevices.getUserMedia({ audio: true })
                            .then(stream => {
                                mediaRecorder = new MediaRecorder(stream);
                                mediaRecorder.start();
                                audioChunks = [];
                                mediaRecorder.ondataavailable = e => {
                                    audioChunks.push(e.data);
                                };
                                mediaRecorder.onstop = e => {
                                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                                    const audioUrl = URL.createObjectURL(audioBlob);
                                    $('#audio-playback').attr('src', audioUrl).show();

                                    // 上传音频到后端
                                    const formData = new FormData();
                                    formData.append('audio', audioBlob, 'record.wav');
                                    formData.append('filename', '{{ filename }}');
                                    $.ajax({
                                        url: '/upload_audio',
                                        type: 'POST',
                                        data: formData,
                                        processData: false,
                                        contentType: false,
                                        success: function(response) {
                                            alert('音频上传成功');
                                        },
                                        error: function() {
                                            alert('音频上传失败');
                                        }
                                    });
                                };
                                $('#record-btn').attr('disabled', true);
                                $('#stop-btn').attr('disabled', false);
                            })
                            .catch(err => {
                                alert('无法访问麦克风: ' + err);
                            });
                    });

                    $('#stop-btn').on('click', function() {
                        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                            mediaRecorder.stop();
                            $('#record-btn').attr('disabled', false);
                            $('#stop-btn').attr('disabled', true);
                            $('#transcribe-btn').prop('disabled', false); // 录音结束后允许转录
                        }
                    });

                    // 转录按钮事件
                    $('#transcribe-btn').on('click', function() {
                        $('#transcribe-btn').prop('disabled', true);
                        $('#transcript-result').text('正在转录...');
                        $.ajax({
                            url: '/transcribe_audio',
                            type: 'POST',
                            contentType: 'application/json',
                            data: JSON.stringify({ filename: filename }),
                            success: function(response) {
                                if (response.success) {
                                    $('#transcript-result').text('转录结果：' + response.transcript);
                                } else {
                                    $('#transcript-result').text('转录失败：' + (response.error || '未知错误'));
                                }
                            },
                            error: function() {
                                $('#transcript-result').text('转录请求失败');
                            }
                        });
                    });
                </script>
            </body>
            </html>
            ''', filename=file.filename, images=image_paths, slice_indices=slice_indices, dimensions=dimensions)
        else:
            return jsonify({'error': 'Please upload a .nii.gz format file'})
    
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Medical Image Upload</title>
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
        <h1>Medical Image Upload System</h1>
        <div class="upload-container">
            <p>Please select the medical image file to upload</p>
            <form method="post" enctype="multipart/form-data">
                <div class="file-input">
                    <input type="file" name="file" id="file" accept=".nii.gz">
                </div>
                <button type="submit" class="upload-btn">Upload File</button>
            </form>
            <p class="note">Note: Only .nii.gz format files are supported</p>
        </div>
    </body>
    </html>
    '''

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)