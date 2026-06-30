#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json, threading, urllib.request, traceback, shutil
from datetime import datetime

from src.process_manager import ProcessManager

VERSION = "1.1.0"


def _ensure_admin():
    if os.name != 'nt':
        return
    import ctypes
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
    except Exception:
        return
    exe_path = sys.argv[0] if getattr(sys, 'frozen', False) else __file__
    script_dir = os.path.dirname(os.path.abspath(exe_path))
    script = os.path.basename(sys.argv[0])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", os.path.join(script_dir, script), '', script_dir, 1)
    sys.exit(0)


def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'AniFlow')
    return os.path.dirname(os.path.abspath(__file__))


def _migrate_config():
    dst = os.path.join(_app_dir(), 'config')
    if os.path.exists(os.path.join(dst, 'settings.json')):
        return
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(exe_dir, 'config', 'settings.json'),
        os.path.join(os.path.dirname(exe_dir) if not getattr(sys, 'frozen', False) else exe_dir, 'config', 'settings.json'),
    ]
    for old_name in ['game-sky', 'gamesky']:
        candidates.append(os.path.join(exe_dir, old_name, 'config', 'settings.json'))
    candidates.append(os.path.join(os.getcwd(), 'config', 'settings.json'))
    for src in candidates:
        if os.path.exists(src):
            os.makedirs(dst, exist_ok=True)
            shutil.copy2(src, os.path.join(dst, 'settings.json'))
            for f in ['accounts.json', 'task_definitions.json']:
                s = os.path.join(os.path.dirname(src), f)
                if os.path.exists(s):
                    shutil.copy2(s, os.path.join(dst, f))
            return


class ConfigManager:
    def __init__(self, config_dir='config'):
        self.config_dir = config_dir
        self.settings_file = os.path.join(config_dir, 'settings.json')
        self.accounts_file = os.path.join(config_dir, 'accounts.json')
        self.task_defs_file = os.path.join(config_dir, 'task_definitions.json')
        self.accounts = self._load_json(self.accounts_file, {'zenless_zone_zero': [], 'endfield': []})
        self.settings = self._load_json(self.settings_file, self._default_settings())
        self.task_definitions = self._load_json(self.task_defs_file, {})

    @staticmethod
    def _load_json(path, default):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default

    def _default_settings(self):
        return {
            'onedragon': {'path': '', 'python_path': 'python'},
            'maaend': {'path': ''},
            'game_paths': {},
            'execution': {'timeout': 7200, 'retry_count': 3, 'switch_delay': 10},
            'sequence': ['onedragon', 'maaend'],
            'post_action': 'close_game'
        }

    def save_settings(self):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def save_accounts(self):
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, indent=2, ensure_ascii=False)

    def get_tool_settings(self, name):
        return self.settings.get(name, {})

    def set_tool_settings(self, name, cfg):
        self.settings.setdefault(name, {}).update(cfg)
        self.save_settings()

    def get_sequence(self):
        return self.settings.get('sequence', ['onedragon', 'maaend'])

    def set_sequence(self, items):
        self.settings['sequence'] = items
        self.save_settings()

    def get_post_action(self):
        return self.settings.get('post_action', 'close_game')

    def set_post_action(self, action):
        self.settings['post_action'] = action
        self.save_settings()


