const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const isDev = require('electron-is-dev');
const fs = require('fs');

let mainWindow;
let pythonProcess;

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Only load the HTML file - no React
  mainWindow.loadFile(path.join(__dirname, 'public', 'tailwind-app.html'));

  // Open DevTools
  mainWindow.webContents.openDevTools();

  // Start Python backend
  startPythonBackend();
}

function startPythonBackend() {
  // Determine the path to the Python executable and script
  const pythonPath = isDev 
    ? 'python' // Use system Python in dev
    : path.join(process.resourcesPath, 'python', 'tinfoil', 'venv', 'bin', 'python');
  
  const scriptPath = isDev
    ? path.join(__dirname, 'python', 'tinfoil.py')
    : path.join(process.resourcesPath, 'python', 'tinfoil.py');

  // Start the Python API server
  pythonProcess = spawn(pythonPath, [scriptPath, '--api']);

  pythonProcess.stdout.on('data', (data) => {
    console.log(`Python stdout: ${data}`);
    if (mainWindow) {
      mainWindow.webContents.send('python-log', data.toString());
    }
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python stderr: ${data}`);
    if (mainWindow) {
      mainWindow.webContents.send('python-error', data.toString());
    }
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
    if (mainWindow) {
      mainWindow.webContents.send('python-exit', code);
    }
  });
}

// IPC handlers for file operations
ipcMain.handle('select-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: 'Audio Files', extensions: ['flac'] }
    ]
  });
  return result.filePaths;
});

ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });
  return result.filePaths;
});

ipcMain.handle('select-output-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory']
  });
  return result.filePaths;
});

ipcMain.handle('open-directory', async (_, dirPath) => {
  const { shell } = require('electron');
  await shell.openPath(dirPath);
  return true;
});

app.on('ready', createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
  
  if (pythonProcess) {
    pythonProcess.kill();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});