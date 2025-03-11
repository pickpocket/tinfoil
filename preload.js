const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld(
  'api', {
    selectFile: () => ipcRenderer.invoke('select-file'),
    selectDirectory: () => ipcRenderer.invoke('select-directory'),
    selectOutputDirectory: () => ipcRenderer.invoke('select-output-directory'),
    openDirectory: (path) => ipcRenderer.invoke('open-directory', path),
    onPythonLog: (callback) => ipcRenderer.on('python-log', (_, data) => callback(data)),
    onPythonError: (callback) => ipcRenderer.on('python-error', (_, data) => callback(data)),
    onPythonExit: (callback) => ipcRenderer.on('python-exit', (_, code) => callback(code))
  }
);