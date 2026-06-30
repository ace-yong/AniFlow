import logging
import os
import json
from datetime import datetime
from typing import Dict, Any


class FileLogger:
    def __init__(self, log_dir: str = 'logs'):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        log_filename = datetime.now().strftime('%Y%m%d_%H%M%S.log')
        self.log_file = os.path.join(log_dir, log_filename)
        
        self.logger = logging.getLogger('GameAutoScheduler')
        self.logger.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log(self, message: str, level: str = 'INFO'):
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'SUCCESS': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        log_level = level_map.get(level, logging.INFO)
        self.logger.log(log_level, message)

    def debug(self, message: str):
        self.log(message, 'DEBUG')

    def info(self, message: str):
        self.log(message, 'INFO')

    def success(self, message: str):
        self.log(message, 'SUCCESS')

    def warning(self, message: str):
        self.log(message, 'WARNING')

    def error(self, message: str):
        self.log(message, 'ERROR')

    def critical(self, message: str):
        self.log(message, 'CRITICAL')


class ReportGenerator:
    @staticmethod
    def generate_report(stats: Dict[str, Any], tasks: list, 
                       report_dir: str = 'logs') -> str:
        os.makedirs(report_dir, exist_ok=True)
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'stats': stats,
            'tasks': []
        }
        
        for task in tasks:
            task_info = {
                'task_id': task.task_id,
                'name': task.name,
                'game_type': task.game_type,
                'account_id': task.account_id,
                'account_name': task.account_name,
                'task_type': task.task_type,
                'priority': task.priority,
                'status': task.status,
                'start_time': task.start_time.isoformat() if task.start_time else None,
                'end_time': task.end_time.isoformat() if task.end_time else None,
                'duration': task.duration,
                'error': task.error
            }
            report['tasks'].append(task_info)
        
        report_filename = datetime.now().strftime('%Y%m%d_%H%M%S_report.json')
        report_path = os.path.join(report_dir, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        return report_path

    @staticmethod
    def generate_summary_report(report_path: str) -> str:
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        summary = []
        summary.append('=' * 60)
        summary.append('          游戏自动化任务执行报告')
        summary.append('=' * 60)
        summary.append(f'生成时间: {report["generated_at"]}')
        summary.append('-' * 60)
        summary.append('执行统计:')
        summary.append(f'  总任务数: {report["stats"]["total"]}')
        summary.append(f'  完成: {report["stats"]["completed"]}')
        summary.append(f'  失败: {report["stats"]["failed"]}')
        summary.append(f'  运行中: {report["stats"]["running"]}')
        summary.append(f'  待执行: {report["stats"]["pending"]}')
        summary.append(f'  成功率: {report["stats"]["success_rate"]}%')
        summary.append(f'  总耗时: {report["stats"]["total_duration"]} 秒')
        summary.append('-' * 60)
        summary.append('任务详情:')
        
        for task in report['tasks']:
            status_icon = '✓' if task['status'] == 'completed' else '✗' if task['status'] == 'failed' else '◐'
            duration = f'{task["duration"]:.2f}s' if task['duration'] else '-'
            error = f' (错误: {task["error"]})' if task['error'] else ''
            summary.append(f'  {status_icon} {task["name"]} - {task["status"]} - 耗时: {duration}{error}')
        
        summary.append('=' * 60)
        
        return '\n'.join(summary)