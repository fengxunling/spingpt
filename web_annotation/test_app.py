from flask import Flask, request, jsonify, render_template, url_for
import os
import nibabel as nib
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64

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

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    """Process uploaded audio file"""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'})
    
    audio_file = request.files['audio']
    filename = request.form.get('filename')
    
    if not filename:
        return jsonify({'error': 'No filename provided'})
    
    # Create audio directory
    audio_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    
    # Save audio file
    audio_path = os.path.join(audio_dir, f"{os.path.splitext(filename)[0]}_audio.wav")
    audio_file.save(audio_path)
    
    return jsonify({'success': True, 'path': audio_path})

@app.route('/transcribe_audio', methods=['POST'])
def transcribe_audio():
    """Transcribe audio file"""
    data = request.json
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'success': False, 'error': 'No filename provided'})
    
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', f"{os.path.splitext(filename)[0]}_audio.wav")
    
    if not os.path.exists(audio_path):
        return jsonify({'success': False, 'error': 'Audio file does not exist'})
    
    try:
        # Should integrate actual speech-to-text service here
        # Currently just returns a mock result
        return jsonify({
            'success': True,
            'transcript': 'This is a mock transcription result. In actual application, you need to integrate a speech recognition service.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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