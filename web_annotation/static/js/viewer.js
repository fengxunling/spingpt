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
            filename: filename,
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
            
            // 更新矢状面视图
            const sagittalImgPath = '/static/images/' + response.images[2] + '?t=' + new Date().getTime();
            $('#sagittal-image').attr('src', sagittalImgPath);
            $('#sagittal-slice-info').text(response.slice_indices[2]);
            
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
            filename: filename,
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
                formData.append('filename', filename);
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

// 获取文件名
const filename = document.querySelector('h2').textContent.replace('File: ', '');

// 矢状面视图缩放功能
$(document).ready(function() {
    const sagittalImage = document.getElementById('sagittal-image');
    let scale = 1;
    let isDragging = false;
    let startX, startY, translateX = 0, translateY = 0;
    
    // 缩放功能
    $('#zoom-in').on('click', function() {
        scale *= 1.2;
        updateTransform();
    });
    
    $('#zoom-out').on('click', function() {
        scale /= 1.2;
        if (scale < 0.1) scale = 0.1;
        updateTransform();
    });
    
    $('#reset-zoom').on('click', function() {
        scale = 1;
        translateX = 0;
        translateY = 0;
        updateTransform();
    });
    
    function updateTransform() {
        sagittalImage.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    }
    
    // 拖动功能
    sagittalImage.addEventListener('mousedown', function(e) {
        isDragging = true;
        startX = e.clientX - translateX;
        startY = e.clientY - translateY;
        sagittalImage.style.cursor = 'grabbing';
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        translateX = e.clientX - startX;
        translateY = e.clientY - startY;
        updateTransform();
    });
    
    document.addEventListener('mouseup', function() {
        isDragging = false;
        sagittalImage.style.cursor = 'move';
    });
    
    // 鼠标滚轮缩放
    document.getElementById('sagittal-view').addEventListener('wheel', function(e) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        scale *= delta;
        if (scale < 0.1) scale = 0.1;
        updateTransform();
    });
    
    // 初始化
    sagittalImage.style.cursor = 'move';
});

// 在适当的位置添加以下代码

// 截图功能
function captureScreenshot() {
    const sagittalView = document.getElementById('sagittal-view');
    const sagittalImage = sagittalView.querySelector('img');
    
    // 创建一个新的canvas元素
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // 设置canvas大小为当前视图大小
    canvas.width = sagittalView.clientWidth;
    canvas.height = sagittalView.clientHeight;
    
    // 绘制当前视图到canvas
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // 获取图像的当前变换
    const transform = sagittalImage.style.transform;
    
    // 临时应用变换到canvas上下文
    ctx.save();
    
    // 计算中心点
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    
    // 应用当前的缩放和平移
    ctx.translate(centerX, centerY);
    
    // 从transform字符串中提取缩放和平移值
    let scale = 1;
    let translateX = 0;
    let translateY = 0;
    
    if (transform) {
        const scaleMatch = transform.match(/scale\(([^)]+)\)/);
        if (scaleMatch && scaleMatch[1]) {
            scale = parseFloat(scaleMatch[1]);
        }
        
        const translateMatch = transform.match(/translate\(([^,]+),\s*([^)]+)\)/);
        if (translateMatch && translateMatch[1] && translateMatch[2]) {
            translateX = parseFloat(translateMatch[1]);
            translateY = parseFloat(translateMatch[2]);
        }
    }
    
    ctx.scale(scale, scale);
    ctx.translate(translateX / scale, translateY / scale);
    
    // 绘制图像
    ctx.drawImage(sagittalImage, -sagittalImage.width / 2, -sagittalImage.height / 2);
    
    // 恢复上下文
    ctx.restore();
    
    // 将canvas转换为图像数据
    const imageData = canvas.toDataURL('image/png');
    
    // 发送到服务器保存
    saveScreenshot(imageData);
}

// 保存截图到服务器
function saveScreenshot(imageData) {
    fetch('/save_screenshot', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            image: imageData,
            filename: currentFilename,
            view_type: 'sagittal'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showScreenshotSaved(data.path);
            // 更新截图列表
            loadSavedScreenshots();
        } else {
            alert('截图保存失败: ' + data.error);
        }
    })
    .catch(error => {
        console.error('截图保存错误:', error);
        alert('截图保存出错，请查看控制台');
    });
}

