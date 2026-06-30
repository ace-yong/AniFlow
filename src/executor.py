import time
from typing import List, Dict, Any
from datetime import datetime
from .config_manager import ConfigManager, AccountConfig
from .task_scheduler import TaskQueue, Task, TaskBuilder
from .tool_invoker import ToolInvoker


class Executor:
    def __init__(self, config_manager: ConfigManager, logger=None):
        self.config_manager = config_manager
        self.tool_invoker = ToolInvoker(config_manager)
        self.task_queue = TaskQueue()
        self.logger = logger
        self.execution_settings = self.config_manager.get_execution_settings()
        self.switch_delay = self.execution_settings.get('account_switch_delay', 30)
        self.is_running = False

    def _log(self, message: str, level: str = 'INFO'):
        if self.logger:
            self.logger.log(message, level)
        else:
            print(f'[{level}] {message}')

    def build_task_queue(self, task_type: str = 'daily'):
        self.task_queue.clear()
        
        zzz_accounts = self.config_manager.get_enabled_accounts('zenless_zone_zero')
        endfield_accounts = self.config_manager.get_enabled_accounts('endfield')
        
        if task_type == 'daily':
            zzz_tasks = TaskBuilder.build_daily_tasks(zzz_accounts)
            endfield_tasks = TaskBuilder.build_daily_tasks(endfield_accounts)
        elif task_type == 'weekly':
            zzz_tasks = TaskBuilder.build_weekly_tasks(zzz_accounts)
            endfield_tasks = TaskBuilder.build_weekly_tasks(endfield_accounts)
        else:
            zzz_tasks = TaskBuilder.build_daily_tasks(zzz_accounts)
            endfield_tasks = TaskBuilder.build_daily_tasks(endfield_accounts)
        
        all_tasks = zzz_tasks + endfield_tasks
        all_tasks.sort(key=lambda x: (x.priority, x.game_type))
        
        self.task_queue.add_tasks(all_tasks)
        
        self._log(f'已构建任务队列，共 {len(all_tasks)} 个任务')
        for task in all_tasks:
            self._log(f'  - {task.name} (优先级: {task.priority})')

    def execute_all_tasks(self) -> Dict[str, Any]:
        self.is_running = True
        start_time = datetime.now()
        
        self._log('===== 开始执行所有任务 =====', 'INFO')
        
        while self.is_running and self.task_queue.get_pending_tasks():
            pending_tasks = self.task_queue.get_pending_tasks()
            
            for task in pending_tasks:
                if not self.is_running:
                    break
                
                self._log(f'--- 开始执行: {task.name} ---', 'INFO')
                task.start()
                
                result = self._execute_task(task)
                
                if result['success']:
                    task.complete()
                    self._log(f'任务完成: {task.name} (耗时: {result["duration"]}秒)', 'SUCCESS')
                else:
                    task.fail(result['error'])
                    self._log(f'任务失败: {task.name} - {result["error"]}', 'ERROR')
                
                self._log(f'--- 任务结束: {task.name} ---', 'INFO')
                
                if self.is_running and self.task_queue.get_pending_tasks():
                    self._log(f'等待 {self.switch_delay} 秒后切换到下一个账号...', 'INFO')
                    time.sleep(self.switch_delay)
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        stats = self.task_queue.get_stats()
        stats['total_duration'] = round(total_duration, 2)
        
        self._log('===== 所有任务执行完毕 =====', 'INFO')
        self._log(f'执行统计: 总数={stats["total"]}, 完成={stats["completed"]}, '
                 f'失败={stats["failed"]}, 成功率={stats["success_rate"]}%, '
                 f'总耗时={stats["total_duration"]}秒', 'INFO')
        
        self.is_running = False
        return stats

    def _execute_task(self, task: Task) -> Dict[str, Any]:
        accounts = self.config_manager.get_enabled_accounts(task.game_type)
        account = next((a for a in accounts if a.id == task.account_id), None)
        
        if not account:
            return {'success': False, 'error': f'找不到账号配置: {task.account_id}', 'duration': 0}
        
        if task.game_type == 'zenless_zone_zero':
            return self.tool_invoker.invoke_onedragon(account)
        elif task.game_type == 'endfield':
            return self.tool_invoker.invoke_maaend(account)
        else:
            return {'success': False, 'error': f'未知游戏类型: {task.game_type}', 'duration': 0}

    def stop(self):
        self.is_running = False
        self.tool_invoker.kill_all_tools()
        self._log('执行已停止', 'WARNING')

    def execute_single_account(self, game_type: str, account_id: str) -> Dict[str, Any]:
        accounts = self.config_manager.get_enabled_accounts(game_type)
        account = next((a for a in accounts if a.id == account_id), None)
        
        if not account:
            return {'success': False, 'error': f'找不到账号配置: {account_id}'}
        
        self._log(f'开始执行单个账号: {account.name}', 'INFO')
        
        if game_type == 'zenless_zone_zero':
            result = self.tool_invoker.invoke_onedragon(account)
        elif game_type == 'endfield':
            result = self.tool_invoker.invoke_maaend(account)
        else:
            return {'success': False, 'error': f'未知游戏类型: {game_type}'}
        
        if result['success']:
            self._log(f'账号执行完成: {account.name}', 'SUCCESS')
        else:
            self._log(f'账号执行失败: {account.name} - {result["error"]}', 'ERROR')
        
        return result