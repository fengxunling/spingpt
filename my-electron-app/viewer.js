// NIfTI文件查看器实现
document.addEventListener('DOMContentLoaded', function() {
    // 从localStorage获取文件信息
    const fileName = localStorage.getItem('selectedFileName');
    const filePath = localStorage.getItem('selectedFilePath');
    
    if (fileName) {
        document.getElementById('filename').textContent = `File: ${fileName}`;
        loadNiftiFile(filePath);
    } else {
        alert('No file selected. Please go back and select a file.');
    }
});

// 全局变量
let niftiHeader = null;
let niftiImage = null;
let scene, camera, renderer, controls;
let axialCanvas, sagittalCanvas, coronalCanvas;
let axialCtx, sagittalCtx, coronalCtx;
let sliceX, sliceY, sliceZ;
let sliceXMax, sliceYMax, sliceZMax;

// 加载NIfTI文件
function loadNiftiFile(filePath) {
    const fs = require('fs');
    
    // 显示加载指示器
    document.getElementById('loading-indicator').style.display = 'block';
    
    // 读取文件
    fs.readFile(filePath, function(err, data) {
        if (err) {
            console.error('Error reading file:', err);
            alert('Error reading file: ' + err.message);
            return;
        }
        
        // 解析NIfTI文件
        const buffer = new Uint8Array(data).buffer;
        const niftiReader = new NiftiReader();
        
        try {
            if (niftiReader.isNIFTI(buffer)) {
                niftiHeader = niftiReader.readHeader(buffer);
                niftiImage = niftiReader.readImage(niftiHeader, buffer);
                
                // 设置切片滑块的范围
                sliceXMax = niftiHeader.dims[1] - 1;
                sliceYMax = niftiHeader.dims[2] - 1;
                sliceZMax = niftiHeader.dims[3] - 1;
                
                const sliceXSlider = document.getElementById('slice-x');
                const sliceYSlider = document.getElementById('slice-y');
                const sliceZSlider = document.getElementById('slice-z');
                
                sliceXSlider.max = sliceXMax;
                sliceYSlider.max = sliceYMax;
                sliceZSlider.max = sliceZMax;
                
                sliceXSlider.value = Math.floor(sliceXMax / 2);
                sliceYSlider.value = Math.floor(sliceYMax / 2);
                sliceZSlider.value = Math.floor(sliceZMax / 2);
                
                document.getElementById('slice-x-value').textContent = sliceXSlider.value;
                document.getElementById('slice-y-value').textContent = sliceYSlider.value;
                document.getElementById('slice-z-value').textContent = sliceZSlider.value;
                
                // 初始化3D场景和2D切片视图
                initScene();
                initCanvases();
                
                // 更新切片视图
                sliceX = parseInt(sliceXSlider.value);
                sliceY = parseInt(sliceYSlider.value);
                sliceZ = parseInt(sliceZSlider.value);
                updateSlices();
                
                // 添加滑块事件监听器
                sliceXSlider.addEventListener('input', function() {
                    document.getElementById('slice-x-value').textContent = this.value;
                    sliceX = parseInt(this.value);
                    updateSlices();
                });
                
                sliceYSlider.addEventListener('input', function() {
                    document.getElementById('slice-y-value').textContent = this.value;
                    sliceY = parseInt(this.value);
                    updateSlices();
                });
                
                sliceZSlider.addEventListener('input', function() {
                    document.getElementById('slice-z-value').textContent = this.value;
                    sliceZ = parseInt(this.value);
                    updateSlices();
                });
                
                // 隐藏加载指示器
                document.getElementById('loading-indicator').style.display = 'none';
            } else {
                alert('Not a valid NIfTI file');
            }
        } catch (error) {
            console.error('Error parsing NIfTI file:', error);
            alert('Error parsing NIfTI file: ' + error.message);
        }
    });
}

// 初始化Three.js场景
function initScene() {
    // 创建场景
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);
    
    // 创建相机
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5;
    
    // 创建渲染器
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth / 2, window.innerHeight / 2);
    document.getElementById('3d-container').appendChild(renderer.domElement);
    
    // 添加轨道控制
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.25;
    
    // 创建3D体积渲染
    createVolumeRendering();
    
    // 添加光源
    const ambientLight = new THREE.AmbientLight(0x404040);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
    directionalLight.position.set(1, 1, 1);
    scene.add(directionalLight);
    
    // 动画循环
    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    
    animate();
    
    // 窗口大小调整
    window.addEventListener('resize', function() {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth / 2, window.innerHeight / 2);
    });
}