// 显示截图已保存的提示
function showScreenshotSaved(imagePath) {
    const notification = document.createElement('div');
    notification.className = 'screenshot-notification';
    notification.innerHTML = `
        <p>截图已保存!</p>
        <img src="${imagePath}" alt="Saved Screenshot" width="150">
        <button id="add-audio-btn" data-screenshot="${imagePath.split('/').pop()}">添加音频注释</button>
    `;
    
    document.body.appendChild(notification);
    
    // 添加事件监听器
    notification.querySelector('#add-audio-btn').addEventListener('click', function() {
        const screenshotFilename = this.getAttribute('data-screenshot');
        showAudioAnnotationDialog(screenshotFilename);
        notification.remove();
    });
    
    // 5秒后自动关闭
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// 显示音频注释对话框
function showAudioAnnotationDialog(screenshotFilename) {
    // 创建对话框
    const dialog = document.createElement('div');
    dialog.className = 'audio-annotation-dialog';
    dialog.innerHTML = `
        <h3>为截图添加音频注释</h3>
        <img src="/static/screenshots/${screenshotFilename}" alt="Screenshot" width="200">
        <div class="audio-controls">
            <button id="start-recording">开始录音</button>
            <button id="stop-recording" disabled>停止录音</button>
            <div id="recording-status"></div>
        </div>
        <div class="audio-playback" style="display:none">
            <audio id="audio-playback" controls></audio>
        </div>
        <div class="annotation-text">
            <textarea id="annotation-text" placeholder="添加文字注释（可选）"></textarea>
        </div>
        <div class="dialog-buttons">
            <button id="save-annotation">保存注释</button>
            <button id="cancel-annotation">取消</button>
        </div>
    `;
    
    document.body.appendChild(dialog);
    
    // 录音相关变量
    let mediaRecorder;
    let audioChunks = [];
    let audioBlob;
    
    // 添加事件监听器
    const startRecordingBtn = dialog.querySelector('#start-recording');
    const stopRecordingBtn = dialog.querySelector('#stop-recording');
    const recordingStatus = dialog.querySelector('#recording-status');
    const audioPlayback = dialog.querySelector('.audio-playback');
    const audioPlayer = dialog.querySelector('#audio-playback');
    const saveAnnotationBtn = dialog.querySelector('#save-annotation');
    const cancelAnnotationBtn = dialog.querySelector('#cancel-annotation');
    
    // 开始录音
    startRecordingBtn.addEventListener('click', function() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.addEventListener('dataavailable', event => {
                    audioChunks.push(event.data);
                });
                
                mediaRecorder.addEventListener('stop', () => {
                    audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    audioPlayer.src = audioUrl;
                    audioPlayback.style.display = 'block';
                    recordingStatus.textContent = '录音完成';
                });
                
                mediaRecorder.start();
                startRecordingBtn.disabled = true;
                stopRecordingBtn.disabled = false;
                recordingStatus.textContent = '正在录音...';
            })
            .catch(error => {
                console.error('获取麦克风失败:', error);
                recordingStatus.textContent = '无法访问麦克风';
            });
    });
    
    // 停止录音
    stopRecordingBtn.addEventListener('click', function() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
            startRecordingBtn.disabled = false;
            stopRecordingBtn.disabled = true;
        }
    });
    
    // 保存注释
    saveAnnotationBtn.addEventListener('click', function() {
        if (!audioBlob) {
            alert('请先录制音频');
            return;
        }
        
        // 创建FormData对象上传音频
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        formData.append('filename', currentFilename);
        
        // 上传音频文件
        fetch('/upload_audio', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 关联音频与截图
                const annotationText = dialog.querySelector('#annotation-text').value;
                
                fetch('/associate_audio_with_image', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        screenshot_filename: screenshotFilename,
                        audio_filename: data.filename,
                        annotation_text: annotationText
                    })
                })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        alert('音频注释已保存');
                        dialog.remove();
                        // 更新注释列表
                        loadAnnotations();
                    } else {
                        alert('保存注释关联失败: ' + result.error);
                    }
                });
            } else {
                alert('上传音频失败: ' + data.error);
            }
        })
        .catch(error => {
            console.error('上传音频错误:', error);
            alert('上传音频出错，请查看控制台');
        });
    });
    
    // 取消
    cancelAnnotationBtn.addEventListener('click', function() {
        dialog.remove();
    });
}

// 加载已保存的注释
function loadAnnotations() {
    fetch(`/get_annotations?filename=${encodeURIComponent(currentFilename)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayAnnotations(data.annotations);
            }
        })
        .catch(error => {
            console.error('加载注释错误:', error);
        });
}

// 显示注释列表
function displayAnnotations(annotations) {
    const annotationsContainer = document.getElementById('annotations-container');
    if (!annotationsContainer) {
        // 创建注释容器
        const container = document.createElement('div');
        container.id = 'annotations-container';
        container.className = 'annotations-container';
        container.innerHTML = '<h3>已保存的注释</h3><div class="annotations-list"></div>';
        document.querySelector('.viewer-container').appendChild(container);
        annotationsContainer = container;
    }
    
    const annotationsList = annotationsContainer.querySelector('.annotations-list');
    annotationsList.innerHTML = '';
    
    if (annotations.length === 0) {
        annotationsList.innerHTML = '<p>暂无注释</p>';
        return;
    }
    
    annotations.forEach(annotation => {
        const annotationItem = document.createElement('div');
        annotationItem.className = 'annotation-item';
        annotationItem.innerHTML = `
            <div class="annotation-image">
                <img src="/static/screenshots/${annotation.screenshot}" alt="Screenshot" width="100">
            </div>
            <div class="annotation-content">
                <div class="annotation-audio">
                    <audio controls src="/static/audio/${annotation.audio}"></audio>
                </div>
                <div class="annotation-text">${annotation.text || '无文字注释'}</div>
                <div class="annotation-timestamp">${new Date(annotation.timestamp).toLocaleString()}</div>
            </div>
        `;
        annotationsList.appendChild(annotationItem);
    });
}

// 在页面加载完成后添加截图按钮
document.addEventListener('DOMContentLoaded', function() {
    // 添加截图按钮到矢状面视图
    const sagittalControls = document.createElement('div');
    sagittalControls.className = 'sagittal-controls';
    sagittalControls.innerHTML = `
        <button id="capture-screenshot" title="截图">📷 截图</button>
    `;
    
    const sagittalView = document.getElementById('sagittal-view');
    if (sagittalView) {
        sagittalView.appendChild(sagittalControls);
        
        // 添加事件监听器
        document.getElementById('capture-screenshot').addEventListener('click', captureScreenshot);
    }
    
    // 加载已保存的注释
    loadAnnotations();
});