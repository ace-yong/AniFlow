#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Headless HTTP server for Electron frontend"""
import sys, os, json, threading, socketserver, http.server, queue, time
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
from process_manager import ProcessManager

VERSION = "1.1.0"

# ---------- scan utilities ----------
def _get_drives():
    drives = []
    if os.name == 'nt':
        import string
        try:
            from ctypes import windll
            bitmask = windll.kernel32.GetLogicalDrives()
            for i, letter in enumerate(string.ascii_uppercase):
                if bitmask & (1 << i):
                    drives.append(f'{letter}:\\')
            drives.reverse()
        except Exception:
            drives = ['C:\\', 'D:\\', 'E:\\', 'F:\\']
    else:
        drives = ['/', '/home', '/opt']
    return drives

def _search_deep(roots, targets, max_depth=2):
    from collections import deque
    for root in roots:
        if not os.path.isdir(root):
            continue
        q = deque([(root, 0)])
        while q:
            dirpath, depth = q.popleft()
            if depth > max_depth:
                continue
            try:
                for name in os.listdir(dirpath):
                    full = os.path.join(dirpath, name)
                    if os.path.isfile(full) and name in targets:
                        return full
                    if os.path.isdir(full):
                        q.append((full, depth + 1))
            except OSError:
                continue
    return ''

def _detect_od_path(drives=None):
    if drives is None:
        drives = _get_drives()
    from collections import deque
    roots = list(drives) + [os.path.expanduser('~')]
    for root in roots:
        if not os.path.isdir(root):
            continue
        q = deque([(root, 0)])
        while q:
            dirpath, depth = q.popleft()
            if depth > 2:
                continue
            try:
                for name in os.listdir(dirpath):
                    full = os.path.join(dirpath, name)
                    if os.path.isdir(full) and name.lower() == 'onedragon':
                        p = os.path.join(full, 'src', 'zzz_od', 'gui', 'app.py')
                        if os.path.isfile(p):
                            return p
                    if os.path.isdir(full):
                        q.append((full, depth + 1))
            except OSError:
                continue
    return ''

def _detect_od_python(od_path):
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(od_path))))
    for py in ['pythonw.exe', 'python.exe']:
        p = os.path.join(base, '.venv', 'Scripts', py)
        if os.path.isfile(p):
            return p
    return ''

def _detect_ma_path(drives=None):
    if drives is None:
        drives = _get_drives()
    roots = list(drives) + [os.path.expanduser('~')]
    return _search_deep(roots, {'MaaEnd.exe'}, 2)

# ---------- SSE ----------
_sse_clients = []
_sse_lock = threading.Lock()

def _sse_broadcast(event, data):
    msg = f"event: {event}\ndata: {data}\n\n"
    with _sse_lock:
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except:
                pass

# ---------- file log ----------
_logs_dir = None

def _init_logs():
    global _logs_dir
    app_dir = os.path.dirname(os.path.abspath(__file__))
    _logs_dir = os.path.join(app_dir, 'logs')
    os.makedirs(_logs_dir, exist_ok=True)

def _write_log(message, level='INFO'):
    if not _logs_dir:
        return
    date_str = datetime.now().strftime('%Y-%m-%d')
    log_path = os.path.join(_logs_dir, f'AniFlow_{date_str}.log')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            if f.tell() == 0:
                f.write('\ufeff')
            f.write(f'[{timestamp}] [{level}] {message}\n')
    except Exception:
        pass

# ---------- config ----------
class ConfigManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_dir = os.path.join(self.app_dir, 'config')
        os.makedirs(self.config_dir, exist_ok=True)
        self.settings_file = os.path.join(self.config_dir, 'settings.json')
        self.accounts_file = os.path.join(self.config_dir, 'accounts.json')
        self.task_defs_file = os.path.join(self.config_dir, 'task_definitions.json')
        self.settings = self._load_settings()
        self.accounts = self._load_accounts()
        self.task_definitions = self._load_task_definitions()

    def _default_settings(self):
        return {
            'onedragon': {'path': '', 'python_path': 'python'},
            'maaend': {'path': ''},
            'game_paths': {},
            'execution': {'timeout': 7200, 'retry_count': 3, 'switch_delay': 10},
            'sequence': ['onedragon', 'maaend'],
            'post_action': 'close_game'
        }

    def _load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, encoding='utf-8') as f:
                return json.load(f)
        return self._default_settings()

    def _load_accounts(self):
        if os.path.exists(self.accounts_file):
            with open(self.accounts_file, encoding='utf-8') as f:
                return json.load(f)
        return {'zenless_zone_zero': [], 'endfield': []}

    def _load_task_definitions(self):
        if os.path.exists(self.task_defs_file):
            with open(self.task_defs_file, encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_accounts(self):
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, val):
        with self._lock:
            self.settings[key] = val
            self.save_settings_unlocked()

    def save_settings_unlocked(self):
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def save_settings(self):
        with self._lock:
            self.save_settings_unlocked()


