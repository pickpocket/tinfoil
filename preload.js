const { contextBridge, ipcRenderer } = require('electron');

const MAX_LISTENERS = 10;
let logListenerCount = 0;
let errorListenerCount = 0;
let exitListenerCount = 0;

function validateString(value, maxLength = 4096) {
    return typeof value === 'string' && 
           value.length > 0 && 
           value.length <= maxLength;
}

function validatePath(path) {
    return validateString(path) && !path.includes('..');
}

contextBridge.exposeInMainWorld('api', {
    selectFile: () => {
        return ipcRenderer.invoke('select-file');
    },
    
    selectDirectory: () => {
        return ipcRenderer.invoke('select-directory');
    },
    
    selectOutputDirectory: () => {
        return ipcRenderer.invoke('select-output-directory');
    },
    
    openDirectory: (path) => {
        if (!validatePath(path)) {
            return Promise.reject(new Error('Invalid path'));
        }
        return ipcRenderer.invoke('open-directory', path);
    },
    
    onPythonLog: (callback) => {
        if (typeof callback !== 'function') {
            return;
        }
        if (logListenerCount >= MAX_LISTENERS) {
            return;
        }
        logListenerCount++;
        ipcRenderer.on('python-log', (_, data) => callback(data));
    },
    
    onPythonError: (callback) => {
        if (typeof callback !== 'function') {
            return;
        }
        if (errorListenerCount >= MAX_LISTENERS) {
            return;
        }
        errorListenerCount++;
        ipcRenderer.on('python-error', (_, data) => callback(data));
    },
    
    onPythonExit: (callback) => {
        if (typeof callback !== 'function') {
            return;
        }
        if (exitListenerCount >= MAX_LISTENERS) {
            return;
        }
        exitListenerCount++;
        ipcRenderer.on('python-exit', (_, code) => callback(code));
    }
});