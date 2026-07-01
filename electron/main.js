const { app, BrowserWindow, Menu, dialog, shell } = require('electron');
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

// ---------- app menu ----------
function buildMenu() {
  const template = [
    {
      label: 'AniFlow',
      submenu: [
        { role: 'about', label: '关于 AniFlow' },
        { type: 'separator' },
        { role: 'quit', label: '退出' }
      ]
    },
    {
      label: '编辑',
      submenu: [
        { role: 'undo', label: '撤销' },
        { role: 'redo', label: '重做' },
        { type: 'separator' },
        { role: 'cut', label: '剪切' },
        { role: 'copy', label: '复制' },
        { role: 'paste', label: '粘贴' }
      ]
    },
    {
      label: '视图',
      submenu: [
        { role: 'reload', label: '刷新' },
        { role: 'toggleDevTools', label: '开发者工具' },
        { type: 'separator' },
        { role: 'resetZoom', label: '重置缩放' },
        { role: 'zoomIn', label: '放大' },
        { role: 'zoomOut', label: '缩小' }
      ]
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '日志目录',
          click: async () => {
            const logsDir = path.join(getAppDir(), 'logs');
            if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });
            shell.openPath(logsDir);
          }
        },
        { type: 'separator' },
        {
          label: '关于',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: '关于 AniFlow',
              message: 'AniFlow v1.1.0',
              detail: '游戏自动化调度工具\n支持绝区零和终末地的自动化任务管理'
            });
          }
        }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ---------- app lifecycle ----------
app.whenReady().then(async () => {
  buildMenu();

  try {
    const port = await startPythonServer();
    await waitForServer(port);

    const savedState = loadWindowState();

    mainWindow = new BrowserWindow({
      width: savedState?.width || 1100,
      height: savedState?.height || 700,
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