config = ConfigManager()

# ---------- process manager with status broadcasting ----------
def _on_status(game_type, status):
    data = json.dumps({'game_type': game_type, 'status': status}, ensure_ascii=False)
    _sse_broadcast('status', data)
    label = {'zenless_zone_zero': '绝区零', 'endfield': '终末地', 'pipeline': '管道'}.get(game_type, game_type)
    _write_log(f'[{label}] {status}', 'INFO')

def _on_output(source, line):
    data = json.dumps({'source': source, 'line': line}, ensure_ascii=False)
    _sse_broadcast('output', data)

pm = ProcessManager(config)
pm.on_status_change(_on_status)
pm.on_output(_on_output)

# ---------- API ----------
class Api:
    def getVersion(self):
        return VERSION

    # --- config ---
    def getConfig(self):
        s = config.settings
        return {
            'onedragon_path': s.get('onedragon', {}).get('path', ''),
            'onedragon_python': s.get('onedragon', {}).get('python_path', ''),
            'maaend_path': s.get('maaend', {}).get('path', ''),
            'sequence': s.get('sequence', []),
            'post_action': s.get('post_action', 'close_game'),
            'exec_timeout': s.get('execution', {}).get('timeout', 7200),
            'exec_retry': s.get('execution', {}).get('retry_count', 3),
            'exec_switch_delay': s.get('execution', {}).get('switch_delay', 10),
        }

    def saveConfig(self, cfg):
        with config._lock:
            config.settings['onedragon'] = {'path': cfg.get('onedragon_path', ''), 'python_path': cfg.get('onedragon_python', '')}
            config.settings['maaend'] = {'path': cfg.get('maaend_path', '')}
            config.settings['sequence'] = cfg.get('sequence', [])
            config.settings['post_action'] = cfg.get('post_action', 'close_game')
            config.settings['execution'] = {
                'timeout': cfg.get('exec_timeout', 7200),
                'retry_count': cfg.get('exec_retry', 3),
                'switch_delay': cfg.get('exec_switch_delay', 10)
            }
            config.save_settings_unlocked()
        _write_log('配置已保存', 'INFO')
        return True

    def savePaths(self, od_path, od_python, ma_path):
        config.set('onedragon', {'path': od_path, 'python_path': od_python})
        config.set('maaend', {'path': ma_path})
        _write_log(f'工具路径已保存: OD={od_path}, MaaEnd={ma_path}', 'INFO')
        return True

    # --- tool scanning ---
    def getDrives(self):
        return _get_drives()

    def scanOD(self):
        od_path = _detect_od_path()
        result = {'path': '', 'python_path': ''}
        if od_path:
            result['path'] = od_path
            result['python_path'] = _detect_od_python(od_path)
        return result

    def scanMaa(self):
        return {'path': _detect_ma_path()}

    # --- tool download ---
    def downloadTool(self, name):
        threading.Thread(target=self._do_download, args=(name,), daemon=True).start()
        return True

    def _do_download(self, name):
        import urllib.request, zipfile, io, shutil, subprocess, traceback
        base_dir = os.path.dirname(os.path.abspath(__file__))
        target = os.path.join(base_dir, 'tools', name)
        try:
            _sse_broadcast('download_status', json.dumps({'msg': f'开始下载 {name}...', 'name': name, 'done': False}))
            if name == 'MaaEnd':
                _sse_broadcast('download_status', json.dumps({'msg': '正在获取 MaaEnd 最新版本信息...', 'name': name, 'done': False}))
                req = urllib.request.Request(
                    'https://api.github.com/repos/MaaXYZ/MaaEnd/releases/latest',
                    headers={'User-Agent': 'AniFlow/1.0'}
                )
                resp = urllib.request.urlopen(req, timeout=15)
                data = json.loads(resp.read().decode())
                asset = None
                for a in data.get('assets', []):
                    if a['name'].endswith('.zip') and 'win' in a['name'].lower() and 'x86_64' in a['name'].lower():
                        asset = a
                        break
                if not asset:
                    raise Exception('未找到 Windows 版本下载文件')
                _sse_broadcast('download_status', json.dumps({'msg': f'正在下载 {asset["name"]}...', 'name': name, 'done': False}))
                resp = urllib.request.urlopen(asset['browser_download_url'], timeout=120)
                z = zipfile.ZipFile(io.BytesIO(resp.read()))
                os.makedirs(target, exist_ok=True)
                z.extractall(target)
                exe_path = os.path.join(target, 'MaaEnd.exe')
                path_found = exe_path if os.path.isfile(exe_path) else ''
                _sse_broadcast('download_status', json.dumps({
                    'msg': 'MaaEnd 下载完成', 'name': name, 'done': True,
                    'path': path_found, 'python_path': ''
                }))
            elif name == 'OneDragon':
                if os.path.exists(target):
                    shutil.rmtree(target, ignore_errors=True)
                _sse_broadcast('download_status', json.dumps({'msg': '正在克隆 OneDragon 仓库...', 'name': name, 'done': False}))
                env = os.environ.copy()
                env['GIT_TERMINAL_PROMPT'] = '0'
                subprocess.run(
                    ['git', 'clone', 'https://gitee.com/OneDragon-Anything/ZenlessZoneZero-OneDragon.git', target],
                    check=True, timeout=300, capture_output=True, env=env
                )
                _sse_broadcast('download_status', json.dumps({'msg': '正在安装 OneDragon 依赖...', 'name': name, 'done': False}))
                py_path = os.path.join(target, '.venv', 'Scripts', 'pythonw.exe')
                if not os.path.isfile(py_path):
                    try:
                        subprocess.run(['uv', 'sync'], cwd=target, check=True, timeout=300, capture_output=True)
                    except Exception:
                        try:
                            subprocess.run(['pip', 'install', '-r', 'requirements.txt'], cwd=target, check=True, timeout=300, capture_output=True)
                        except Exception as e:
                            _sse_broadcast('download_status', json.dumps({'msg': f'依赖安装失败: {e}', 'name': name, 'done': True, 'error': True}))
                            return
                app_path = os.path.join(target, 'src', 'zzz_od', 'gui', 'app.py')
                python_path = ''
                for py in ['pythonw.exe', 'python.exe']:
                    p = os.path.join(target, '.venv', 'Scripts', py)
                    if os.path.isfile(p):
                        python_path = p
                        break
                _sse_broadcast('download_status', json.dumps({
                    'msg': 'OneDragon 下载完成', 'name': name, 'done': True,
                    'path': app_path if os.path.isfile(app_path) else '',
                    'python_path': python_path
                }))
            _write_log(f'{name} 下载完成', 'INFO')
        except Exception as e:
            err_msg = f'{name} 下载失败: {e}'
            _sse_broadcast('download_status', json.dumps({'msg': err_msg, 'name': name, 'done': True, 'error': True}))
            _write_log(err_msg, 'ERROR')
            traceback.print_exc()

    def saveSequence(self, items):
        config.set('sequence', items)
        return True

    def savePostAction(self, action):
        config.set('post_action', action)
        return True

    def saveExecutionConfig(self, cfg):
        config.set('execution', cfg)
        return True

    # --- accounts ---
    def getAccounts(self):
        return config.accounts

    def saveAccounts(self, data):
        config.accounts = data
        config.save_accounts()
        _write_log('账号配置已保存', 'INFO')
        return True

    def getTaskDefinitions(self):
        return config.task_definitions

    # --- game control ---
    def startGame(self, game_type):
        ok, reason = pm.start_game(game_type)
        return ok

    def stopGame(self, game_type):
        ok, reason = pm.stop_game(game_type)
        return ok

    def startSequence(self):
        pm.run_sequence()
        _write_log('一键运行 - 开始顺序执行', 'INFO')

    def stopSequence(self):
        pm.stop_sequence()
        _write_log('一键运行 - 已停止', 'WARNING')

    def openLogFolder(self):
        folder = _logs_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(folder, exist_ok=True)
        os.startfile(folder)
        return True

    # --- update ---
    def checkUpdate(self):
        import urllib.request
        try:
            api_url = 'https://api.github.com/repos/ace-yong/AniFlow/releases/latest'
            req = urllib.request.Request(api_url, headers={'User-Agent': 'AniFlow/1.0', 'Accept': 'application/vnd.github.v3+json'})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode('utf-8'))
            latest = data.get('tag_name', '').lstrip('v')
            return {'current': VERSION, 'latest': latest, 'notes': data.get('body', ''), 'url': data.get('html_url', '')}
        except Exception as e:
            return {'current': VERSION, 'latest': VERSION, 'notes': '', 'url': ''}


