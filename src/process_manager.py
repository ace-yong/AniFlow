import subprocess
import os
import threading
import tempfile
import time
from typing import Dict, Optional, Callable


class GameProcess:
    def __init__(self, game_type: str, name: str):
        self.game_type = game_type
        self.name = name
        self.process: Optional[subprocess.Popen] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._gen = 0
        self._pid: Optional[int] = None
        self.on_exit: Optional[callable] = None
        self.on_output: Optional[callable] = None

    @property
    def is_running(self):
        if self.process and self.process.poll() is not None:
            self._running = False
        return self._running

    def start(self, args, cwd=None, env=None):
        if self.is_running:
            return False
        self._gen += 1
        self._target_gen = self._gen
        self._ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run, args=(args, cwd, env), daemon=True
        )
        self._thread.start()
        self._ready.wait(timeout=5)
        return self._running

    def _run(self, args, cwd, env):
        my_gen = self._target_gen
        self.process = None
        self._pid = None
        try:
            self.process = subprocess.Popen(
                args, cwd=cwd, env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self._pid = self.process.pid
            self._running = True
            self._ready.set()
            for raw_line in self.process.stdout:
                if self._gen != my_gen:
                    break
                try:
                    line = raw_line.decode('utf-8').rstrip('\r\n')
                except UnicodeDecodeError:
                    line = raw_line.decode('gbk', errors='replace').rstrip('\r\n')
                if self.on_output:
                    self.on_output(line)
            self.process.wait()
        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            if self._gen == my_gen:
                was_running = self._running
                self._running = False
                self.process = None
                self._pid = None
                if was_running and self.on_exit:
                    self.on_exit()

    def stop(self):
        pid = self._pid
        if pid and self._running:
            try:
                if os.name == 'nt':
                    subprocess.run(
                        ['taskkill', '/f', '/t', '/pid', str(pid)],
                        capture_output=True, timeout=10
                    )
                else:
                    if self.process:
                        self.process.kill()
            except Exception:
                pass
            self._gen += 1
            self._running = False
            self.process = None
            self._pid = None
            if self._thread:
                self._thread.join(timeout=3)
            return True
        return False


class ProcessManager:
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self._games: Dict[str, GameProcess] = {}
        self._callback = None
        self._output_cb = None

    def on_status_change(self, callback):
        self._callback = callback

    def on_output(self, callback):
        self._output_cb = callback

    def _notify(self, game_type, status):
        if self._callback:
            self._callback(game_type, status)

    def _notify_output(self, source, line):
        if self._output_cb:
            self._output_cb(source, line)

    def _get_game(self, game_type: str) -> GameProcess:
        if game_type not in self._games:
            name = {'zenless_zone_zero': '绝区零', 'endfield': '终末地'}.get(game_type, game_type)
            gp = GameProcess(game_type, name)
            gp.on_exit = lambda gt=game_type: self._notify(gt, 'stopped')
            gp.on_output = lambda line, gt=game_type: self._notify_output(gt, line)
            self._games[game_type] = gp
        return self._games[game_type]

    def start_game(self, game_type: str) -> bool:
        gp = self._get_game(game_type)
        if gp.is_running:
            return True

        settings = self.config_manager.settings if self.config_manager else {}
        args = []
        cwd = None
        env = None

        if game_type == 'endfield':
            tool_path = settings.get('maaend', {}).get('path', '')
            if not tool_path or not os.path.exists(tool_path):
                self._notify(game_type, 'failed')
                return False
            args = [tool_path, '--autostart', '-i', '全套日常']
            cwd = os.path.dirname(tool_path)
        elif game_type == 'zenless_zone_zero':
            tool_path = settings.get('onedragon', {}).get('path', '')
            python_path = settings.get('onedragon', {}).get('python_path', 'python')
            if not tool_path or not os.path.exists(tool_path) or not os.path.exists(python_path):
                self._notify(game_type, 'failed')
                return False
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(python_path)))
            env = os.environ.copy()
            env['PYTHONPATH'] = os.path.join(project_dir, 'src')
            args = [python_path, tool_path]
            cwd = project_dir
        else:
            return False

        ok = gp.start(args, cwd=cwd, env=env)
        if ok:
            self._notify(game_type, 'running')
        else:
            self._notify(game_type, 'failed')
        return ok

    def stop_game(self, game_type: str) -> bool:
        gp = self._games.get(game_type)
        if not gp:
            return False
        ok = gp.stop()
        if ok:
            self._notify(game_type, 'stopped')
        return ok

    def start_all(self):
        for gt in ['zenless_zone_zero', 'endfield']:
            self.start_game(gt)

    def stop_all(self):
        for gt in list(self._games.keys()):
            self.stop_game(gt)

    def is_running(self, game_type: str) -> bool:
        gp = self._games.get(game_type)
        return gp.is_running if gp else False

    def all_stopped(self) -> bool:
        return not any(gp.is_running for gp in self._games.values())

    # ---------- 顺序执行管道 ----------

    _TOOL_LABELS = {
        'onedragon': 'OneDragon',
        'maaend': 'MaaEnd',
    }

    def _run_seq_item(self, key: str) -> bool:
        """运行单个管道项目，返回 True 表示执行成功"""
        settings = self.config_manager.settings if self.config_manager else {}

        if key == 'onedragon':
            python_path = settings.get('onedragon', {}).get('python_path', 'python')
            tool_path = settings.get('onedragon', {}).get('path', '')
            if not tool_path or not os.path.exists(tool_path) or not os.path.exists(python_path):
                return False
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(python_path)))
            python_exe = python_path.replace('pythonw.exe', 'python.exe')
            script = (
                'import sys; '
                'sys.argv = ["launcher", "-c"]; '
                'from zzz_od.application.zzz_application_launcher import main; '
                'main()'
            )
            script_path = os.path.join(tempfile.gettempdir(), 'od_headless_run.py')
            try:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(script)
            except Exception:
                return False
            env = os.environ.copy()
            env['PYTHONPATH'] = os.path.join(project_dir, 'src')
            args = [python_exe, script_path]
            cwd = project_dir
        elif key == 'maaend':
            tool_path = settings.get('maaend', {}).get('path', '')
            if not tool_path or not os.path.exists(tool_path):
                return False
            args = [tool_path, '--autostart', '-i', '全套日常']
            cwd = os.path.dirname(tool_path)
            env = None
        else:
            return False

        self._seq_process = subprocess.Popen(
            args, cwd=cwd, env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' and key == 'onedragon' else 0
        )

        stop_read = threading.Event()
        def read_output():
            for raw_line in self._seq_process.stdout:
                if stop_read.is_set():
                    break
                try:
                    line = raw_line.decode('utf-8').rstrip('\r\n')
                except UnicodeDecodeError:
                    line = raw_line.decode('gbk', errors='replace').rstrip('\r\n')
                self._notify_output(key, line)

        t = threading.Thread(target=read_output, daemon=True)
        t.start()

        if key == 'maaend':
            try:
                self._seq_process.wait(timeout=900)
            except subprocess.TimeoutExpired:
                pass
            if self._seq_process.poll() is None:
                for name in ('MaaEnd.exe', 'Endfield.exe'):
                    subprocess.run(['taskkill', '/f', '/im', name],
                                  capture_output=True, timeout=10)
                self._seq_process.wait()
        else:
            self._seq_process.wait()

        stop_read.set()
        t.join(timeout=3)
        self._seq_process = None
        return True

    def run_sequence(self) -> bool:
        """按配置顺序依次执行管道项目"""
        if getattr(self, '_seq_running', False):
            return False
        self._seq_running = True
        self._seq_process = None

        settings = self.config_manager.settings if self.config_manager else {}
        sequence = settings.get('sequence', ['onedragon', 'maaend'])

        def _run():
            try:
                for key in sequence:
                    if not self._seq_running:
                        return
                    label = self._TOOL_LABELS.get(key, key)
                    self._notify('pipeline', f'seq_{key}_running')
                    self._run_seq_item(key)

                if self._seq_running:
                    self._notify('pipeline', 'seq_completed')
                    post_action = settings.get('post_action', 'close_game')
                    if post_action == 'close_game':
                        for exe in ('MaaEnd.exe', 'Endfield.exe'):
                            subprocess.run(['taskkill', '/f', '/im', exe],
                                          capture_output=True, timeout=10)
                    elif post_action == 'shutdown':
                        subprocess.run(['shutdown', '/s', '/t', '30', '/c', 'AniFlow 一键运行已完成，即将关机'],
                                      capture_output=True, timeout=35)
            except Exception:
                import traceback
                traceback.print_exc()
            finally:
                self._seq_running = False
                self._seq_process = None

        threading.Thread(target=_run, daemon=True).start()
        return True

    def stop_sequence(self):
        """停止正在执行的顺序管道"""
        self._seq_running = False
        if self._seq_process:
            try:
                if os.name == 'nt':
                    subprocess.run(
                        ['taskkill', '/f', '/t', '/pid', str(self._seq_process.pid)],
                        capture_output=True, timeout=10
                    )
                else:
                    self._seq_process.kill()
            except Exception:
                pass
            self._seq_process = None
