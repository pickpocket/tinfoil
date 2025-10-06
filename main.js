const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const isDev = require('electron-is-dev');
const fs = require('fs');

let mainWindow;
let pythonProcess;


const CSP_POLICY = [
    "default-src 'self'",
    "script-src 'self' https://cdn.tailwindcss.com 'sha256-fRVfnfDL9LIOevIoXS0QI4NLL1kAzWBpi9CczgchrHI=' 'sha256-G4xQKrMSKLqp+N97FjBZxb5nyq0eMf2P9xZFNaNVi+M='",
    "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com",
    "img-src 'self' data: blob:",
    "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000"
].join('; ');

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true,
            webSecurity: true,
            allowRunningInsecureContent: false,
            preload: path.join(__dirname, 'preload.js')
        }
    });

    mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
        callback({
            responseHeaders: {
                ...details.responseHeaders,
                'Content-Security-Policy': [CSP_POLICY]
            }
        });
    });

    mainWindow.loadFile(path.join(__dirname, 'public', 'tailwind-app.html'));

    if (isDev) {
        mainWindow.webContents.openDevTools();
    }

    startPythonBackend();
}

function startPythonBackend() {
    const pythonPath = isDev 
        ? 'python' 
        : path.join(process.resourcesPath, 'python', 'tinfoil', 'venv', 'bin', 'python');
    
    // Define the base directory for Python
    const pythonBaseDir = isDev
        ? path.join(__dirname, 'python')
        : path.join(process.resourcesPath, 'python');

    // The script path is now relative to the base directory
    const scriptPath = path.join('app', 'main.py');
    
    if (!fs.existsSync(path.join(pythonBaseDir, scriptPath))) {
        console.error('Python script not found:', path.join(pythonBaseDir, scriptPath));
        return;
    }

    // Pass the cwd (current working directory) option to spawn
    pythonProcess = spawn(pythonPath, [scriptPath], {
        cwd: pythonBaseDir
    });
    
    if (!pythonProcess || !pythonProcess.pid) {
        console.error('Failed to start Python process');
        return;
    }

    // ... (the rest of the function remains the same)
    // pythonProcess.stdout.on(...);
    // pythonProcess.stderr.on(...);
    // etc.
}
function validatePath(filePath) {
    if (typeof filePath !== 'string') return false;
    if (filePath.includes('..')) return false;
    if (filePath.length > 4096) return false;
    return true;
}

ipcMain.handle('select-file', async () => {
    if (!mainWindow || mainWindow.isDestroyed()) {
        return [];
    }

    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile'],
        filters: [
            { name: 'Audio Files', extensions: ['flac'] }
        ]
    });
    
    return result.filePaths || [];
});

ipcMain.handle('select-directory', async () => {
    if (!mainWindow || mainWindow.isDestroyed()) {
        return [];
    }

    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory']
    });
    
    return result.filePaths || [];
});

ipcMain.handle('select-output-directory', async () => {
    if (!mainWindow || mainWindow.isDestroyed()) {
        return [];
    }

    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory', 'createDirectory']
    });
    
    return result.filePaths || [];
});

ipcMain.handle('open-directory', async (_, dirPath) => {
    if (!validatePath(dirPath)) {
        return false;
    }

    if (!fs.existsSync(dirPath)) {
        return false;
    }

    const stats = fs.statSync(dirPath);
    if (!stats.isDirectory()) {
        return false;
    }

    await shell.openPath(dirPath);
    return true;
});

app.on('ready', createWindow);

app.on('window-all-closed', () => {
    if (pythonProcess && pythonProcess.pid) {
        pythonProcess.kill('SIGTERM');
    }
    
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (mainWindow === null) {
        createWindow();
    }
});

app.on('will-quit', () => {
    if (pythonProcess && pythonProcess.pid) {
        pythonProcess.kill('SIGTERM');
    }
});