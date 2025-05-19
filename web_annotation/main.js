const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { PythonShell } = require('python-shell');
const fs = require('fs');
const { spawn } = require('child_process');

// 保存Python进程的引用
let pyProc = null;
let mainWindow = null;
let serverRunning = false;
let serverPort = 5000;

// 检查端口是否可用
function isPortAvailable(port) {
  return new Promise((resolve) => {
    const net = require('net');
    const tester = net.createServer()
      .once('error', () => resolve(false))
      .once('listening', () => {
        tester.close();
        resolve(true);
      })
      .listen(port);
  });
}

// 查找可用端口
async function findAvailablePort(startPort) {
  let port = startPort;
  while (!(await isPortAvailable(port))) {
    port++;
    if (port > startPort + 100) {
      throw new Error('无法找到可用端口');
    }
  }
  return port;
}

// 启动Flask服务器
async function startPythonServer() {
  if (serverRunning) return;

  try {
    // 查找可用端口
    serverPort = await findAvailablePort(5000);
    
    const scriptPath = path.join(__dirname, 'test_app.py');
    
    // 检查Python脚本是否存在
    if (!fs.existsSync(scriptPath)) {
      dialog.showErrorBox('错误', `找不到Python脚本: ${scriptPath}`);
      app.quit();
      return;
    }

    // 启动Python进程
    pyProc = spawn('python', [scriptPath], {
      env: { ...process.env, FLASK_PORT: serverPort.toString() }
    });

    pyProc.stdout.on('data', (data) => {
      console.log(`Python输出: ${data}`);
      if (data.toString().includes('Running on')) {
        serverRunning = true;
        createWindow();
      }
    });

    pyProc.stderr.on('data', (data) => {
      console.error(`Python错误: ${data}`);
    });

    pyProc.on('close', (code) => {
      console.log(`Python进程退出，代码: ${code}`);
      serverRunning = false;
      pyProc = null;
    });

    // 设置超时，如果服务器在指定时间内没有启动，则创建窗口
    setTimeout(() => {
      if (!serverRunning) {
        console.log('服务器启动超时，尝试创建窗口');
        serverRunning = true; // 假设服务器已启动
        createWindow();
      }
    }, 5000);
  } catch (error) {
    console.error('启动Python服务器时出错:', error);
    dialog.showErrorBox('错误', `启动服务器失败: ${error.message}`);
    app.quit();
  }
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'static/icon.ico')
  });

  // 加载Flask应用
  mainWindow.loadURL(`http://localhost:${serverPort}/`);
  
  // 打开开发者工具（开发时使用，发布时可注释掉）
  // mainWindow.webContents.openDevTools();

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 当Electron完成初始化时
app.whenReady().then(() => {
  startPythonServer();
});

// 当所有窗口关闭时退出应用
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// 应用退出前清理
app.on('before-quit', () => {
  if (pyProc) {
    // 在Windows上使用taskkill强制终止进程
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', pyProc.pid, '/f', '/t']);
    } else {
      pyProc.kill();
    }
    pyProc = null;
  }
});