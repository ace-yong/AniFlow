const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');

let mainWindow;
let pythonProcess;

// ---------- window state persistence ----------
const statePath = path.join(app.getPath('userData'), 'window-state.json');

function loadWindowState() {
  try {
    if (fs.existsSync(statePath)) {
      return JSON.parse(fs.readFileSync(statePath, 'utf-8'));
    }
  } catch (_) {}
  return null;
}

function saveWindowState(win) {
  try {
    const bounds = win.getBounds();
    const maximized = win.isMaximized();
    fs.writeFileSync(statePath, JSON.stringify({ ...bounds, maximized }), 'utf-8');
  } catch (_) {}
}

// ---------- Python server ----------
function getResourcePath(relativePath) {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, relativePath);
  }
  return path.join(__dirname, '..', relativePath);
}

function getAppDir() {
  if (app.isPackaged) {
    return process.resourcesPath;
  }
  return path.join(__dirname, '..');
}

function startPythonServer() {
  return new Promise((resolve, reject) => {
    const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
    const scriptPath = getResourcePath('gui_server.py');

    pythonProcess = spawn(pythonPath, [scriptPath], {
      cwd: getAppDir(),
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let portData = '';
    pythonProcess.stdout.on('data', (data) => {
      portData += data.toString();
      const port = parseInt(portData.trim());
      if (!isNaN(port)) {
        resolve(port);
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`Python: ${data}`);
    });

    pythonProcess.on('error', (err) => {
      dialog.showErrorBox('启动失败', `无法启动 Python 服务器:\n${err.message}\n\n请确保已安装 Python 3。`);
      reject(err);
    });

    pythonProcess.on('exit', (code) => {
      if (code !== 0) {
        dialog.showErrorBox('Python 退出', `Python 进程异常退出 (code: ${code})`);
      }
    });

    setTimeout(() => reject(new Error('Python 服务器启动超时')), 10000);
  });
}

function waitForServer(port) {
  return new Promise((resolve) => {
    const check = () => {
      http.get(`http://127.0.0.1:${port}/api/getVersion`, (res) => {
        resolve();
      }).on('error', () => {
        setTimeout(check, 200);
      });
    };
    check();
  });
}



// ---------- app lifecycle ----------
app.whenReady().then(async () => {
  try {
    const port = await startPythonServer();
    await waitForServer(port);

    const savedState = loadWindowState();

    mainWindow = new BrowserWindow({
      width: savedState?.width || 1400,
      height: savedState?.height || 900,
      x: savedState?.x,
      y: savedState?.y,
      title: 'AniFlow',
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, 'preload.js')
      }
    });

    if (savedState?.maximized) {
      mainWindow.maximize();
    }

    mainWindow.on('resize', () => saveWindowState(mainWindow));
    mainWindow.on('move', () => saveWindowState(mainWindow));
    mainWindow.on('close', () => saveWindowState(mainWindow));

    mainWindow.loadURL(`http://127.0.0.1:${port}/index.html`);
  } catch (err) {
    dialog.showErrorBox('启动失败', err.message);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
});