api = Api()
HOST = '127.0.0.1'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 0


class Handler(http.server.SimpleHTTPRequestHandler):
    # --- SSE ---
    def _handle_sse(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        q = queue.Queue()
        with _sse_lock:
            _sse_clients.append(q)
        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    self.wfile.write(msg.encode())
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(": heartbeat\n\n".encode())
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _sse_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)

    # --- wallpaper ---
    def _serve_wallpaper(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        wallpaper_path = None
        content_type = None
        for name in ['wallpaper_source.png', 'wallpaper_source.jpg']:
            p = os.path.join(base_dir, name)
            if os.path.isfile(p):
                wallpaper_path = p
                content_type = 'image/png' if name.endswith('.png') else 'image/jpeg'
                break
        if wallpaper_path:
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'max-age=3600')
            self.end_headers()
            with open(wallpaper_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404)

    # --- routing ---
    def do_GET(self):
        if self.path == '/api/events':
            return self._handle_sse()
        if self.path == '/wallpaper.jpg':
            return self._serve_wallpaper()
        if self.path.startswith('/api/'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            method = self.path[5:].split('?')[0]
            try:
                result = getattr(api, method)()
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/'):
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode() if length else '{}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            method = self.path[5:].split('?')[0]
            try:
                args = json.loads(body) if body else []
                fn = getattr(api, method)
                result = fn(*args) if isinstance(args, list) else fn(args)
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
        self.send_error(404)

    def log_message(self, format, *args):
        pass


def _log_exception(exc_type, exc_value, exc_traceback):
    import traceback, platform
    msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    app_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(app_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f'crash_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\ufeff')
        f.write(f'[CRASH] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'Version: {VERSION}\n')
        f.write(f'Python: {sys.version}\n')
        f.write(f'OS: {platform.system()} {platform.release()}\n\n')
        f.write(msg)
    print(f'程序崩溃，日志已保存: {log_path}', file=sys.stderr)
    sys.exit(1)


def _migrate_config():
    """从旧目录迁移配置"""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    dst = os.path.join(app_dir, 'config')
    if os.path.exists(os.path.join(dst, 'settings.json')):
        return
    old_names = ['game-sky', 'gamesky']
    candidates = []
    for old in old_names:
        candidates.append(os.path.join(app_dir, old, 'config', 'settings.json'))
    candidates.append(os.path.join(os.getcwd(), 'config', 'settings.json'))
    for src in candidates:
        if os.path.exists(src):
            import shutil
            os.makedirs(dst, exist_ok=True)
            shutil.copy2(src, os.path.join(dst, 'settings.json'))
            for f in ['accounts.json', 'task_definitions.json']:
                s = os.path.join(os.path.dirname(src), f)
                if os.path.exists(s):
                    shutil.copy2(s, os.path.join(dst, f))
            return


if __name__ == '__main__':
    sys.excepthook = _log_exception
    threading.excepthook = lambda args: _log_exception(args.exc_type, args.exc_value, args.exc_traceback)
    _migrate_config()
    _init_logs()
    _write_log(f'AniFlow v{VERSION} 服务器启动', 'INFO')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    renderer_dir = os.path.join(script_dir, 'renderer')
    if os.path.isdir(renderer_dir):
        static_dir = renderer_dir
    else:
        static_dir = os.path.join(script_dir, 'electron', 'renderer')
    os.chdir(static_dir)
    server = socketserver.ThreadingTCPServer((HOST, PORT), Handler)
    server.allow_reuse_address = True
    port = server.server_address[1]
    print(port, flush=True)
    _write_log(f'HTTP 服务器已启动: http://127.0.0.1:{port}', 'INFO')
    server.serve_forever()
