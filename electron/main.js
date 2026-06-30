const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow;
let pythonProcess;

function startPythonServer() {
  return new Promise((resolve, reject) => {
    const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
    const scriptPath = path.join(__dirname, '..', 'gui_server.py');
    
    pythonProcess = spawn(pythonPath, [scriptPath], {
      cwd: path.join(__dirname, '..'),
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

app.whenReady().then(async () => {
  try {
    const port = await startPythonServer();
    await waitForServer(port);
    
    mainWindow = new BrowserWindow({
      width: 1100,
      height: 700,
      title: 'AniFlow',
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true
      }
    });

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
