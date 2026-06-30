import json
import os
from typing import Dict, List, Any


class AccountConfig:
    def __init__(self, config_data: Dict[str, Any]):
        self.id = config_data['id']
        self.name = config_data['name']
        self.game_path = config_data['game_path']
        self.config_path = config_data.get('config_path', '')
        self.tasks = config_data.get('tasks', [])
        self.enabled = config_data.get('enabled', True)
        self.priority = config_data.get('priority', 1)


class ConfigManager:
    def __init__(self, config_dir: str = 'config'):
        self.config_dir = config_dir
        self.accounts_file = os.path.join(config_dir, 'accounts.json')
        self.settings_file = os.path.join(config_dir, 'settings.json')
        self.accounts = self._load_accounts()
        self.settings = self._load_settings()

    def _load_accounts(self) -> Dict[str, List[AccountConfig]]:
        if os.path.exists(self.accounts_file):
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'zenless_zone_zero': [AccountConfig(a) for a in data.get('zenless_zone_zero', [])],
                    'endfield': [AccountConfig(a) for a in data.get('endfield', [])]
                }
        return {'zenless_zone_zero': [], 'endfield': []}

    def _load_settings(self) -> Dict[str, Any]:
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_enabled_accounts(self, game_type: str) -> List[AccountConfig]:
        accounts = self.accounts.get(game_type, [])
        return sorted([a for a in accounts if a.enabled], key=lambda x: x.priority)

    def get_all_accounts(self) -> List[AccountConfig]:
        all_accounts = []
        for game_type in ['zenless_zone_zero', 'endfield']:
            all_accounts.extend(self.accounts.get(game_type, []))
        return sorted(all_accounts, key=lambda x: x.priority)

    def get_tool_path(self, tool_name: str) -> str:
        return self.settings.get('tools', {}).get(tool_name, {}).get('path', '')

    def get_tool_settings(self, tool_name: str) -> Dict[str, Any]:
        return self.settings.get('tools', {}).get(tool_name, {})

    def get_execution_settings(self) -> Dict[str, Any]:
        return self.settings.get('execution', {})

    def get_schedule_settings(self) -> Dict[str, Any]:
        return self.settings.get('schedule', {})

    def get_logging_settings(self) -> Dict[str, Any]:
        return self.settings.get('logging', {})

    def save_accounts(self):
        data = {
            'zenless_zone_zero': [
                {
                    'id': a.id,
                    'name': a.name,
                    'game_path': a.game_path,
                    'config_path': a.config_path,
                    'tasks': a.tasks,
                    'enabled': a.enabled,
                    'priority': a.priority
                } for a in self.accounts['zenless_zone_zero']
            ],
            'endfield': [
                {
                    'id': a.id,
                    'name': a.name,
                    'game_path': a.game_path,
                    'config_path': a.config_path,
                    'tasks': a.tasks,
                    'enabled': a.enabled,
                    'priority': a.priority
                } for a in self.accounts['endfield']
            ]
        }
        with open(self.accounts_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_settings(self):
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)