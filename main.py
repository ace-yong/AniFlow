#!/usr/bin/env python3
import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config_manager import ConfigManager
from src.executor import Executor
from src.logger import FileLogger, ReportGenerator
from src.scheduler import TaskScheduler
from src.process_manager import ProcessManager


def execute_daily_tasks(config_manager: ConfigManager, logger: FileLogger):
    executor = Executor(config_manager, logger)
    executor.build_task_queue('daily')
    stats = executor.execute_all_tasks()
    
    report_path = ReportGenerator.generate_report(stats, executor.task_queue.tasks)
    summary = ReportGenerator.generate_summary_report(report_path)
    
    logger.info('任务执行报告:')
    logger.info(summary)
    
    print('\n' + '=' * 60)
    print('任务执行完成！')
    print(f'报告已保存至: {report_path}')
    print('=' * 60)


def execute_weekly_tasks(config_manager: ConfigManager, logger: FileLogger):
    executor = Executor(config_manager, logger)
    executor.build_task_queue('weekly')
    stats = executor.execute_all_tasks()
    
    report_path = ReportGenerator.generate_report(stats, executor.task_queue.tasks)
    summary = ReportGenerator.generate_summary_report(report_path)
    
    logger.info('周常任务执行报告:')
    logger.info(summary)
    
    print('\n' + '=' * 60)
    print('周常任务执行完成！')
    print(f'报告已保存至: {report_path}')
    print('=' * 60)


def run_scheduler(config_manager: ConfigManager, logger: FileLogger):
    schedule_settings = config_manager.get_schedule_settings()
    daily_time = schedule_settings.get('daily_time', '08:30')
    weekly_time = schedule_settings.get('weekly_time', '00:00')
    weekly_day = schedule_settings.get('weekly_day', 0)
    
    task_scheduler = TaskScheduler(logger)
    
    task_scheduler.add_daily_task('daily_tasks', execute_daily_tasks, 
                                  time_str=daily_time,
                                  args=(config_manager, logger))
    
    task_scheduler.add_weekly_task('weekly_tasks', execute_weekly_tasks,
                                   time_str=weekly_time,
                                   day_of_week=weekly_day,
                                   args=(config_manager, logger))
    
    print('定时任务调度器已启动')
    print(f'每日任务: 每天 {daily_time} 执行')
    days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    print(f'周常任务: 每周{days[weekly_day]} {weekly_time} 执行')
    print('按 Ctrl+C 停止调度器')
    
    task_scheduler.start()
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        task_scheduler.stop()
        print('\n调度器已停止')


def list_accounts(config_manager: ConfigManager):
    print('\n=== 账号列表 ===')
    
    zzz_accounts = config_manager.get_enabled_accounts('zenless_zone_zero')
    print('\n[绝区零]')
    for account in zzz_accounts:
        status = '✓ 启用' if account.enabled else '✗ 禁用'
        print(f'  {status} {account.name} (ID: {account.id}, 优先级: {account.priority})')
        print(f'    任务: {", ".join(account.tasks)}')
    
    endfield_accounts = config_manager.get_enabled_accounts('endfield')
    print('\n[终末地]')
    for account in endfield_accounts:
        status = '✓ 启用' if account.enabled else '✗ 禁用'
        print(f'  {status} {account.name} (ID: {account.id}, 优先级: {account.priority})')
        print(f'    任务: {", ".join(account.tasks)}')


def show_config(config_manager: ConfigManager):
    print('\n=== 当前配置 ===')
    
    print('\n[工具路径]')
    onedragon_settings = config_manager.get_tool_settings('onedragon')
    maaend_settings = config_manager.get_tool_settings('maaend')
    print(f'  OneDragon: {onedragon_settings.get("path", "未设置")}')
    print(f'  MaaEnd: {maaend_settings.get("path", "未设置")}')
    
    print('\n[执行设置]')
    exec_settings = config_manager.get_execution_settings()
    print(f'  账号切换延迟: {exec_settings.get("account_switch_delay", 30)}秒')
    print(f'  任务超时时间: {exec_settings.get("task_timeout", 1800)}秒')
    print(f'  重试次数: {exec_settings.get("retry_count", 2)}次')
    print(f'  重试间隔: {exec_settings.get("retry_delay", 60)}秒')
    
    print('\n[定时设置]')
    schedule_settings = config_manager.get_schedule_settings()
    print(f'  每日执行时间: {schedule_settings.get("daily_time", "08:30")}')
    print(f'  周常执行时间: {schedule_settings.get("weekly_time", "00:00")}')
    days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    print(f'  周常执行日期: {days[schedule_settings.get("weekly_day", 0)]}')


