const { contextBridge, ipcRenderer } = require('electron')

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  openFileDialog: () => ipcRenderer.invoke('open-file-dialog'),
  readNiftiFile: (filePath) => ipcRenderer.invoke('read-nifti-file', filePath)
})