class Api:
    def __init__(self):
        _migrate_config()
        self.config = ConfigManager(os.path.join(_app_dir(), 'config'))
        self.pm = ProcessManager(self.config)
        self.pm.on_status_change(self._on_status)
        self.pm.on_output(self._on_output)
        self._log_dir = os.path.join(_app_dir(), 'logs')
        os.makedirs(self._log_dir, exist_ok=True)
        self._log_file()
        self._log('AniFlow v{} 启动'.format(VERSION), 'INFO')
        self._log('数据目录: {}'.format(_app_dir()), 'INFO')

    def _log_file(self):
        name = 'AniFlow_{}.log'.format(datetime.now().strftime('%Y-%m-%d'))
        self._log_path = os.path.join(self._log_dir, name)

    def _log(self, msg, level='INFO'):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = '[{}] [{}] {}\n'.format(ts, level, msg)
        try:
            with open(self._log_path, 'a', encoding='utf-8') as f:
                if f.tell() == 0:
                    f.write('\ufeff')
                f.write(line)
        except Exception:
            pass
        self._emit('addLog', msg, level)

    def _emit(self, event, *args):
        try:
            import webview
            webview.windows[0].evaluate_js('window._on({}, {})'.format(
                json.dumps(event), json.dumps(args)))
        except Exception:
            pass

    def _on_status(self, game_type, status):
        self._emit('onStatus', game_type, status)

    def _on_output(self, source, line):
        self._emit('onToolOutput', source, line)

    # ---------- JS API ----------
    def getVersion(self):
        return VERSION

    def getConfig(self):
        s = self.config.settings
        return {
            'onedragon_path': s.get('onedragon', {}).get('path', ''),
            'onedragon_python': s.get('onedragon', {}).get('python_path', ''),
            'maaend_path': s.get('maaend', {}).get('path', ''),
            'sequence': s.get('sequence', []),
            'post_action': s.get('post_action', 'close_game'),
        }

    def savePaths(self, od_path, od_python, ma_path):
        self.config.set_tool_settings('onedragon', {'path': od_path, 'python_path': od_python})
        self.config.set_tool_settings('maaend', {'path': ma_path})
        self._log('已保存工具路径', 'INFO')
        return True

    def saveSequence(self, items):
        self.config.set_sequence(items)
        self._log('已保存执行顺序: {}'.format(items), 'INFO')
        return True

    def savePostAction(self, action):
        self.config.set_post_action(action)
        self._log('已保存执行后动作: {}'.format(action), 'INFO')
        return True

    def startGame(self, game_type):
        ok, reason = self.pm.start_game(game_type)
        return ok

    def stopGame(self, game_type):
        ok, reason = self.pm.stop_game(game_type)
        return ok

    def isRunning(self, game_type):
        return self.pm.is_running(game_type)

    def startSequence(self):
        self.pm.run_sequence()

    def stopSequence(self):
        self.pm.stop_sequence()

    def scanTool(self, tool, drive):
        self._log('正在扫描 {} ({}...)'.format(tool, drive or '全部盘符'), 'INFO')
        drives = None if drive == '全部盘符' or not drive else [drive.rstrip('\\') + '\\']
        if tool == 'onedragon':
            p = self._detect_od_path(drives)
            py = self._detect_od_python(drives) if p else ''
            if p:
                self._log('找到 OneDragon: {}'.format(p), 'INFO')
            return json.dumps({'path': p or '', 'python': py or ''})
        elif tool == 'maaend':
            p = self._detect_ma_path(drives)
            if p:
                self._log('找到 MaaEnd: {}'.format(p), 'INFO')
            return json.dumps({'path': p or ''})
        return json.dumps({'path': '', 'python': ''})

    def downloadTool(self, tool):
        self._log('开始下载 {}...'.format(tool), 'INFO')
        import webview, subprocess, shutil, zipfile, io, urllib.request
        base_dir = _app_dir()
        target = os.path.join(base_dir, 'tools', tool)
        if os.path.exists(target):
            shutil.rmtree(target, ignore_errors=True)
        try:
            if tool == 'onedragon':
                self._log('正在从 Gitee 克隆 OneDragon...', 'INFO')
                env = os.environ.copy()
                env['GIT_TERMINAL_PROMPT'] = '0'
                git_cmd = ['git', '-c', 'credential.helper=', 'clone',
                    'https://gitee.com/OneDragon-Anything/ZenlessZoneZero-OneDragon.git', target]
                subprocess.run(git_cmd, check=True, timeout=300, capture_output=True, env=env)
                self._log('OneDragon 下载完成，安装依赖...', 'INFO')
                py_path = os.path.join(target, '.venv', 'Scripts', 'pythonw.exe')
                if not os.path.isfile(py_path):
                    try:
                        subprocess.run(['uv', 'sync'], cwd=target, check=True, timeout=300, capture_output=True)
                    except Exception:
                        try:
                            subprocess.run(['pip', 'install', '-r', 'requirements.txt'], cwd=target, check=True, timeout=300, capture_output=True)
                        except Exception as e:
                            self._log('依赖安装失败: {}'.format(e), 'ERROR')
                app_path = os.path.join(target, 'src', 'zzz_od', 'gui', 'app.py')
                if os.path.isfile(app_path):
                    self._log('OneDragon 安装完成', 'SUCCESS')
                    return json.dumps({'path': app_path, 'python': py_path if os.path.isfile(py_path) else ''})
            elif tool == 'maaend':
                self._log('正在从 GitHub 获取 MaaEnd 最新版本...', 'INFO')
                req = urllib.request.Request('https://api.github.com/repos/MaaXYZ/MaaEnd/releases/latest',
                    headers={'User-Agent': 'AniFlow/1.0'})
                data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
                asset = None
                for a in data.get('assets', []):
                    name = a['name'].lower()
                    if name.endswith('.zip') and 'win' in name and 'x86_64' in name:
                        asset = a
                        break
                if not asset:
                    raise Exception('未找到 Windows x86_64 版本')
                self._log('正在下载 {} ({}MB)...'.format(asset['name'], asset['size']//1048576), 'INFO')
                resp = urllib.request.urlopen(asset['browser_download_url'], timeout=120)
                z = zipfile.ZipFile(io.BytesIO(resp.read()))
                os.makedirs(target, exist_ok=True)
                z.extractall(target)
                exe_path = os.path.join(target, 'MaaEnd.exe')
                if os.path.isfile(exe_path):
                    self._log('MaaEnd 安装完成', 'SUCCESS')
                    return json.dumps({'path': exe_path})
                raise Exception('解压后未找到 MaaEnd.exe')
            return json.dumps({'path': '', 'python': ''})
        except Exception as e:
            self._log('{} 下载失败: {}'.format(tool, e), 'ERROR')
            return json.dumps({'error': str(e)})

    def _search_deep(self, roots, targets, max_depth=2):
        from collections import deque
        for root in roots:
            if not os.path.isdir(root):
                continue
            q = deque([(root, 0)])
            while q:
                d, depth = q.popleft()
                if depth > max_depth:
                    continue
                try:
                    for name in os.listdir(d):
                        full = os.path.join(d, name)
                        if os.path.isfile(full) and name in targets:
                            return full
                        if os.path.isdir(full):
                            q.append((full, depth + 1))
                except PermissionError:
                    continue
        return ''

    def _detect_od_path(self, drives=None):
        if drives is None:
            drives = ['{}:\\'.format(chr(d)) for d in range(ord('C'), ord('Z') + 1) if os.path.exists('{}:\\'.format(chr(d)))]
        roots = list(drives) + [os.path.expanduser('~')]
        for root in roots:
            if not os.path.isdir(root):
                continue
            from collections import deque
            q = deque([(root, 0)])
            while q:
                d, depth = q.popleft()
                if depth > 2:
                    continue
                try:
                    for name in os.listdir(d):
                        full = os.path.join(d, name)
                        if os.path.isdir(full) and name.lower() == 'onedragon':
                            p = os.path.join(full, 'src', 'zzz_od', 'gui', 'app.py')
                            if os.path.isfile(p):
                                return p
                        if os.path.isdir(full):
                            q.append((full, depth + 1))
                except PermissionError:
                    continue
        return ''

    def _detect_od_python(self, drives=None):
        path = self._detect_od_path(drives)
        if not path:
            return ''


if __name__ == '__main__':
    api = Api()
    _script_dir = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.abspath(__file__))
    html = os.path.join(_script_dir, 'static', 'index.html')
    if not os.path.isfile(html):
        html = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'index.html')
    import webview
    try:
        webview.create_window('AniFlow v' + VERSION, html, js_api=api, width=1100, height=700)
    except Exception as e:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, '启动失败: {}'.format(e), 'AniFlow Error', 0x10)

    def _detect_ma_path(self, drives=None):
        if drives is None:
            drives = ['{}:\\'.format(chr(d)) for d in range(ord('C'), ord('Z') + 1) if os.path.exists('{}:\\'.format(chr(d)))]
        roots = list(drives) + [os.path.expanduser('~')]
        return self._search_deep(roots, {'MaaEnd.exe'}, 2)

    def checkUpdate(self):
        api_url = 'https://api.github.com/repos/ace-yong/AniFlow/releases/latest'
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'AniFlow/1.0', 'Accept': 'application/vnd.github.v3+json'})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode())
            tag = data.get('tag_name', '').lstrip('v')
            return json.dumps({'latest': tag, 'current': VERSION, 'notes': data.get('body', ''), 'url': data.get('html_url', '')})
        except Exception as e:
            return json.dumps({'latest': VERSION, 'current': VERSION, 'notes': '', 'url': '', 'error': str(e)})

    def downloadUpdate(self):
        import webview
        api_url = 'https://api.github.com/repos/ace-yong/AniFlow/releases/latest'
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'AniFlow/1.0'})
            data = json.loads(urllib.request.urlopen(req, timeout=15).read())
            dl_url = ''
            for a in data.get('assets', []):
                if a['name'].endswith('.exe'):
                    dl_url = a['browser_download_url']
                    break
            if not dl_url:
                raise Exception('未找到可下载文件')
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            tmp = os.path.join(exe_dir, 'AniFlow_update.exe')
            urllib.request.urlretrieve(dl_url, tmp)
            new_exe = os.path.join(exe_dir, 'AniFlow.exe')
            updater = os.path.join(exe_dir, 'update.bat')
            with open(updater, 'w', encoding='utf-8') as f:
                f.write('@echo off\nchcp 65001 >nul\n:wait\n')
                f.write('tasklist /FI "IMAGENAME eq AniFlow.exe" 2>nul | find /I /N "AniFlow.exe" >nul\n')
                f.write('if %errorlevel% equ 0 (timeout /t 1 /nobreak >nul & goto wait)\n')
                f.write('move /Y "{}" "{}" >nul\n'.format(tmp, new_exe))
                f.write('start "" "{}"\ndel "%~f0"\n'.format(new_exe))
            os.startfile(updater)
            sys.exit(0)
        except Exception as e:
            return str(e)

    def browseFile(self, filter_str):
        import webview
        try:
            files = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, file_types=[filter_str])
            if files:
                return files[0]
        except Exception:
            pass
        return ''
