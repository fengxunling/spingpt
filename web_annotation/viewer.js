// 全局变量
let currentSession = null;
let dimensions = [0, 0, 0];
let currentIndices = [0, 0, 0];
let isRecording = false;
let annotations = [];

// DOM元素
const fileUpload = document.getElementById('fileUpload');
const loadLocalBtn = document.getElementById('loadLocalBtn');
const fileListContainer = document.getElementById('fileListContainer');
const currentFileName = document.getElementById('currentFileName');
const startRecordBtn = document.getElementById('startRecordBtn');
const stopRecordBtn = document.getElementById('stopRecordBtn');

// 视图元素
const sagittalView = document.getElementById('sagittalView');
const axialView = document.getElementById('axialView');
const coronalView = document.getElementById('coronalView');
const sagittalSlider = document.getElementById('sagittalSlider');
const axialSlider = document.getElementById('axialSlider');
const coronalSlider = document.getElementById('coronalSlider');
const sagittalIndex = document.getElementById('sagittalIndex');
const axialIndex = document.getElementById('axialIndex');
const coronalIndex = document.getElementById('coronalIndex');

// 注释元素
const annotationText = document.getElementById('annotationText');
const addAnnotationBtn = document.getElementById('addAnnotationBtn');
const annotationListContainer = document.getElementById('annotationListContainer');
const aiCommand = document.getElementById('aiCommand');
const submitAiCommand = document.getElementById('submitAiCommand');
const aiResponse = document.getElementById('aiResponse');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 加载文件列表
    fetchFileList();
    
    // 事件监听器
    fileUpload.addEventListener('change', handleFileUpload);
    loadLocalBtn.addEventListener('click', showLocalFileDialog);
    startRecordBtn.addEventListener('click', startRecording);
    stopRecordBtn.addEventListener('click', stopRecording);
    
    // 滑块事件
    sagittalSlider.addEventListener('input', () => updateSlice('sagittal', sagittalSlider.value));
    axialSlider.addEventListener('input', () => updateSlice('axial', axialSlider.value));
    coronalSlider.addEventListener('input', () => updateSlice('coronal', coronalSlider.value));
    
    // 注释事件
    addAnnotationBtn.addEventListener('click', addAnnotation);
    submitAiCommand.addEventListener('click', submitAiCommandHandler);
});

// 获取文件列表
async function fetchFileList() {
    try {
        const response = await fetch('/api/list-files');
        const data = await response.json();
        
        fileListContainer.innerHTML = '';
        data.files.forEach(file => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = file;
            li.addEventListener('click', () => loadNiftiFile(file));
            fileListContainer.appendChild(li);
        });
    } catch (error) {
        console.error('Error fetching file list:', error);
    }
}

// 处理文件上传
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/load-nifti', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        handleNiftiData(data, file.name);
    } catch (error) {
        console.error('Error uploading file:', error);
    }
}

// 加载本地NIFTI文件
async function loadNiftiFile(filePath) {
    try {
        const response = await fetch('/api/load-nifti', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ path: filePath })
        });
        
        const data = await response.json();
        handleNiftiData(data, filePath);
    } catch (error) {
        console.error('Error loading file:', error);
    }
}

// 处理NIFTI数据
function handleNiftiData(data, filename) {
    currentSession = data.session_id;
    dimensions = data.dimensions;
    currentIndices = data.current_indices;
    
    // 更新UI
    currentFileName.textContent = filename;
    
    // 设置滑块范围
    sagittalSlider.min = 0;
    sagittalSlider.max = dimensions[0] - 1;
    sagittalSlider.value = currentIndices[0];
    
    axialSlider.min = 0;
    axialSlider.max = dimensions[2] - 1;
    axialSlider.value = currentIndices[2];
    
    coronalSlider.min = 0;
    coronalSlider.max = dimensions[1] - 1;
    coronalSlider.value = currentIndices[1];
    
    // 更新索引显示
    updateIndexDisplay();
    
    // 渲染初始切片
    renderSlice(sagittalView, data.sagittal_slice);
    renderSlice(axialView, data.axial_slice);
    renderSlice(coronalView, data.coronal_slice);
}

// 更新切片
async function updateSlice(viewType, index) {
    if (!currentSession) return;
    
    try {
        const response = await fetch('/api/get-slice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSession,
                view_type: viewType,
                index: parseInt(index)
            })
        });
        
        const data = await response.json();
        
        // 更新当前索引
        if (viewType === 'sagittal') {
            currentIndices[0] = parseInt(index);
            renderSlice(sagittalView, data.slice_data);
        } else if (viewType === 'axial') {
            currentIndices[2] = parseInt(index);
            renderSlice(axialView, data.slice_data);
        } else if (viewType === 'coronal') {
            currentIndices[1] = parseInt(index);
            renderSlice(coronalView, data.slice_data);
        }
        
        // 更新索引显示
        updateIndexDisplay();
    } catch (error) {
        console.error(`Error updating ${viewType} slice:`, error);
    }
}

// 更新索引显示
function updateIndexDisplay() {
    sagittalIndex.textContent = `${currentIndices[0]}/${dimensions[0] - 1}`;
    axialIndex.textContent = `${currentIndices[2]}/${dimensions[2] - 1}`;
    coronalIndex.textContent = `${currentIndices[1]}/${dimensions[1] - 1}`;
}

