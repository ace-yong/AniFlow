from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from typing import Callable, Dict, Any


class TaskScheduler:
    def __init__(self, logger=None):
        self.scheduler = BackgroundScheduler()
        self.logger = logger
        self.jobs = {}

    def _log(self, message: str, level: str = 'INFO'):
        if self.logger:
            self.logger.log(message, level)
        else:
            print(f'[{level}] {message}')

    def add_daily_task(self, task_name: str, func: Callable, 
                       time_str: str = '08:30', args: tuple = ()):
        hour, minute = map(int, time_str.split(':'))
        
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone='Asia/Shanghai'
        )
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=f'daily_{task_name}',
            name=f'每日任务: {task_name}',
            args=args,
            replace_existing=True
        )
        
        self.jobs[f'daily_{task_name}'] = {
            'type': 'daily',
            'name': task_name,
            'time': time_str,
            'func': func.__name__
        }
        
        self._log(f'已添加每日任务 "{task_name}"，每天 {time_str} 执行', 'INFO')

    def add_weekly_task(self, task_name: str, func: Callable,
                        time_str: str = '00:00', day_of_week: int = 0, 
                        args: tuple = ()):
        hour, minute = map(int, time_str.split(':'))
        
        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            timezone='Asia/Shanghai'
        )
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=f'weekly_{task_name}',
            name=f'周常任务: {task_name}',
            args=args,
            replace_existing=True
        )
        
        days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
        
        self.jobs[f'weekly_{task_name}'] = {
            'type': 'weekly',
            'name': task_name,
            'time': time_str,
            'day': days[day_of_week],
            'func': func.__name__
        }
        
        self._log(f'已添加周常任务 "{task_name}"，每周{days[day_of_week]} {time_str} 执行', 'INFO')

    def add_custom_task(self, task_name: str, func: Callable, 
                       cron_expr: str, args: tuple = ()):
        trigger = CronTrigger.from_crontab(cron_expr, timezone='Asia/Shanghai')
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=f'custom_{task_name}',
            name=f'自定义任务: {task_name}',
            args=args,
            replace_existing=True
        )
        
        self.jobs[f'custom_{task_name}'] = {
            'type': 'custom',
            'name': task_name,
            'cron': cron_expr,
            'func': func.__name__
        }
        
        self._log(f'已添加自定义任务 "{task_name}"，Cron: {cron_expr}', 'INFO')

    def start(self):
        self.scheduler.start()
        self._log('定时任务调度器已启动', 'INFO')
        self._log(f'当前时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 'INFO')
        
        if self.jobs:
            self._log('已注册的任务:', 'INFO')
            for job_id, job_info in self.jobs.items():
                self._log(f'  - {job_info["name"]} ({job_info["type"]})', 'INFO')

    def stop(self):
        self.scheduler.shutdown()
        self._log('定时任务调度器已停止', 'WARNING')

    def pause_job(self, job_id: str):
        self.scheduler.pause_job(job_id)
        self._log(f'任务 "{job_id}" 已暂停', 'WARNING')

    def resume_job(self, job_id: str):
        self.scheduler.resume_job(job_id)
        self._log(f'任务 "{job_id}" 已恢复', 'INFO')

    def remove_job(self, job_id: str):
        self.scheduler.remove_job(job_id)
        if job_id in self.jobs:
            del self.jobs[job_id]
        self._log(f'任务 "{job_id}" 已移除', 'WARNING')

    def get_jobs(self) -> Dict[str, Any]:
        jobs_info = {}
        for job in self.scheduler.get_jobs():
            jobs_info[job.id] = {
                'name': job.name,
                'next_run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None,
                'trigger': str(job.trigger),
                'status': 'paused' if job.paused else 'running'
            }
        return jobs_info

    def run_now(self, job_id: str):
        job = self.scheduler.get_job(job_id)
        if job:
            job.func(*job.args)
            self._log(f'任务 "{job_id}" 已立即执行', 'INFO')
        else:
            self._log(f'任务 "{job_id}" 不存在', 'ERROR')