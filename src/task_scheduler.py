from typing import List, Dict, Any, Callable
from datetime import datetime, timedelta
import time


class Task:
    def __init__(self, task_id: str, name: str, game_type: str, 
                 account_id: str, account_name: str, 
                 task_type: str, priority: int = 1):
        self.task_id = task_id
        self.name = name
        self.game_type = game_type
        self.account_id = account_id
        self.account_name = account_name
        self.task_type = task_type
        self.priority = priority
        self.status = 'pending'
        self.start_time = None
        self.end_time = None
        self.error = None
        self.duration = 0

    def start(self):
        self.status = 'running'
        self.start_time = datetime.now()

    def complete(self):
        self.status = 'completed'
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0

    def fail(self, error: str):
        self.status = 'failed'
        self.error = error
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0


class TaskQueue:
    def __init__(self):
        self.tasks: List[Task] = []

    def add_task(self, task: Task):
        self.tasks.append(task)

    def add_tasks(self, tasks: List[Task]):
        self.tasks.extend(tasks)

    def get_pending_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == 'pending']

    def get_running_task(self) -> Task | None:
        for t in self.tasks:
            if t.status == 'running':
                return t
        return None

    def get_completed_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == 'completed']

    def get_failed_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == 'failed']

    def sort_by_priority(self):
        self.tasks.sort(key=lambda x: (x.priority, x.task_type))

    def clear(self):
        self.tasks.clear()

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.tasks)
        completed = len(self.get_completed_tasks())
        failed = len(self.get_failed_tasks())
        running = len([t for t in self.tasks if t.status == 'running'])
        pending = total - completed - failed - running
        
        total_duration = sum(t.duration for t in self.tasks)
        
        return {
            'total': total,
            'completed': completed,
            'failed': failed,
            'running': running,
            'pending': pending,
            'total_duration': round(total_duration, 2),
            'success_rate': round(completed / total * 100, 2) if total > 0 else 0
        }


class TaskBuilder:
    @staticmethod
    def build_daily_tasks(accounts: List[Any]) -> List[Task]:
        tasks = []
        task_counter = 0
        
        for account in accounts:
            for task_type in account.tasks:
                task_counter += 1
                task = Task(
                    task_id=f'daily_{task_counter}',
                    name=f'{account.name} - {TaskBuilder._get_task_name(task_type)}',
                    game_type='zenless_zone_zero' if 'zzz' in account.id else 'endfield',
                    account_id=account.id,
                    account_name=account.name,
                    task_type=task_type,
                    priority=account.priority
                )
                tasks.append(task)
        
        return tasks

    @staticmethod
    def build_weekly_tasks(accounts: List[Any]) -> List[Task]:
        tasks = []
        task_counter = 0
        
        for account in accounts:
            task_counter += 1
            task = Task(
                task_id=f'weekly_{task_counter}',
                name=f'{account.name} - 周常任务',
                game_type='zenless_zone_zero' if 'zzz' in account.id else 'endfield',
                account_id=account.id,
                account_name=account.name,
                task_type='weekly',
                priority=account.priority
            )
            tasks.append(task)
        
        return tasks

    @staticmethod
    def _get_task_name(task_type: str) -> str:
        task_names = {
            'daily': '日常任务',
            'coffee': '咖啡馆',
            'world_patrol': '世界巡逻',
            'hollow': '空洞探索',
            'infrast': '基建管理',
            'rewards': '领取奖励',
            'weekly': '周常任务'
        }
        return task_names.get(task_type, task_type)