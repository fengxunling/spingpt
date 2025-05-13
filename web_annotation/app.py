from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# 确保上传目录存在
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': '没有文件部分'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'})
        
        if file:
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            return jsonify({'success': True, 'filename': file.filename})
    
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
        </style>
    </head>
    <body>
        <h1>医学影像上传系统</h1>
        <div class="upload-container">
            <p>请选择您要上传的医学影像文件</p>
            <form method="post" enctype="multipart/form-data">
                <div class="file-input">
                    <input type="file" name="file" id="file">
                </div>
                <button type="submit" class="upload-btn">上传文件</button>
            </form>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True)