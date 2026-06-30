import subprocess
import os
import time
from typing import Dict, Any, Optional
import signal


class ToolInvoker:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.onedragon_settings = self.config_manager.get_tool_settings('onedragon')
        self.maaend_settings = self.config_manager.get_tool_settings('maaend')
        self.execution_settings = self.config_manager.get_execution_settings()
        self.timeout = self.execution_settings.get('task_timeout', 1800)
        self.retry_count = self.execution_settings.get('retry_count', 2)
        self.retry_delay = self.execution_settings.get('retry_delay', 60)

    def invoke_onedragon(self, account: Any) -> Dict[str, Any]:
        tool_path = self.onedragon_settings.get('path', '')
        python_path = self.onedragon_settings.get('python_path', 'python')
        headless = self.onedragon_settings.get('headless', False)
        
        if not os.path.exists(tool_path):
            return {'success': False, 'error': f'OneDragon路径不存在: {tool_path}'}
        
        project_dir = os.path.dirname(tool_path)
        
        tasks_str = ','.join(account.tasks)
        instance_name = account.id.replace('zzz_', '')
        
        args = [python_path, tool_path, '--onedragon', '--instance', instance_name, '--app', tasks_str]
        
        if headless:
            args.append('--headless')
        
        if account.game_path:
            env = os.environ.copy()
            env['GAME_PATH'] = account.game_path
        else:
            env = None
        
        return self._run_command(args, project_dir, env=env, timeout=self.timeout)

    def invoke_maaend(self, account: Any) -> Dict[str, Any]:
        """调用MaaEnd（终末地）- 使用视觉识别，无需配置账号"""
        tool_path = self.maaend_settings.get('path', '')
        
        if not os.path.exists(tool_path):
            return {'success': False, 'error': f'MaaEnd路径不存在: {tool_path}'}
        
        project_dir = os.path.dirname(tool_path)
        
        tasks_str = ','.join(account.tasks)
        
        # MaaEnd使用视觉识别，只需指定任务和窗口模式，不强制要求实例/账号
        args = [tool_path, '--tasks', tasks_str]
        
        if self.maaend_settings.get('headless', False):
            args.append('--headless')
        
        return self._run_command(args, project_dir, timeout=self.timeout)

    def _run_command(self, args: list, cwd: str, env: Optional[Dict] = None, 
                    timeout: int = 1800) -> Dict[str, Any]:
        result = {
            'success': False,
            'error': None,
            'output': '',
            'duration': 0,
            'return_code': None
        }
        
        for attempt in range(self.retry_count + 1):
            start_time = time.time()
            
            try:
                process = subprocess.Popen(
                    args,
                    cwd=cwd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                stdout, stderr = process.communicate(timeout=timeout)
                
                duration = time.time() - start_time
                
                if process.returncode == 0:
                    result['success'] = True
                    result['output'] = stdout
                    result['duration'] = round(duration, 2)
                    result['return_code'] = process.returncode
                    return result
                
                result['error'] = f'命令执行失败 (返回码: {process.returncode}): {stderr}'
                result['output'] = stdout
                result['duration'] = round(duration, 2)
                result['return_code'] = process.returncode
                
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                duration = time.time() - start_time
                result['error'] = f'命令执行超时 ({timeout}秒)'
                result['duration'] = round(duration, 2)
            except Exception as e:
                duration = time.time() - start_time
                result['error'] = f'命令执行异常: {str(e)}'
                result['duration'] = round(duration, 2)
            
            if attempt < self.retry_count:
                time.sleep(self.retry_delay)
        
        return result

    def kill_all_tools(self):
        try:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/f', '/im', 'python.exe'], capture_output=True)
                subprocess.run(['taskkill', '/f', '/im', 'MaaEnd.exe'], capture_output=True)
            else:
                subprocess.run(['pkill', '-f', 'one_dragon.py'], capture_output=True)
                subprocess.run(['pkill', '-f', 'MaaEnd'], capture_output=True)
        except Exception as e:
            pass