// 创建体积渲染
function createVolumeRendering() {
    if (!niftiHeader || !niftiImage) return;
    
    // 清除现有的对象
    while (scene.children.length > 0) {
        scene.remove(scene.children[0]);
    }
    
    // 创建几何体
    const geometry = new THREE.BoxGeometry(1, 1, 1);
    const material = new THREE.MeshBasicMaterial({ color: 0x00ff00, wireframe: true });
    const cube = new THREE.Mesh(geometry, material);
    scene.add(cube);
    
    // 这里可以实现更复杂的体积渲染
    // 例如使用点云或体素渲染技术
    // 但这需要更复杂的实现，超出了基本示例的范围
}

// 初始化2D切片画布
function initCanvases() {
    axialCanvas = document.getElementById('axial-canvas');
    sagittalCanvas = document.getElementById('sagittal-canvas');
    coronalCanvas = document.getElementById('coronal-canvas');
    
    // 设置画布大小
    const canvasSize = 256;
    axialCanvas.width = canvasSize;
    axialCanvas.height = canvasSize;
    sagittalCanvas.width = canvasSize;
    sagittalCanvas.height = canvasSize;
    coronalCanvas.width = canvasSize;
    coronalCanvas.height = canvasSize;
    
    // 获取2D上下文
    axialCtx = axialCanvas.getContext('2d');
    sagittalCtx = sagittalCanvas.getContext('2d');
    coronalCtx = coronalCanvas.getContext('2d');
}

// 更新切片视图
function updateSlices() {
    if (!niftiHeader || !niftiImage) return;
    
    // 绘制轴向切片 (Axial - XY平面)
    drawSlice(axialCtx, 'axial', sliceZ);
    
    // 绘制矢状切片 (Sagittal - YZ平面)
    drawSlice(sagittalCtx, 'sagittal', sliceX);
    
    // 绘制冠状切片 (Coronal - XZ平面)
    drawSlice(coronalCtx, 'coronal', sliceY);
}

// 绘制单个切片
function drawSlice(ctx, sliceType, sliceIndex) {
    const width = niftiHeader.dims[1]; // X维度
    const height = niftiHeader.dims[2]; // Y维度
    const depth = niftiHeader.dims[3]; // Z维度
    
    // 创建图像数据
    const imageData = ctx.createImageData(ctx.canvas.width, ctx.canvas.height);
    const data = imageData.data;
    
    // 根据切片类型获取数据
    let sliceData;
    let sliceWidth, sliceHeight;
    
    if (sliceType === 'axial') {
        // XY平面
        sliceWidth = width;
        sliceHeight = height;
        sliceData = new Float32Array(sliceWidth * sliceHeight);
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const index = x + y * width + sliceIndex * width * height;
                sliceData[x + y * width] = niftiImage[index];
            }
        }
    } else if (sliceType === 'sagittal') {
        // YZ平面
        sliceWidth = depth;
        sliceHeight = height;
        sliceData = new Float32Array(sliceWidth * sliceHeight);
        
        for (let z = 0; z < depth; z++) {
            for (let y = 0; y < height; y++) {
                const index = sliceIndex + y * width + z * width * height;
                sliceData[z + y * depth] = niftiImage[index];
            }
        }
    } else if (sliceType === 'coronal') {
        // XZ平面
        sliceWidth = width;
        sliceHeight = depth;
        sliceData = new Float32Array(sliceWidth * sliceHeight);
        
        for (let z = 0; z < depth; z++) {
            for (let x = 0; x < width; x++) {
                const index = x + sliceIndex * width + z * width * height;
                sliceData[x + z * width] = niftiImage[index];
            }
        }
    }
    
    // 找到数据范围
    let min = Infinity;
    let max = -Infinity;
    
    for (let i = 0; i < sliceData.length; i++) {
        if (sliceData[i] < min) min = sliceData[i];
        if (sliceData[i] > max) max = sliceData[i];
    }
    
    // 归一化并绘制图像
    const range = max - min;
    const scale = ctx.canvas.width / sliceWidth;
    
    for (let y = 0; y < ctx.canvas.height; y++) {
        for (let x = 0; x < ctx.canvas.width; x++) {
            const sourceX = Math.floor(x / scale);
            const sourceY = Math.floor(y / scale);
            
            if (sourceX < sliceWidth && sourceY < sliceHeight) {
                const value = sliceData[sourceX + sourceY * sliceWidth];
                const normalizedValue = (value - min) / range;
                const intensity = Math.floor(normalizedValue * 255);
                
                const pixelIndex = (y * ctx.canvas.width + x) * 4;
                data[pixelIndex] = intensity;     // R
                data[pixelIndex + 1] = intensity; // G
                data[pixelIndex + 2] = intensity; // B
                data[pixelIndex + 3] = 255;       // A
            }
        }
    }
    
    ctx.putImageData(imageData, 0, 0);
}