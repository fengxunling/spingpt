const { app, BrowserWindow, ipcMain, dialog } = require('electron/main')
const path = require('path')
const fs = require('fs')

// 保存对主窗口的引用
let mainWindow

const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 1024,
    height: 768,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: true,
      contextIsolation: false
    }
  })

  mainWindow.loadFile('index.html')
  
  // 可选：打开开发者工具
  // mainWindow.webContents.openDevTools()
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
  
  // 设置IPC通信处理文件操作
  ipcMain.handle('open-file-dialog', async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: [{ name: 'NIfTI Files', extensions: ['nii', 'nii.gz'] }]
    })
    if (!canceled && filePaths.length > 0) {
      return filePaths[0]
    }
    return null
  })
  
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})