// 渲染切片到Canvas
function renderSlice(canvas, sliceData) {
    const ctx = canvas.getContext('2d');
    const width = sliceData[0].length;
    const height = sliceData.length;
    
    // 创建图像数据
    const imageData = ctx.createImageData(width, height);
    
    // 填充图像数据
    let idx = 0;
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            // 归一化像素值到0-255
            const value = Math.max(0, Math.min(255, sliceData[y][x] * 255 / 1000));
            
            imageData.data[idx++] = value; // R
            imageData.data[idx++] = value; // G
            imageData.data[idx++] = value; // B
            imageData.data[idx++] = 255;   // A
        }
    }
    
    // 清除画布并绘制图像
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // 计算缩放比例以适应画布
    const scaleX = canvas.width / width;
    const scaleY = canvas.height / height;
    const scale = Math.min(scaleX, scaleY);
    
    // 创建临时画布进行缩放
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = width;
    tempCanvas.height = height;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.putImageData(imageData, 0, 0);
    
    // 在主画布上绘制缩放后的图像
    const scaledWidth = width * scale;
    const scaledHeight = height * scale;
    const offsetX = (canvas.width - scaledWidth) / 2;
    const offsetY = (canvas.height - scaledHeight) / 2;
    
    ctx.drawImage(tempCanvas, offsetX, offsetY, scaledWidth, scaledHeight);
}

// 添加注释
function addAnnotation() {
    if (!currentSession) return;
    
    const text = annotationText.value.trim();
    if (!text) return;
    
    const annotation = {
        text,
        timestamp: new Date().toISOString(),
        position: [...currentIndices],
        viewType: 'sagittal' // 默认视图类型
    };
    
    annotations.push(annotation);
    
    // 更新注释列表
    updateAnnotationList();
    
    // 清空输入框
    annotationText.value = '';
}

// 更新注释列表
function updateAnnotationList() {
    annotationListContainer.innerHTML = '';
    
    annotations.forEach((annotation, index) => {
        const li = document.createElement('li');
        li.className = 'list-group-item';
        
        const time = new Date(annotation.timestamp).toLocaleTimeString();
        li.innerHTML = `
            <strong>注释 ${index + 1}</strong> (${time})<br>
            ${annotation.text}<br>
            <small>位置: [${annotation.position.join(', ')}]</small>
        `;
        
        li.addEventListener('click', () => {
            // 点击注释时跳转到对应位置
            sagittalSlider.value = annotation.position[0];
            coronalSlider.value = annotation.position[1];
            axialSlider.value = annotation.position[2];
            
            updateSlice('sagittal', annotation.position[0]);
            updateSlice('coronal', annotation.position[1]);
            updateSlice('axial', annotation.position[2]);
        });
        
        annotationListContainer.appendChild(li);
    });
}

// 开始录制
async function startRecording() {
    if (!currentSession) return;
    
    try {
        const response = await fetch('/api/start-recording', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSession
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'recording_started') {
            isRecording = true;
            startRecordBtn.disabled = true;
            stopRecordBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error starting recording:', error);
    }
}

// 停止录制
async function stopRecording() {
    if (!isRecording) return;
    
    try {
        const response = await fetch('/api/stop-recording', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSession
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'recording_stopped') {
            isRecording = false;
            startRecordBtn.disabled = false;
            stopRecordBtn.disabled = true;
            
            // 保存注释
            saveAnnotations();
        }
    } catch (error) {
        console.error('Error stopping recording:', error);
    }
}

// 保存注释
async function saveAnnotations() {
    if (!currentSession || annotations.length === 0) return;
    
    try {
        const response = await fetch('/api/save-annotation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSession,
                annotations
            })
        });
        
        const data = await response.json();
        console.log('Annotations saved:', data);
    } catch (error) {
        console.error('Error saving annotations:', error);
    }
}

// 提交AI命令
async function submitAiCommandHandler() {
    const command = aiCommand.value.trim();
    if (!command) return;
    
    // 这里可以集成您现有的AI命令处理逻辑
    // 简单示例：解析命令中的数字和轴向
    const match = command.match(/(\d+)/);
    const axisMatch = command.match(/[xyz]/i);
    
    if (match && axisMatch) {
        const value = parseInt(match[0]);
        const axis = axisMatch[0].toLowerCase();
        
        if (axis === 'x') {
            sagittalSlider.value = value;
            updateSlice('sagittal', value);
        } else if (axis === 'y') {
            coronalSlider.value = value;
            updateSlice('coronal', value);
        } else if (axis === 'z') {
            axialSlider.value = value;
            updateSlice('axial', value);
        }
        
        aiResponse.textContent = `已将${axis.toUpperCase()}轴切片调整到${value}`;
    } else {
        aiResponse.textContent = '无法解析命令，请使用格式：调整X切片到22';
    }
    
    aiCommand.value = '';
}

// 显示本地文件对话框
function showLocalFileDialog() {
    // 这个功能在Web应用中通常需要后端支持
    // 简单实现：触发文件上传控件的点击事件
    fileUpload.click();
}