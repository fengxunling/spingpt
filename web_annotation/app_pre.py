# from flask import Flask, render_template, request, jsonify, send_from_directory
# import os
# import nibabel as nib
# import numpy as np
# from pathlib import Path
# import json
# import uuid
# import time

# app = Flask(__name__, 
#             static_folder='static',
#             template_folder='templates')

# # 确保必要的目录存在
# os.makedirs('temp', exist_ok=True)
# os.makedirs('uploads', exist_ok=True)
# os.makedirs('annotations', exist_ok=True)

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/api/load-nifti', methods=['POST'])
# def load_nifti():
#     session_id = str(uuid.uuid4())
    
#     # 处理上传的文件或本地路径
#     if 'file' in request.files:
#         file = request.files['file']
#         filename = file.filename
#         temp_path = os.path.join('uploads', f"{session_id}_{filename}")
#         file.save(temp_path)
#         file_path = temp_path
#     else:
#         file_path = request.json.get('path')
#         filename = os.path.basename(file_path)
    
#     # 加载 NIFTI 文件
#     try:
#         img = nib.load(file_path)
#         data = img.get_fdata()
        
#         # 获取中间切片作为初始视图
#         z_mid = data.shape[0] // 2
#         y_mid = data.shape[1] // 2
#         x_mid = data.shape[2] // 2
        
#         # 保存会话信息
#         session_info = {
#             'id': session_id,
#             'filename': filename,
#             'filepath': file_path,
#             'dimensions': data.shape,
#             'timestamp': time.time()
#         }
        
#         with open(os.path.join('temp', f"{session_id}.json"), 'w') as f:
#             json.dump(session_info, f)
        
#         # 返回初始数据
#         return jsonify({
#             'session_id': session_id,
#             'dimensions': data.shape,
#             'sagittal_slice': data[z_mid, :, :].tolist(),
#             'coronal_slice': data[:, y_mid, :].tolist(),
#             'axial_slice': data[:, :, x_mid].tolist(),
#             'current_indices': [z_mid, y_mid, x_mid]
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/get-slice', methods=['POST'])
# def get_slice():
#     data = request.json
#     session_id = data.get('session_id')
#     view_type = data.get('view_type')
#     index = data.get('index')
    
#     # 从会话信息获取文件路径
#     try:
#         with open(os.path.join('temp', f"{session_id}.json"), 'r') as f:
#             session_info = json.load(f)
        
#         file_path = session_info['filepath']
#         img = nib.load(file_path)
#         volume = img.get_fdata()
        
#         if view_type == 'sagittal':
#             slice_data = volume[index, :, :].tolist()
#         elif view_type == 'coronal':
#             slice_data = volume[:, index, :].tolist()
#         elif view_type == 'axial':
#             slice_data = volume[:, :, index].tolist()
        
#         return jsonify({'slice_data': slice_data})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/list-files')
# def list_files():
#     data_dir = Path('data')
#     if not data_dir.exists():
#         return jsonify({'files': []})
        
#     files = [str(f.relative_to(data_dir)) for f in data_dir.glob('**/*.nii.gz')]
#     return jsonify({'files': files})

# @app.route('/api/save-annotation', methods=['POST'])
# def save_annotation():
#     data = request.json
#     session_id = data.get('session_id')
#     annotations = data.get('annotations')
    
#     # 保存注释
#     annotation_file = os.path.join('annotations', f"{session_id}_annotations.json")
#     with open(annotation_file, 'w') as f:
#         json.dump(annotations, f)
    
#     return jsonify({'status': 'success', 'file': annotation_file})

# @app.route('/api/start-recording', methods=['POST'])
# def start_recording():
#     # 这里可以集成您现有的录制功能，但通过Web API控制
#     # 实际实现可能需要使用WebSocket或其他技术来处理长时间运行的任务
#     return jsonify({'status': 'recording_started', 'record_id': str(uuid.uuid4())})

# @app.route('/api/stop-recording', methods=['POST'])
# def stop_recording():
#     # 停止录制
#     return jsonify({'status': 'recording_stopped'})

# @app.route('/uploads/<path:filename>')
# def download_file(filename):
#     return send_from_directory('uploads', filename)

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5000)