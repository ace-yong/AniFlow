#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏自动化调度工具 - 图形化界面
支持绝区零和终末地的多账号自动化任务管理
"""
import sys
import os
import json
import time
import threading
import urllib.request
import webbrowser
import shutil
import traceback


VERSION = "1.0.1"

def _app_dir():
    """返回 AniFlow 数据目录（config、logs、tools 等都在此目录下）"""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'AniFlow')
    return os.path.dirname(os.path.abspath(__file__))


def _migrate_config():
    """将旧版本配置迁移到当前数据目录（处理项目改名后的路径变化）"""
    dst = os.path.join(_app_dir(), 'config')
    if os.path.exists(os.path.join(dst, 'settings.json')):
        return  # 已有新配置
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(exe_dir, 'config', 'settings.json'),
        os.path.join(os.path.dirname(exe_dir), 'config', 'settings.json'),
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

import threading
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QTreeWidget,
    QTreeWidgetItem, QGroupBox, QCheckBox, QTextEdit, QSplitter,
    QTabWidget, QFormLayout, QLineEdit, QSpinBox, QComboBox,
    QMessageBox, QProgressBar, QFrame, QScrollArea, QDialog,
    QDialogButtonBox, QFileDialog, QToolBar, QAction, QStatusBar, QRadioButton,
    QGridLayout, QSizePolicy, QHeaderView, QTableWidget, QTableWidgetItem,
    QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QObject
import subprocess
import urllib.request
import zipfile
import io
import shutil
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QBrush, QPixmap, QImage


# 配置管理类
class ConfigManager:
    def __init__(self, config_dir='config'):
        self.config_dir = config_dir
        self.accounts_file = os.path.join(config_dir, 'accounts.json')
        self.settings_file = os.path.join(config_dir, 'settings.json')
        self.task_defs_file = os.path.join(config_dir, 'task_definitions.json')
        self.accounts = self._load_accounts()
        self.settings = self._load_settings()
        self.task_definitions = self._load_task_definitions()

    def _load_accounts(self):
        if os.path.exists(self.accounts_file):
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'zenless_zone_zero': [], 'endfield': []}

    def _load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_settings()

    def _default_settings(self):
        return {
            'onedragon': {'path': '', 'python_path': 'python'},
            'maaend': {'path': ''},
            'game_paths': {},
            'execution': {'timeout': 7200, 'retry_count': 3, 'switch_delay': 10},
            'sequence': ['onedragon', 'maaend'],
            'post_action': 'close_game'
        }

    def _load_task_definitions(self):
        if os.path.exists(self.task_defs_file):
            with open(self.task_defs_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_enabled_accounts(self, game_type):
        accounts_data = self.accounts.get(game_type, [])
        accounts = []
        for a in accounts_data:
            if a.get('enabled', True):
                account = type('Account', (), a)()
                accounts.append(account)
        return sorted(accounts, key=lambda x: x.priority)

    def save_accounts(self):
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(self.accounts, f, indent=2, ensure_ascii=False)

    def save_settings(self):
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def get_tool_settings(self, tool_name):
        return self.settings.get(tool_name, {})

    def set_tool_settings(self, tool_name, config):
        existing = self.settings.get(tool_name, {})
        existing.update(config)
        self.settings[tool_name] = existing
        self.save_settings()

    def get_execution_settings(self):
        return self.settings.get('execution', {})

    def get_schedule_settings(self):
        return self.settings.get('schedule', {})

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


# 游戏进程管理 - 包装 ProcessManager 的 QObject
from src.process_manager import ProcessManager as ProcessManagerCls
ProcessManager = ProcessManagerCls


class GameProcessManager(QObject):
    status_changed = pyqtSignal(str, str)  # game_type, status (running/stopped/failed)
    log_message = pyqtSignal(str, str)     # message, level
    tool_output = pyqtSignal(str, str)     # source, line (from managed tools)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.pm = ProcessManager(config_manager)
        self.pm.on_status_change(self._on_status)
        self.pm.on_output(self._on_process_output)

    def _on_status(self, game_type, status):
        self.status_changed.emit(game_type, status)
        if game_type == 'pipeline':
            if status == 'seq_completed':
                self.log_message.emit('【一键运行】全部任务完成！', 'SUCCESS')
            elif status.startswith('seq_') and status.endswith('_running'):
                key = status[4:-8]
                labels = {'onedragon': 'OneDragon', 'maaend': 'MaaEnd'}
                label = labels.get(key, key)
                self.log_message.emit(f'【一键运行】正在执行 {label}...', 'INFO')
            else:
                self.log_message.emit(f'管道: {status}', 'INFO')
            return
        label = {'zenless_zone_zero': '绝区零', 'endfield': '终末地'}.get(game_type, game_type)
        icons = {'running': '●', 'stopped': '○', 'failed': '✗'}
        icon = icons.get(status, '?')
        level = 'SUCCESS' if status == 'running' else 'WARNING' if status == 'stopped' else 'ERROR'
        msg = {
            'running': f'启动 {label} 成功',
            'stopped': f'已停止 {label}',
            'failed': f'启动 {label} 失败，请检查工具路径',
        }.get(status, f'{label} {status}')
        self.log_message.emit(f'{label} {icon} {msg}', level)

    def _on_process_output(self, source, line):
        self.tool_output.emit(source, line)

    def start_game(self, game_type: str):
        label = {'zenless_zone_zero': '绝区零', 'endfield': '终末地'}.get(game_type, game_type)
        if self.pm.is_running(game_type):
            self.log_message.emit(f'{label} 已在运行中', 'WARNING')
            return False, '运行中'
        threading.Thread(target=self._do_start, args=(game_type,), daemon=True).start()
        return True, '正在启动...'

    def _do_start(self, game_type):
        self.pm.start_game(game_type)

    def stop_game(self, game_type: str):
        label = {'zenless_zone_zero': '绝区零', 'endfield': '终末地'}.get(game_type, game_type)
        if not self.pm.is_running(game_type):
            self.log_message.emit(f'{label} 未在运行', 'WARNING')
            return False, '已停止'
        threading.Thread(target=self._do_stop, args=(game_type,), daemon=True).start()
        return True, '正在停止...'

    def _do_stop(self, game_type):
        self.pm.stop_game(game_type)

    def start_all(self):
        threading.Thread(target=self._do_start_all, daemon=True).start()

    def _do_start_all(self):
        self.pm.start_all()

    def stop_all(self):
        threading.Thread(target=self._do_stop_all, daemon=True).start()

    def _do_stop_all(self):
        self.pm.stop_all()

    def start_sequence(self):
        self.pm.run_sequence()
        self.log_message.emit('【一键运行】开始顺序执行任务', 'INFO')

    def stop_sequence(self):
        self.pm.stop_sequence()
        self.log_message.emit('【一键运行】已停止', 'WARNING')

    def is_running(self, game_type: str) -> bool:
        return self.pm.is_running(game_type)


# 账号配置对话框
class AccountConfigDialog(QDialog):
    """账号配置对话框 - 支持详细的任务选择"""
    def __init__(self, parent=None, account_data=None, game_type='zenless_zone_zero', config_manager=None):
        super().__init__(parent)
        self.account_data = account_data or {}
        self.game_type = game_type
        self.config_manager = config_manager
        self.task_definitions = {}
        self.setWindowTitle('账号配置')
        self.setMinimumSize(650, 600)
        self.task_checkboxes = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 基本信息区域
        info_group = QGroupBox('基本信息')
        info_layout = QFormLayout(info_group)

        self.name_edit = QLineEdit()
        self.name_edit.setText(self.account_data.get('name', ''))
        self.name_edit.setPlaceholderText('输入账号名称（如：绝区零主账号）')
        info_layout.addRow('账号名称:', self.name_edit)

        self.game_path_edit = QLineEdit()
        self.game_path_edit.setText(self.account_data.get('game_path', ''))
        self.game_path_edit.setPlaceholderText('游戏安装路径（可选）')
        browse_btn = QPushButton('浏览')
        browse_btn.clicked.connect(self.browse_game_path)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.game_path_edit)
        path_layout.addWidget(browse_btn)
        info_layout.addRow('游戏路径:', path_layout)

        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 10)
        self.priority_spin.setValue(self.account_data.get('priority', 1))
        self.priority_spin.setToolTip('数值越小优先级越高，越先执行')
        info_layout.addRow('执行优先级:', self.priority_spin)

        layout.addWidget(info_group)

        # 任务配置区域 - 使用滚动区域
        tasks_group = QGroupBox('任务配置')
        tasks_main_layout = QVBoxLayout(tasks_group)

        # 快捷操作按钮
        quick_layout = QHBoxLayout()
        select_all_btn = QPushButton('全选')
        select_all_btn.clicked.connect(self.select_all_tasks)
        deselect_all_btn = QPushButton('取消全选')
        deselect_all_btn.clicked.connect(self.deselect_all_tasks)
        select_daily_btn = QPushButton('选择日常任务')
        select_daily_btn.clicked.connect(self.select_daily_tasks)
        quick_layout.addWidget(select_all_btn)
        quick_layout.addWidget(deselect_all_btn)
        quick_layout.addWidget(select_daily_btn)
        quick_layout.addStretch()
        tasks_main_layout.addLayout(quick_layout)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(350)
        scroll_content = QWidget()
        self.tasks_layout = QVBoxLayout(scroll_content)

        # 加载任务定义
        self.load_task_definitions()

        scroll_area.setWidget(scroll_content)
        tasks_main_layout.addWidget(scroll_area)
        layout.addWidget(tasks_group)

        # 启用账号
        self.enabled_checkbox = QCheckBox('启用此账号')
        self.enabled_checkbox.setChecked(self.account_data.get('enabled', True))
        layout.addWidget(self.enabled_checkbox)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_task_definitions(self):
        """从task_definitions.json加载任务定义"""
        if self.config_manager:
            self.task_definitions = self.config_manager.task_definitions.get(self.game_type, {})
        else:
            # 如果没有config_manager，尝试直接加载文件
            task_defs_file = os.path.join('config', 'task_definitions.json')
            if os.path.exists(task_defs_file):
                with open(task_defs_file, 'r', encoding='utf-8') as f:
                    defs = json.load(f)
                    self.task_definitions = defs.get(self.game_type, {})

        tasks = self.task_definitions.get('tasks', {})
        current_tasks = self.account_data.get('tasks', [])

        # 按类别分组
        categories = {}
        for task_id, task_info in tasks.items():
            category = task_info.get('category', '其他')
            if category not in categories:
                categories[category] = []
            categories[category].append((task_id, task_info))

        # 显示任务（按类别分组）
        category_order = ['日常', '基建', '战斗', '探索', '贸易', '社交', '养成', '活动', '副本', '其他']
        for category in category_order:
            if category in categories:
                self.add_category_section(category, categories[category], current_tasks)

        # 添加其他未分类的任务
        for category, items in categories.items():
            if category not in category_order:
                self.add_category_section(category, items, current_tasks)

    def add_category_section(self, category, tasks, current_tasks):
        """添加一个类别的任务区域"""
        category_group = QGroupBox(category)
        category_layout = QVBoxLayout(category_group)

        for task_id, task_info in tasks:
            task_widget = QWidget()
            task_layout = QHBoxLayout(task_widget)
            task_layout.setContentsMargins(0, 0, 0, 0)

            # 复选框
            checkbox = QCheckBox(task_info.get('name', task_id))
            checkbox.setChecked(task_id in current_tasks)
            checkbox.setToolTip(task_info.get('description', ''))
            self.task_checkboxes[task_id] = checkbox
            task_layout.addWidget(checkbox)

            # 描述标签
            desc_label = QLabel(task_info.get('description', ''))
            desc_label.setStyleSheet('color: #666; font-size: 11px;')
            desc_label.setWordWrap(True)
            task_layout.addWidget(desc_label, 1)

            # 日常标记
            if task_info.get('daily', False):
                daily_tag = QLabel('[日常]')
                daily_tag.setStyleSheet('color: #4CAF50; font-size: 10px;')
                task_layout.addWidget(daily_tag)

            category_layout.addWidget(task_widget)

        self.tasks_layout.addWidget(category_group)

    def select_all_tasks(self):
        for checkbox in self.task_checkboxes.values():
            checkbox.setChecked(True)

    def deselect_all_tasks(self):
        for checkbox in self.task_checkboxes.values():
            checkbox.setChecked(False)

    def select_daily_tasks(self):
        """选择所有日常任务"""
        tasks = self.task_definitions.get('tasks', {})
        for task_id, checkbox in self.task_checkboxes.items():
            task_info = tasks.get(task_id, {})
            checkbox.setChecked(task_info.get('daily', False))

    def browse_game_path(self):
        path = QFileDialog.getExistingDirectory(self, '选择游戏目录')
        if path:
            self.game_path_edit.setText(path)

    def get_account_data(self):
        tasks = [task_id for task_id, checkbox in self.task_checkboxes.items() if checkbox.isChecked()]

        if self.account_data.get('id'):
            account_id = self.account_data['id']
        else:
            prefix = 'zzz' if self.game_type == 'zenless_zone_zero' else 'end'
            account_id = f'{prefix}_account_{int(time.time())}'

        return {
            'id': account_id,
            'name': self.name_edit.text(),
            'game_path': self.game_path_edit.text(),
            'tasks': tasks,
            'enabled': self.enabled_checkbox.isChecked(),
            'priority': self.priority_spin.value()
        }


class UpdateDialog(QDialog):
    def __init__(self, parent=None, current_version='', latest_version='', release_url='', notes=''):
        super().__init__(parent)
        self.setWindowTitle('检查更新')
        self.setFixedSize(420, 260)
        self._release_url = release_url
        self._download_url = ''

        root = QVBoxLayout(self)
        root.setSpacing(12)

        title = QLabel('检查更新')
        title.setStyleSheet('font-size: 16px; font-weight: bold; color: #333;')
        root.addWidget(title)

        info = QLabel()
        if latest_version and latest_version != current_version:
            text = f'当前版本：<span style="color:#999">v{current_version}</span><br>最新版本：<span style="color:#52c41a;font-weight:bold">v{latest_version}</span>'
            info.setText(text)
            info.setStyleSheet('font-size: 13px; padding: 8px 0;')
            root.addWidget(info)

            notes_label = QLabel('更新内容：')
            notes_label.setStyleSheet('font-size: 12px; color: #666;')
            root.addWidget(notes_label)

            notes_text = QTextEdit()
            notes_text.setReadOnly(True)
            notes_text.setPlainText(notes)
            notes_text.setMaximumHeight(80)
            notes_text.setStyleSheet('font-size: 11px; color: #555; border: 1px solid #ddd; border-radius: 4px; padding: 4px;')
            root.addWidget(notes_text)

            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            self._update_btn = QPushButton('立即更新')
            self._update_btn.setStyleSheet("""
                QPushButton { background-color: rgba(64, 158, 255, 200); color: white; padding: 8px 24px; border: none; border-radius: 4px; font-size: 13px; }
                QPushButton:hover { background-color: rgba(64, 158, 255, 240); }
            """)
            self._update_btn.clicked.connect(self._start_update)
            btn_layout.addWidget(self._update_btn)

            close_btn = QPushButton('取消')
            close_btn.setStyleSheet("""
                QPushButton { background: transparent; color: #666; padding: 8px 16px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; }
                QPushButton:hover { border-color: #999; }
            """)
            close_btn.clicked.connect(self.close)
            btn_layout.addWidget(close_btn)
            root.addLayout(btn_layout)
        else:
            text = f'当前版本：<span style="color:#999">v{current_version}</span><br>最新版本：<span style="color:#52c41a;font-weight:bold">v{current_version}</span>'
            info.setText(text)
            info.setStyleSheet('font-size: 13px; padding: 12px 0;')
            root.addWidget(info)

            ok_msg = QLabel('✓ 已是最新版本')
            ok_msg.setStyleSheet('font-size: 14px; color: #52c41a; font-weight: bold; padding: 8px 0;')
            root.addWidget(ok_msg)

            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            close_btn = QPushButton('确定')
            close_btn.setStyleSheet("""
                QPushButton { background-color: rgba(64, 158, 255, 200); color: white; padding: 8px 24px; border: none; border-radius: 4px; font-size: 13px; }
                QPushButton:hover { background-color: rgba(64, 158, 255, 240); }
            """)
            close_btn.clicked.connect(self.close)
            btn_layout.addWidget(close_btn)
            root.addLayout(btn_layout)

    def _start_update(self):
        self._update_btn.setEnabled(False)
        self._update_btn.setText('下载中...')
        QApplication.processEvents()
        threading.Thread(target=self._do_download, daemon=True).start()

    def _do_download(self):
        api_url = 'https://api.github.com/repos/ace-yong/AniFlow/releases/latest'
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'AniFlow/1.0', 'Accept': 'application/vnd.github.v3+json'})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read().decode('utf-8'))
            for asset in data.get('assets', []):
                if asset.get('name', '').endswith('.exe'):
                    self._download_url = asset['browser_download_url']
                    break
            if not self._download_url:
                return
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            tmp_path = os.path.join(exe_dir, 'AniFlow_update.exe')
            urllib.request.urlretrieve(self._download_url, tmp_path)
            new_exe = os.path.join(exe_dir, 'AniFlow.exe')
            updater = os.path.join(exe_dir, 'update.bat')
            with open(updater, 'w', encoding='utf-8') as f:
                f.write(f'''@echo off
chcp 65001 >nul
:wait
tasklist /FI "IMAGENAME eq AniFlow.exe" 2>nul | find /I /N "AniFlow.exe" >nul
if %errorlevel% equ 0 (
    timeout /t 1 /nobreak >nul
    goto wait
)
move /Y "{tmp_path}" "{new_exe}" >nul
start "" "{new_exe}"
del "%~f0"
''')
            os.startfile(updater)
            sys.exit(0)
        except Exception as e:
            self._update_btn.setEnabled(True)
            self._update_btn.setText('下载失败')


# 配置对话框（选项卡：顺序执行 + 工具路径）
class ConfigDialog(QDialog):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle('配置')
        self.setMinimumWidth(540)
        self.setMinimumHeight(420)
        self.setStyleSheet("""
            QDialog { background-color: rgb(238, 240, 245); }
            QLabel, QCheckBox, QPushButton, QLineEdit {
                font-family: "Segoe UI", "Microsoft YaHei";
            }
        """)

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(0, 4, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.seq_tab = _SequenceTab(self.config_manager)
        self.tools_tab = _ToolsTab(self.config_manager)
        self.sys_tab = _SystemTab(self.config_manager)
        self.tabs.addTab(self.seq_tab, '工具配置')
        self.tabs.addTab(self.tools_tab, '工具路径')
        self.tabs.addTab(self.sys_tab, '系统配置')
        root.addWidget(self.tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(24, 12, 24, 16)
        btn_row.addStretch()
        ok_btn = QPushButton('确定')
        ok_btn.setFont(QFont('Segoe UI', 12))
        ok_btn.setStyleSheet("""
            QPushButton { background-color: rgb(64, 158, 255); color: white; padding: 7px 28px; border: none; border-radius: 5px; }
            QPushButton:hover { background-color: rgb(96, 184, 255); }
        """)
        ok_btn.clicked.connect(self._save)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    def _save(self):
        if self.config_manager:
            self.config_manager.set_sequence(self.seq_tab.get_selected())
            self.tools_tab.save(self.config_manager)
            self.sys_tab.save(self.config_manager)
        self.accept()


class _SequenceTab(QWidget):
    """顺序执行配置选项卡"""
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(12)

        title = QLabel('执行顺序配置')
        title.setFont(QFont('Segoe UI', 15, QFont.Bold))
        title.setStyleSheet('color: #1a1a1a;')
        layout.addWidget(title)

        desc = QLabel('勾选的工具将按列表顺序依次执行。使用右侧按钮调整顺序，取消勾选则跳过。')
        desc.setStyleSheet('color: #888; font-size: 12px;')
        desc.setWordWrap(True)
        layout.addWidget(desc)

        list_row = QHBoxLayout()
        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.InternalMove)
        self._list.setDefaultDropAction(Qt.MoveAction)
        self._list.setStyleSheet("""
            QListWidget { background: white; border: 1px solid #e0e0e0; border-radius: 6px; outline: none; }
            QListWidget::item { border-bottom: 1px solid #f0f0f0; padding: 2px 0; }
            QListWidget::item:selected { background: rgba(64, 158, 255, 0.08); }
        """)
        list_row.addWidget(self._list, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)
        self._up_btn = QPushButton('▲ 上移')
        self._up_btn.setFont(QFont('Segoe UI', 11))
        self._up_btn.clicked.connect(self._move_up)
        self._up_btn.setStyleSheet("""
            QPushButton { background: white; color: #333; padding: 6px 12px; border: 1px solid #d0d0d0; border-radius: 4px; }
            QPushButton:hover { border-color: rgb(64, 158, 255); color: rgb(64, 158, 255); }
        """)
        self._down_btn = QPushButton('▼ 下移')
        self._down_btn.setFont(QFont('Segoe UI', 11))
        self._down_btn.clicked.connect(self._move_down)
        self._down_btn.setStyleSheet("""
            QPushButton { background: white; color: #333; padding: 6px 12px; border: 1px solid #d0d0d0; border-radius: 4px; }
            QPushButton:hover { border-color: rgb(64, 158, 255); color: rgb(64, 158, 255); }
        """)
        btn_col.addWidget(self._up_btn)
        btn_col.addWidget(self._down_btn)
        btn_col.addStretch()
        list_row.addLayout(btn_col)
        layout.addLayout(list_row, 1)

        self._avail = {
            'onedragon': 'OneDragon（绝区零无头模式）',
            'maaend': 'MaaEnd（终末地）',
        }
        current = self.config_manager.get_sequence() if self.config_manager else ['onedragon', 'maaend']
        for key in current:
            self._add_item(key, True)
        for key in self._avail:
            if key not in current:
                self._add_item(key, False)

    def _add_item(self, key, checked=True):
        label = self._avail.get(key, key)
        item = QListWidgetItem()
        item.setData(Qt.UserRole, key)
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(8, 4, 8, 4)
        cb = QCheckBox(label)
        cb.setChecked(checked)
        cb.setFont(QFont('Segoe UI', 13))
        cb.setStyleSheet('padding: 2px 0;')
        row.addWidget(cb)
        row.addStretch()
        item.setSizeHint(QSize(0, 36))
        self._list.addItem(item)
        self._list.setItemWidget(item, widget)

    def _rebuild(self, items):
        self._list.clear()
        for key, checked in items:
            self._add_item(key, checked)

    def _collect(self):
        data = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            key = item.data(Qt.UserRole)
            w = self._list.itemWidget(item)
            cb = w.findChild(QCheckBox)
            data.append((key, cb.isChecked() if cb else True))
        return data

    def _move_up(self):
        row = self._list.currentRow()
        if row > 0:
            data = self._collect()
            data[row], data[row - 1] = data[row - 1], data[row]
            self._rebuild(data)
            self._list.setCurrentRow(row - 1)

    def _move_down(self):
        row = self._list.currentRow()
        if row >= 0 and row < self._list.count() - 1:
            data = self._collect()
            data[row], data[row + 1] = data[row + 1], data[row]
            self._rebuild(data)
            self._list.setCurrentRow(row + 1)

    def get_selected(self):
        result = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            key = item.data(Qt.UserRole)
            w = self._list.itemWidget(item)
            cb = w.findChild(QCheckBox)
            if cb and cb.isChecked():
                result.append(key)
        return result


class _ToolsTab(QWidget):
    """工具路径配置选项卡"""
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager
        s = config_manager.settings if config_manager else {}
        od = s.get('onedragon', {})
        ma = s.get('maaend', {})

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(12)

        title = QLabel('工具路径设置')
        title.setFont(QFont('Segoe UI', 15, QFont.Bold))
        title.setStyleSheet('color: #1a1a1a;')
        layout.addWidget(title)

        desc = QLabel('配置各工具的路径，可手动填写、检测本地安装，或下载安装。')
        desc.setStyleSheet('color: #888; font-size: 12px;')
        desc.setWordWrap(True)
        layout.addWidget(desc)

        def make_row(label_text, default_val):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFont(QFont('Segoe UI', 11))
            lbl.setStyleSheet('color: #333;')
            lbl.setFixedWidth(90)
            row.addWidget(lbl)
            ed = QLineEdit(default_val)
            ed.setFont(QFont('Consolas', 10))
            ed.setStyleSheet("padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; background: #fafafa;")
            row.addWidget(ed, 1)
            self._last_row = row
            return lbl, ed

        from PyQt5.QtWidgets import QComboBox

        def make_drive_combo():
            cb = QComboBox()
            cb.setFont(QFont('Segoe UI', 10))
            cb.setStyleSheet("QComboBox { padding: 3px 8px; border: 1px solid #ccc; border-radius: 4px; min-width: 80px; } QComboBox:hover { border-color: rgb(64,158,255); }")
            cb.addItem('全部盘符')
            for d in range(ord('C'), ord('Z') + 1):
                letter = chr(d)
                if os.path.exists(f'{letter}:\\'):
                    cb.addItem(f'{letter}:\\')
            return cb

        def get_drives(cb):
            t = cb.currentText()
            return None if t == '全部盘符' else [t.rstrip('\\') + '\\']

        # OneDragon
        od_group = QGroupBox('OneDragon（绝区零）')
        od_group.setFont(QFont('Segoe UI', 12, QFont.Bold))
        od_group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #e0e0e0; border-radius: 6px; margin-top: 10px; padding: 16px 12px 12px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)
        od_layout = QVBoxLayout(od_group)
        od_layout.setSpacing(8)

        scan_od_row = QHBoxLayout()
        od_drive_cb = make_drive_combo()
        scan_od_row.addWidget(od_drive_cb)
        scan_od_btn = QPushButton('扫描')
        scan_od_btn.setFont(QFont('Segoe UI', 11))
        scan_od_btn.setStyleSheet("""
            QPushButton { background: rgb(64,158,255); color: white; padding: 4px 16px; border: none; border-radius: 4px; }
            QPushButton:hover { background: rgb(96,184,255); }
        """)
        scan_od_btn.clicked.connect(lambda: self._scan_od(od_drive_cb))
        scan_od_row.addWidget(scan_od_btn)
        scan_od_row.addStretch()
        od_layout.addLayout(scan_od_row)

        lbl, self.od_path = make_row('脚本路径', od.get('path', ''))
        od_layout.addLayout(self._last_row)

        lbl, self.od_python = make_row('Python 路径', od.get('python_path', ''))
        od_layout.addLayout(self._last_row)

        dl_od = QPushButton('📥 下载并安装 OneDragon (Gitee)')
        dl_od.setFont(QFont('Segoe UI', 11))
        dl_od.setStyleSheet("""
            QPushButton { background: rgba(64,158,255,0.1); color: rgb(64,158,255); padding: 6px 12px; border: 1px solid rgba(64,158,255,0.3); border-radius: 4px; }
            QPushButton:hover { background: rgba(64,158,255,0.2); }
        """)
        dl_od.clicked.connect(lambda: self._download_onedragon(dl_od))
        od_layout.addWidget(dl_od)
        layout.addWidget(od_group)

        # MaaEnd
        ma_group = QGroupBox('MaaEnd（终末地）')
        ma_group.setFont(QFont('Segoe UI', 12, QFont.Bold))
        ma_group.setStyleSheet(od_group.styleSheet())
        ma_layout = QVBoxLayout(ma_group)
        ma_layout.setSpacing(8)

        scan_ma_row = QHBoxLayout()
        ma_drive_cb = make_drive_combo()
        scan_ma_row.addWidget(ma_drive_cb)
        scan_ma_btn = QPushButton('扫描')
        scan_ma_btn.setFont(QFont('Segoe UI', 11))
        scan_ma_btn.setStyleSheet(scan_od_btn.styleSheet())
        scan_ma_btn.clicked.connect(lambda: self._scan_ma(ma_drive_cb))
        scan_ma_row.addWidget(scan_ma_btn)
        scan_ma_row.addStretch()
        ma_layout.addLayout(scan_ma_row)

        lbl, self.ma_path = make_row('程序路径', ma.get('path', ''))
        ma_layout.addLayout(self._last_row)

        dl_ma = QPushButton('📥 下载并安装 MaaEnd (GitHub)')
        dl_ma.setFont(QFont('Segoe UI', 11))
        dl_ma.setStyleSheet("""
            QPushButton { background: rgba(114,46,209,0.1); color: rgb(114,46,209); padding: 6px 12px; border: 1px solid rgba(114,46,209,0.3); border-radius: 4px; }
            QPushButton:hover { background: rgba(114,46,209,0.2); }
        """)
        dl_ma.clicked.connect(lambda: self._download_maaend(dl_ma))
        ma_layout.addWidget(dl_ma)
        layout.addWidget(ma_group)
        layout.addStretch()

        self._status = QLabel('')
        self._status.setStyleSheet('color: #888; font-size: 11px; border: none;')
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

    def _browse_file(self, edit, filter_str):
        path, _ = QFileDialog.getOpenFileName(self, '选择文件', '', filter_str)
        if path:
            edit.setText(path)

    def _scan_od(self, drive_cb):
        self._status.setText('正在扫描 OneDragon...')
        QApplication.processEvents()
        drives = None if drive_cb.currentText() == '全部盘符' else [drive_cb.currentText().rstrip('\\') + '\\']
        od_path = self._detect_od_path(drives)
        if od_path:
            self.od_path.setText(od_path)
            py_path = self._detect_od_python(drives)
            if py_path:
                self.od_python.setText(py_path)
            self._status.setText('已找到 OneDragon')
        else:
            self._status.setText('未扫描到 OneDragon')

    def _scan_ma(self, drive_cb):
        self._status.setText('正在扫描 MaaEnd...')
        QApplication.processEvents()
        drives = None if drive_cb.currentText() == '全部盘符' else [drive_cb.currentText().rstrip('\\') + '\\']
        ma_path = self._detect_ma_path(drives)
        if ma_path:
            self.ma_path.setText(ma_path)
            self._status.setText('已找到 MaaEnd')
        else:
            self._status.setText('未扫描到 MaaEnd')

    @staticmethod
    def _search_deep(roots, targets, max_depth=2):
        """在 roots 目录列表中递归搜索最多 max_depth 层，返回第一个匹配 target 文件的路径"""
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
                except PermissionError:
                    continue
        return ''

    def _detect_od_path(self, drives=None):
        from collections import deque
        if drives is None:
            drives = ['E:\\']
        roots = list(drives)
        roots.append(os.path.expanduser('~'))
        # 先搜 onedragon 目录名，再在里面找 app.py
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
                except PermissionError:
                    continue
        return ''

    def _detect_od_python(self, drives=None):
        od_path = self._detect_od_path(drives)
        if not od_path:
            return ''
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(od_path))))
        for py in ['pythonw.exe', 'python.exe']:
            p = os.path.join(base, '.venv', 'Scripts', py)
            if os.path.isfile(p):
                return p
        return ''

    def _detect_ma_path(self, drives=None):
        if drives is None:
            drives = ['E:\\']
        roots = list(drives)
        roots.append(os.path.expanduser('~'))
        return self._search_deep(roots, {'MaaEnd.exe'}, 5)

    def _get_base_dir(self):
        return _app_dir()

    def _download_onedragon(self, btn):
        self._run_download(btn, 'OneDragon',
            'git clone https://gitee.com/OneDragon-Anything/ZenlessZoneZero-OneDragon.git',
            self._after_od_download)

    def _download_maaend(self, btn):
        self._run_download(btn, 'MaaEnd',
            'github',  # special marker
            self._after_ma_download)

    def _run_download(self, btn, name, cmd, after_cb):
        def task():
            btn.setEnabled(False)
            orig = btn.text()
            btn.setText(f'⏳ 正在下载 {name}...')
            self._status.setText(f'开始下载 {name}...')
            QApplication.processEvents()
            try:
                base_dir = self._get_base_dir()
                target = os.path.join(base_dir, 'tools', name)
                if cmd == 'github':
                    self._status.setText('正在获取 MaaEnd 最新版本信息...')
                    QApplication.processEvents()
                    req = urllib.request.Request(
                        'https://api.github.com/repos/MaaXYZ/MaaEnd/releases/latest',
                        headers={'User-Agent': 'AniFlow/1.0'}
                    )
                    resp = urllib.request.urlopen(req, timeout=15)
                    data = json.loads(resp.read().decode())
                    asset = None
                    for a in data.get('assets', []):
                        if a['name'].endswith('.zip') and 'win' in a['name'].lower():
                            asset = a
                            break
                    if not asset:
                        raise Exception('未找到 Windows 版本下载文件')
                    dl_url = asset['browser_download_url']
                    self._status.setText(f'正在下载 {asset["name"]}...')
                    QApplication.processEvents()
                    resp = urllib.request.urlopen(dl_url, timeout=60)
                    z = zipfile.ZipFile(io.BytesIO(resp.read()))
                    target = os.path.join(self._get_base_dir(), 'tools', 'MaaEnd')
                    os.makedirs(target, exist_ok=True)
                    z.extractall(target)
                    exe_path = os.path.join(target, 'MaaEnd.exe')
                    if os.path.isfile(exe_path):
                        self.ma_path.setText(exe_path)
                else:
                    self._status.setText(f'正在运行: {cmd} -> {target}...')
                    QApplication.processEvents()
                    env = os.environ.copy()
                    env['GIT_TERMINAL_PROMPT'] = '0'
                    subprocess.run(cmd.split() + [target], check=True, timeout=300, capture_output=True, env=env)
                    after_cb(target)
                self._status.setText(f'{name} 下载完成！路径已自动填入。')
            except Exception as e:
                self._status.setText(f'{name} 下载失败: {e}')
            finally:
                btn.setText(orig)
                btn.setEnabled(True)
        threading.Thread(target=task, daemon=True).start()

    def _after_od_download(self, target):
        py_path = os.path.join(target, '.venv', 'Scripts', 'pythonw.exe')
        if not os.path.isfile(py_path):
            self._status.setText('正在安装 OneDragon 依赖 (uv sync)...')
            QApplication.processEvents()
            try:
                subprocess.run(['uv', 'sync'], cwd=target, check=True, timeout=300, capture_output=True)
            except Exception:
                try:
                    subprocess.run(['pip', 'install', '-r', 'requirements.txt'], cwd=target, check=True, timeout=300, capture_output=True)
                except Exception as e:
                    self._status.setText(f'依赖安装失败，请手动运行 uv sync: {e}')
                    return
        app_path = os.path.join(target, 'src', 'zzz_od', 'gui', 'app.py')
        if os.path.isfile(app_path):
            self.od_path.setText(app_path)
        for py in ['pythonw.exe', 'python.exe']:
            p = os.path.join(target, '.venv', 'Scripts', py)
            if os.path.isfile(p):
                self.od_python.setText(p)
                break

    def _after_ma_download(self, target):
        """MaaEnd 下载完成后的回调（下载逻辑已在 _run_download 中处理，此处仅作标识）"""
        pass

    def save(self, config_manager):
        config_manager.set_tool_settings('onedragon', {
            'path': self.od_path.text(),
            'python_path': self.od_python.text(),
        })
        config_manager.set_tool_settings('maaend', {
            'path': self.ma_path.text(),
        })


class _SystemTab(QWidget):
    """系统配置选项卡"""
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager
        action = config_manager.get_post_action() if config_manager else 'close_game'

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(12)

        title = QLabel('系统配置')
        title.setFont(QFont('Segoe UI', 15, QFont.Bold))
        title.setStyleSheet('color: #1a1a1a;')
        layout.addWidget(title)

        desc = QLabel('一键运行全部任务完成后的操作。')
        desc.setStyleSheet('color: #888; font-size: 12px;')
        desc.setWordWrap(True)
        layout.addWidget(desc)

        group = QGroupBox('执行完成后')
        group.setFont(QFont('Segoe UI', 12, QFont.Bold))
        group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #e0e0e0; border-radius: 6px; margin-top: 10px; padding: 20px 16px 16px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
        """)
        glayout = QVBoxLayout(group)
        glayout.setSpacing(10)

        self._radio_none = QRadioButton('不执行任何操作')
        self._radio_close = QRadioButton('关闭游戏')
        self._radio_shutdown = QRadioButton('关机')
        for rb in (self._radio_none, self._radio_close, self._radio_shutdown):
            rb.setFont(QFont('Segoe UI', 12))
            rb.setStyleSheet('color: #333;')

        action_map = {'none': self._radio_none, 'close_game': self._radio_close, 'shutdown': self._radio_shutdown}
        rb = action_map.get(action, self._radio_close)
        rb.setChecked(True)

        glayout.addWidget(self._radio_none)
        glayout.addWidget(self._radio_close)
        glayout.addWidget(self._radio_shutdown)
        layout.addWidget(group)
        layout.addStretch()

    def save(self, config_manager):
        if self._radio_none.isChecked():
            config_manager.set_post_action('none')
        elif self._radio_close.isChecked():
            config_manager.set_post_action('close_game')
        elif self._radio_shutdown.isChecked():
            config_manager.set_post_action('shutdown')


# 主窗口类
class MainWindow(QMainWindow):
    """主窗口 - 游戏卡片布局，支持独立启动/停止"""
    show_update = pyqtSignal(str, str, str, str)  # current, latest, release_url, notes

    def __init__(self):
        super().__init__()
        self.setWindowTitle('AniFlow')
        self.setMinimumSize(1000, 650)

        icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        _migrate_config()
        self.config_manager = ConfigManager(os.path.join(_app_dir(), 'config'))
        self.game_manager = GameProcessManager(self.config_manager)
        self.game_manager.status_changed.connect(self._on_game_status)
        self.show_update.connect(self._show_update_dialog)
        self.game_manager.log_message.connect(self.add_log)
        self.game_manager.tool_output.connect(self._on_tool_output)
        self._init_log_file()

        self._setup_ui()
        self._setup_background()
        self._apply_style()

        self.add_log(f'AniFlow v{VERSION} 启动', 'INFO')
        self.add_log(f'数据目录: {_app_dir()}', 'INFO')
        self.add_log(f'配置目录: {os.path.join(_app_dir(), "config")}', 'INFO')
        settings = self.config_manager.settings
        od_path = settings.get('onedragon', {}).get('path', '')
        me_path = settings.get('maaend', {}).get('path', '')
        self.add_log(f'OneDragon 路径: {od_path or "未配置"}', 'INFO')
        self.add_log(f'MaaEnd 路径: {me_path or "未配置"}', 'INFO')
        self.add_log(f'执行顺序: {settings.get("sequence", [])}', 'INFO')

    # ---------- background ----------
    def _setup_background(self):
        path = r'D:\壁纸\二次元\001 (19).jpg'
        if not os.path.exists(path):
            path = os.path.join(os.path.dirname(__file__), 'wallpaper_source.jpg')
            if not os.path.exists(path):
                return
        pix = QPixmap(path)
        if pix.isNull():
            return
        self._bg_label = QLabel(self.centralWidget())
        self._bg_label.setGeometry(self.centralWidget().rect())
        self._bg_pixmap = pix
        self._update_bg()
        self._bg_label.lower()

    def _update_bg(self):
        if not hasattr(self, '_bg_label') or not self._bg_label:
            return
        scaled = self._bg_pixmap.scaled(
            self.centralWidget().size(),
            Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self._bg_label.setPixmap(scaled)
        self._bg_label.setGeometry(self.centralWidget().rect())
        effect = QGraphicsOpacityEffect(self._bg_label)
        effect.setOpacity(0.45)
        self._bg_label.setGraphicsEffect(effect)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_bg()

    # ---------- style ----------
    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: transparent; }
            QGroupBox { font-weight: bold; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; margin-top: 14px; padding-top: 18px; background: rgba(255,255,255,60); }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 10px; color: #111; font-size: 13px; }
            QTreeWidget { border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; background: rgba(255,255,255,60); }
            QTextEdit { border: 1px solid rgba(255,255,255,0.12); border-radius: 6px; font-family: 'Cascadia Code', 'Consolas', monospace; background: rgba(255,255,255,50); color: #222; font-size: 12px; padding: 6px; }
            QLabel { color: #222; font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC'; }
            QStatusBar { background: rgba(255,255,255,80); border-top: 1px solid rgba(255,255,255,0.15); font-size: 12px; color: #555; }
        """)

    # ---------- UI setup ----------
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 8, 12, 8)

        # === 工具栏 ===
        toolbar = QHBoxLayout()

        btn_font = QFont('Segoe UI', 13, QFont.Bold)

        self.run_seq_btn = QPushButton('▶ 一键运行')
        self.run_seq_btn.setFont(btn_font)
        self.run_seq_btn.setStyleSheet("""
            QPushButton { background-color: rgba(64, 158, 255, 200); color: white; padding: 9px 28px; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: rgba(64, 158, 255, 240); }
            QPushButton:disabled { background-color: rgba(200, 200, 200, 150); color: rgba(255, 255, 255, 180); }
            QPushButton:pressed { background-color: rgba(48, 128, 220, 220); }
        """)
        self.run_seq_btn.clicked.connect(self._run_sequence)
        toolbar.addWidget(self.run_seq_btn)

        self.stop_seq_btn = QPushButton('■ 停止')
        self.stop_seq_btn.setFont(btn_font)
        self.stop_seq_btn.setStyleSheet("""
            QPushButton { background-color: rgba(255, 77, 79, 200); color: white; padding: 9px 22px; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: rgba(255, 77, 79, 240); }
            QPushButton:disabled { background-color: rgba(224, 224, 224, 150); color: rgba(200, 200, 200, 180); }
            QPushButton:pressed { background-color: rgba(217, 54, 62, 220); }
        """)

        self.stop_seq_btn.setEnabled(False)
        self.stop_seq_btn.clicked.connect(self._stop_sequence)
        toolbar.addWidget(self.stop_seq_btn)

        self.seq_config_btn = QPushButton('⚙ 配置')
        self.seq_config_btn.setFont(QFont('Segoe UI', 12))
        self.seq_config_btn.setStyleSheet("""
            QPushButton { background-color: rgba(255,255,255,180); color: #555; padding: 7px 14px; border: 1px solid rgba(255,255,255,0.4); border-radius: 6px; }
            QPushButton:hover { border-color: rgba(64, 158, 255, 200); color: rgb(64, 158, 255); }
        """)
        self.seq_config_btn.clicked.connect(self._open_seq_config)
        toolbar.addWidget(self.seq_config_btn)

        self.seq_status_label = QLabel('')
        self.seq_status_label.setStyleSheet('color: #999; font-size: 12px; padding: 0 12px; font-family: "Segoe UI", "Microsoft YaHei";')
        toolbar.addWidget(self.seq_status_label)

        toolbar.addStretch()

        self._version_label = QLabel(f'v{VERSION}')
        self._version_label.setStyleSheet('color: #999; font-size: 12px; padding: 0 8px; font-family: "Segoe UI", "Microsoft YaHei";')
        toolbar.addWidget(self._version_label)

        self._check_update_btn = QPushButton('检查更新')
        self._check_update_btn.setFont(QFont('Segoe UI', 12))
        self._check_update_btn.setStyleSheet("""
            QPushButton { background-color: rgba(255,255,255,180); color: #555; padding: 7px 14px; border: 1px solid rgba(255,255,255,0.4); border-radius: 6px; font-size: 12px; }
            QPushButton:hover { border-color: rgba(64, 158, 255, 200); color: rgb(64, 158, 255); }
            QPushButton:disabled { color: #ccc; }
        """)
        self._check_update_btn.clicked.connect(self._check_update)
        toolbar.addWidget(self._check_update_btn)

        root.addLayout(toolbar)

        # === 主区域: 左侧列表 + 右侧日志 ===
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(0)
        splitter.setChildrenCollapsible(False)

        # -- 左侧工具列表 --
        side_widget = QWidget()
        side_widget.setStyleSheet('background: rgba(255,255,255,80); border-radius: 8px;')
        side_layout = QVBoxLayout(side_widget)
        side_layout.setSpacing(4)
        side_layout.setContentsMargins(8, 8, 8, 8)

        self._tool_items = {}
        tool_defs = [
            ('zenless_zone_zero', '绝区零', 'OneDragon', 'rgb(64, 158, 255)'),
            ('endfield', '终末地', 'MaaEnd', 'rgb(114, 46, 209)'),
        ]
        for gt, title, tool_name, accent in tool_defs:
            item = self._build_side_item(gt, title, tool_name, accent)
            self._tool_items[gt] = item
            side_layout.addWidget(item['frame'])

        side_layout.addStretch()

        # -- 底部 全部打开/全部关闭 --
        all_row = QHBoxLayout()
        self.start_all_btn = QPushButton('全部打开')
        self.start_all_btn.setFont(QFont('Segoe UI', 12, QFont.Bold))
        self.start_all_btn.setStyleSheet("""
            QPushButton { background-color: rgba(82, 196, 26, 200); color: white; padding: 9px 0; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: rgba(82, 196, 26, 240); }
            QPushButton:pressed { background-color: rgba(69, 168, 24, 220); }
        """)
        self.start_all_btn.clicked.connect(self._start_all)
        all_row.addWidget(self.start_all_btn)

        self.stop_all_btn = QPushButton('全部关闭')
        self.stop_all_btn.setFont(QFont('Segoe UI', 12, QFont.Bold))
        self.stop_all_btn.setStyleSheet("""
            QPushButton { background-color: rgba(255, 77, 79, 200); color: white; padding: 9px 0; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: rgba(255, 77, 79, 240); }
            QPushButton:pressed { background-color: rgba(217, 54, 62, 220); }
        """)
        self.stop_all_btn.clicked.connect(self._stop_all)
        all_row.addWidget(self.stop_all_btn)
        side_layout.addLayout(all_row)

        splitter.addWidget(side_widget)

        # -- 右侧日志 --
        log_widget = QWidget()
        log_widget.setStyleSheet('background: rgba(255,255,255,70); border-radius: 8px;')
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_header = QHBoxLayout()
        log_title = QLabel('执行日志')
        log_title.setFont(QFont('Segoe UI', 13, QFont.Bold))
        log_header.addWidget(log_title)
        log_header.addStretch()
        btn_box = QHBoxLayout()
        btn_box.setSpacing(6)
        clr_btn = QPushButton('清空')
        clr_btn.setFont(QFont('Segoe UI', 11))
        clr_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,180); color: #555; padding: 4px 12px; border: 1px solid rgba(255,255,255,0.4); border-radius: 4px; }
            QPushButton:hover { border-color: rgb(255, 77, 79); color: rgb(255, 77, 79); }
        """)
        clr_btn.clicked.connect(lambda: self.log_text.clear())
        btn_box.addWidget(clr_btn)
        log_btn = QPushButton('📋 日志目录')
        log_btn.setFont(QFont('Segoe UI', 11))
        log_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,180); color: #555; padding: 4px 12px; border: 1px solid rgba(255,255,255,0.4); border-radius: 4px; }
            QPushButton:hover { border-color: rgba(64, 158, 255, 200); color: rgb(64, 158, 255); }
        """)
        log_btn.clicked.connect(self.open_log_folder)
        btn_box.addWidget(log_btn)
        log_header.addLayout(btn_box)
        log_layout.addLayout(log_header)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text, 1)
        self.log_text.setStyleSheet('background: rgba(255,255,255,50); border: none; border-radius: 4px; font-family: "Cascadia Code", "Consolas", monospace; font-size: 12px; color: #222; padding: 6px;')
        splitter.addWidget(log_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        splitter.setSizes([280, 700])
        root.addWidget(splitter, 1)

        self.statusBar().showMessage('就绪')

    def _build_side_item(self, game_type, title, tool_name, accent):
        """构建左侧列表中的一个工具条目"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(255,255,255,80);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 6px;
                border-left: 3px solid {accent};
            }}
            QFrame:hover {{
                background: rgba(255,255,255,120);
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 8, 12, 10)

        # 标题行: 名称 + 工具名
        header = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont('Segoe UI', 14, QFont.Bold))
        title_lbl.setStyleSheet(f'color: {accent}; background: transparent; border: none;')
        header.addWidget(title_lbl)
        header.addStretch()
        tool_lbl = QLabel(tool_name)
        tool_lbl.setFont(QFont('Segoe UI', 10))
        tool_lbl.setStyleSheet(f'color: {accent}; background: rgba(64,158,255,0.08); padding: 1px 8px; border-radius: 8px; font-weight: 600; border: none;')
        header.addWidget(tool_lbl)
        layout.addLayout(header)

        # 状态行
        status_row = QHBoxLayout()
        indicator = QLabel('●')
        indicator.setFont(QFont('Segoe UI', 12))
        indicator.setStyleSheet('color: #bbb; background: transparent; border: none;')
        status_row.addWidget(indicator)
        status_lbl = QLabel('已停止')
        status_lbl.setFont(QFont('Segoe UI', 11))
        status_lbl.setStyleSheet('color: #999; background: transparent; border: none;')
        status_row.addWidget(status_lbl)
        status_row.addStretch()
        layout.addLayout(status_row)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        start_btn = QPushButton('打开')
        start_btn.setFont(QFont('Segoe UI', 11, QFont.Bold))
        start_btn.setStyleSheet("""
            QPushButton { background: rgba(82, 196, 26, 200); color: white; padding: 7px 0; border: none; border-radius: 5px; }
            QPushButton:hover { background: rgba(82, 196, 26, 240); }
            QPushButton:pressed { background: rgba(69, 168, 24, 220); }
            QPushButton:disabled { background: rgba(217, 217, 217, 150); color: rgba(200,200,200,180); }
        """)
        stop_btn = QPushButton('关闭')
        stop_btn.setFont(QFont('Segoe UI', 11, QFont.Bold))
        stop_btn.setStyleSheet("""
            QPushButton { background: rgba(255, 77, 79, 200); color: white; padding: 7px 0; border: none; border-radius: 5px; }
            QPushButton:hover { background: rgba(255, 77, 79, 240); }
            QPushButton:pressed { background: rgba(217, 54, 62, 220); }
            QPushButton:disabled { background: rgba(224, 224, 224, 150); color: rgba(200,200,200,180); }
        """)
        stop_btn.setEnabled(False)
        btn_row.addWidget(start_btn)
        btn_row.addWidget(stop_btn)
        layout.addLayout(btn_row)

        item = {
            'frame': frame,
            'indicator': indicator,
            'status_label': status_lbl,
            'start_btn': start_btn,
            'stop_btn': stop_btn,
        }
        start_btn.clicked.connect(lambda: self._start_game(game_type))
        stop_btn.clicked.connect(lambda: self._stop_game(game_type))
        self.__dict__[f'_{game_type}_card'] = item
        return item

    # ---------- sequence pipeline ----------
    def _run_sequence(self):
        self.game_manager.start_sequence()
        self.run_seq_btn.setEnabled(False)
        self.stop_seq_btn.setEnabled(True)
        self.seq_status_label.setText('执行中...')
        self.seq_status_label.setStyleSheet('color: #FF9800; font-size: 12px; padding: 0 8px; font-weight: bold;')

    def _stop_sequence(self):
        self.game_manager.stop_sequence()
        self.run_seq_btn.setEnabled(True)
        self.stop_seq_btn.setEnabled(False)
        self.seq_status_label.setText('已停止')
        self.seq_status_label.setStyleSheet('color: #f44336; font-size: 12px; padding: 0 8px;')

    def _open_seq_config(self):
        dialog = ConfigDialog(self, self.config_manager)
        dialog.exec_()

    def _check_update(self):
        self._check_update_btn.setEnabled(False)
        self._check_update_btn.setText('检查中...')
        QApplication.processEvents()
        threading.Thread(target=self._do_check_update, daemon=True).start()

    def _do_check_update(self):
        api_url = 'https://api.github.com/repos/ace-yong/AniFlow/releases/latest'
        try:
            req = urllib.request.Request(api_url, headers={'User-Agent': 'AniFlow/1.0', 'Accept': 'application/vnd.github.v3+json'})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode('utf-8'))
            latest_tag = data.get('tag_name', '').lstrip('v')
            curr = VERSION
            notes = data.get('body', '')
            release_url = data.get('html_url', '')
        except Exception:
            latest_tag = VERSION
            notes = ''
            release_url = ''
        finally:
            self._check_update_btn.setEnabled(True)
            self._check_update_btn.setText('检查更新')
        self.show_update.emit(VERSION, latest_tag, release_url, notes)

    def _show_update_dialog(self, current, latest, url, notes):
        dialog = UpdateDialog(self, current_version=current, latest_version=latest, release_url=url, notes=notes)
        dialog.exec_()

    # ---------- game control ----------
    def _start_game(self, game_type):
        card = self.__dict__.get(f'_{game_type}_card')
        if card:
            card['start_btn'].setEnabled(False)
            card['stop_btn'].setEnabled(False)
            card['indicator'].setStyleSheet('color: #FF9800;')
            card['indicator'].setText('◌')
            card['status_label'].setText('正在启动...')
            card['status_label'].setStyleSheet('color: #FF9800; font-weight: bold;')
            QApplication.processEvents()
        ok, reason = self.game_manager.start_game(game_type)
        if not ok:
            self._reset_card_ui(game_type, reason)

    def _stop_game(self, game_type):
        card = self.__dict__.get(f'_{game_type}_card')
        if card:
            card['start_btn'].setEnabled(False)
            card['stop_btn'].setEnabled(False)
            card['indicator'].setStyleSheet('color: #FF9800;')
            card['indicator'].setText('◌')
            card['status_label'].setText('正在停止...')
            card['status_label'].setStyleSheet('color: #FF9800; font-weight: bold;')
            QApplication.processEvents()
        ok, reason = self.game_manager.stop_game(game_type)
        if not ok:
            self._reset_card_ui(game_type, reason)

    def _reset_card_ui(self, game_type, status_text):
        card = self.__dict__.get(f'_{game_type}_card')
        if not card:
            return
        running = self.game_manager.is_running(game_type)
        if running:
            card['indicator'].setStyleSheet('color: #52c41a; border: none;')
            card['indicator'].setText('●')
            card['status_label'].setText('运行中')
            card['status_label'].setStyleSheet('color: #52c41a; font-weight: 600; border: none;')
            card['start_btn'].setEnabled(False)
            card['stop_btn'].setEnabled(True)
        else:
            card['indicator'].setStyleSheet('color: #bbb; border: none;')
            card['indicator'].setText('●')
            card['status_label'].setText(status_text)
            card['status_label'].setStyleSheet('color: #999; border: none;')
            card['start_btn'].setEnabled(True)
            card['stop_btn'].setEnabled(False)
            if self.game_manager.pm.all_stopped():
                self.statusBar().showMessage('就绪')

    def _start_all(self):
        for gt in ['zenless_zone_zero', 'endfield']:
            self._start_game(gt)

    def _stop_all(self):
        for gt in ['zenless_zone_zero', 'endfield']:
            self._stop_game(gt)

    def _on_game_status(self, game_type, status):
        """回调 - 由 GameProcessManager 触发"""
        if game_type == 'pipeline':
            if status == 'seq_completed':
                self.seq_status_label.setText('全部任务完成 ✓')
                self.seq_status_label.setStyleSheet('color: #4CAF50; font-size: 12px; padding: 0 8px; font-weight: bold;')
                self.run_seq_btn.setEnabled(True)
                self.stop_seq_btn.setEnabled(False)
                self.statusBar().showMessage('全部任务完成')
            elif status.startswith('seq_') and status.endswith('_running'):
                key = status[4:-8]
                labels = {'onedragon': 'OneDragon', 'maaend': 'MaaEnd'}
                label = labels.get(key, key)
                self.seq_status_label.setText(f'正在执行 {label}...')
                self.seq_status_label.setStyleSheet('color: #FF9800; font-size: 12px; padding: 0 8px; font-weight: bold;')
                self.run_seq_btn.setEnabled(False)
                self.stop_seq_btn.setEnabled(True)
            return

        card = self.__dict__.get(f'_{game_type}_card')
        if not card:
            return
        if status == 'running':
            card['indicator'].setStyleSheet('color: #52c41a; border: none;')
            card['status_label'].setText('运行中')
            card['status_label'].setStyleSheet('color: #52c41a; font-weight: 600; border: none;')
            card['start_btn'].setEnabled(False)
            card['stop_btn'].setEnabled(True)
            self.statusBar().showMessage('运行中...')
        elif status == 'stopped':
            card['indicator'].setStyleSheet('color: #bbb; border: none;')
            card['status_label'].setText('已停止')
            card['status_label'].setStyleSheet('color: #999; border: none;')
            card['start_btn'].setEnabled(True)
            card['stop_btn'].setEnabled(False)
            if self.game_manager.pm.all_stopped():
                self.statusBar().showMessage('就绪')
        elif status == 'failed':
            card['indicator'].setStyleSheet('color: #f44336;')
            card['indicator'].setText('✗')
            card['status_label'].setText('启动失败')
            card['status_label'].setStyleSheet('color: #f44336; font-weight: bold;')
            card['start_btn'].setEnabled(True)
            card['stop_btn'].setEnabled(False)
            self.statusBar().showMessage('启动失败')

    # ---------- log ----------
    def _init_log_file(self):
        self._logs_dir = os.path.join(_app_dir(), 'logs')
        os.makedirs(self._logs_dir, exist_ok=True)

    def _write_log(self, message, level='INFO'):
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_path = os.path.join(self._logs_dir, f'AniFlow_{date_str}.log')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                if f.tell() == 0:
                    f.write('\ufeff')
                f.write(f'[{timestamp}] [{level}] {message}\n')
        except Exception:
            pass

    def _on_tool_output(self, source, line):
        label_map = {
            'zenless_zone_zero': '绝区零',
            'endfield': '终末地',
            'onedragon': 'OneDragon',
            'maaend': 'MaaEnd',
        }
        label = label_map.get(source, source)
        self.add_log(f'[{label}] {line}', 'INFO')

    def add_log(self, message, level='INFO'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        colors = {'INFO': 'black', 'SUCCESS': 'green', 'WARNING': 'orange', 'ERROR': 'red'}
        color = colors.get(level, 'black')
        self.log_text.append(f'<span style="color:{color}">[{timestamp}] {message}</span>')
        self._write_log(message, level)

    # ---------- dialogs ----------
    def open_log_folder(self):
        logs_dir = os.path.join(_app_dir(), 'logs')
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        if os.name == 'nt':
            os.startfile(logs_dir)


def _ensure_admin():
    """检测并自动以管理员权限重启"""
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
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", os.path.join(script_dir, script), '', script_dir, 1
    )
    sys.exit(0)


def _log_exception(exc_type, exc_value, exc_traceback):
    """全局未捕获异常处理 - 写入日志文件"""
    msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log_dir = os.path.join(_app_dir(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f'crash_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('\ufeff')
        f.write(f'[CRASH] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'Version: {VERSION}\n')
        f.write(f'Sys.argv: {sys.argv}\n')
        f.write(f'Frozen: {getattr(sys, "frozen", False)}\n')
        f.write(f'Executable: {sys.executable if getattr(sys, "frozen", False) else __file__}\n')
        f.write(f'CWD: {os.getcwd()}\n')
        f.write(f'_app_dir: {_app_dir()}\n\n')
        import platform
        f.write(f'OS: {platform.system()} {platform.release()}\n')
        f.write(f'Python: {sys.version}\n\n')
        f.write(msg)
    print(f'程序崩溃，日志已保存: {log_path}')
    sys.exit(1)


def main():
    """主函数"""
    sys.excepthook = _log_exception
    threading.excepthook = lambda args: _log_exception(args.exc_type, args.exc_value, args.exc_traceback)
    _ensure_admin()
    log_dir = os.path.join(_app_dir(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    startup_log = os.path.join(log_dir, f'startup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    with open(startup_log, 'w', encoding='utf-8') as f:
        f.write('\ufeff')
        f.write(f'[STARTUP] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'Version: {VERSION}\n')
        f.write(f'Frozen: {getattr(sys, "frozen", False)}\n')
        f.write(f'Executable: {sys.executable if getattr(sys, "frozen", False) else __file__}\n')
        f.write(f'CWD: {os.getcwd()}\n')
        f.write(f'_app_dir: {_app_dir()}\n')
        f.write(f'Config dir: {os.path.join(_app_dir(), "config")}\n')
        import platform
        f.write(f'OS: {platform.system()} {platform.release()} {platform.version()}\n')
        f.write(f'Python: {sys.version}\n')
    try:
        cfg_dir = os.path.join(_app_dir(), 'config')
        if not os.path.exists(cfg_dir):
            os.makedirs(cfg_dir)
        
        import PyQt5.QtCore
        qt_plugin_path = os.path.join(os.path.dirname(PyQt5.QtCore.__file__), 'Qt5', 'plugins', 'platforms')
        if os.path.isdir(qt_plugin_path):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
        elif getattr(sys, 'frozen', False):
            # PyInstaller onefile: plugins are in _MEIPASS/PyQt5/Qt5/plugins
            meipass = getattr(sys, '_MEIPASS', '')
            if meipass:
                p = os.path.join(meipass, 'PyQt5', 'Qt5', 'plugins', 'platforms')
                if os.path.isdir(p):
                    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = p
        
        print("正在启动GUI...")
        
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        print("创建主窗口...")
        window = MainWindow()
        window.show()
        
        print("GUI启动成功！")
        
        sys.exit(app.exec_())
    except Exception as e:
        print(f"错误: {e}")
        traceback.print_exc()
        input("按任意键退出...")
        sys.exit(1)


if __name__ == '__main__':
    main()