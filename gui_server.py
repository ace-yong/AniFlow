#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Headless HTTP server for Electron frontend"""
import sys, os, json, threading, socketserver, http.server, webbrowser
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
from process_manager import ProcessManager

VERSION = "1.1.0"


class ConfigManager:
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
        os.makedirs(self.config_dir, exist_ok=True)
        self.settings_file = os.path.join(self.config_dir, 'settings.json')
        self.settings = self._load()

    def _load(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, encoding='utf-8') as f:
                return json.load(f)
        return {'onedragon': {'path':'','python_path':'python'}, 'maaend': {'path':''},
                'sequence': ['onedragon','maaend'], 'post_action': 'close_game'}

    def save(self):
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, val):
        self.settings[key] = val
        self.save()


config = ConfigManager()
pm = ProcessManager(config)


class Api:
    def getVersion(self): return VERSION

    def getConfig(self):
        s = config.settings
        return {'onedragon_path': s.get('onedragon',{}).get('path',''),
                'onedragon_python': s.get('onedragon',{}).get('python_path',''),
                'maaend_path': s.get('maaend',{}).get('path',''),
                'sequence': s.get('sequence',[]),
                'post_action': s.get('post_action','close_game')}

    def savePaths(self, od_path, od_python, ma_path):
        config.set('onedragon', {'path': od_path, 'python_path': od_python})
        config.set('maaend', {'path': ma_path})
        return True

    def saveSequence(self, items):
        config.set('sequence', items)
        return True

    def savePostAction(self, action):
        config.set('post_action', action)
        return True

    def startGame(self, game_type):
        ok, reason = pm.start_game(game_type)
        return ok

    def stopGame(self, game_type):
        ok, reason = pm.stop_game(game_type)
        return ok

    def startSequence(self):
        pm.run_sequence()

    def stopSequence(self):
        pm.stop_sequence()


api = Api()
HOST = '127.0.0.1'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 0


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
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

    def log_message(self, format, *args): pass


if __name__ == '__main__':
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'renderer')
    os.chdir(static_dir)
    server = socketserver.TCPServer((HOST, PORT), Handler)
    port = server.server_address[1]
    print(port, flush=True)  # Print port for Electron to read
    server.serve_forever()