GAME_TYPES = {'zzz': 'zenless_zone_zero', 'endfield': 'endfield', 'all': 'all'}


def cmd_start(game_arg: str, config_manager: ConfigManager, logger: FileLogger):
    pm = ProcessManager(config_manager)
    game_type = GAME_TYPES.get(game_arg)
    if game_type == 'all':
        pm.start_all()
        logger.info('已启动全部游戏')
        print('已启动全部游戏')
    elif game_type:
        ok = pm.start_game(game_type)
        label = {'zenless_zone_zero': '绝区零', 'endfield': '终末地'}.get(game_type, game_type)
        if ok:
            logger.info(f'已启动 {label}')
            print(f'已启动 {label}')
        else:
            logger.error(f'启动 {label} 失败，请检查工具路径配置')
            print(f'启动 {label} 失败，请检查工具路径配置')
    else:
        print(f'未知游戏: {game_arg}，可用: zzz, endfield, all')


def cmd_stop(game_arg: str, config_manager: ConfigManager, logger: FileLogger):
    pm = ProcessManager(config_manager)
    game_type = GAME_TYPES.get(game_arg)
    if game_type == 'all':
        pm.stop_all()
        logger.info('已停止全部游戏')
        print('已停止全部游戏')
    elif game_type:
        pm.stop_game(game_type)
        label = {'zenless_zone_zero': '绝区零', 'endfield': '终末地'}.get(game_type, game_type)
        logger.info(f'已停止 {label}')
        print(f'已停止 {label}')
    else:
        print(f'未知游戏: {game_arg}，可用: zzz, endfield, all')


def cmd_status(config_manager: ConfigManager, logger: FileLogger):
    pm = ProcessManager(config_manager)
    print('\n=== 游戏状态 ===')
    for gt, label in [('zenless_zone_zero', '绝区零'), ('endfield', '终末地')]:
        status = '● 运行中' if pm.is_running(gt) else '○ 已停止'
        print(f'  {label}: {status}')


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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(script_dir, os.path.basename(sys.argv[0]))
    args = ' '.join(f'"{a}"' if ' ' in a else a for a in sys.argv[1:])
    cmd = f'"{script}" {args}'.strip()
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, cmd, script_dir, 1
    )
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='游戏自动化调度工具')
    parser.add_argument('action', choices=['daily', 'weekly', 'schedule', 'list', 'config', 'start', 'stop', 'status'],
                        help='执行动作: daily(日常), weekly(周常), schedule(定时), list(账号), config(配置), start(启动), stop(停止), status(状态)')
    parser.add_argument('target', nargs='?', default=None,
                        help='start/stop 目标: zzz, endfield, all')
    parser.add_argument('--config-dir', default='config', help='配置目录')
    
    args = parser.parse_args()
    
    if args.action in ('start', 'stop', 'status', 'schedule'):
        _ensure_admin()
    
    logger = FileLogger()
    config_manager = ConfigManager(args.config_dir)
    
    logger.info(f'=== 游戏自动化调度工具启动 ===')
    logger.info(f'启动时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    logger.info(f'执行动作: {args.action}')
    
    if args.action == 'daily':
        execute_daily_tasks(config_manager, logger)
    elif args.action == 'weekly':
        execute_weekly_tasks(config_manager, logger)
    elif args.action == 'schedule':
        run_scheduler(config_manager, logger)
    elif args.action == 'list':
        list_accounts(config_manager)
    elif args.action == 'config':
        show_config(config_manager)
    elif args.action == 'start':
        if not args.target:
            print('请指定目标: python main.py start zzz|endfield|all')
            return
        cmd_start(args.target, config_manager, logger)
    elif args.action == 'stop':
        if not args.target:
            print('请指定目标: python main.py stop zzz|endfield|all')
            return
        cmd_stop(args.target, config_manager, logger)
    elif args.action == 'status':
        cmd_status(config_manager, logger)
    
    logger.info('=== 工具执行完毕 ===')


if __name__ == '__main__':
    main()