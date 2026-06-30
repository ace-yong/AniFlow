#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将GUI工具打包成exe可执行程序
"""
import os
import sys
import shutil
import subprocess


def build_exe():
    """打包生成exe文件"""
    print("开始打包...")
    
    # 项目路径
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # PyInstaller命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=游戏自动化调度工具',
        '--windowed',  # 无控制台窗口
        '--onefile',   # 打包成单个exe
        '--clean',
        '--noconfirm',
        '--add-data=config;config',
        '--icon=NONE',
        'gui.py'
    ]
    
    # 执行打包
    print("执行PyInstaller命令...")
    result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("打包失败:")
        print(result.stderr)
        return False
    
    # 检查生成的exe
    exe_path = os.path.join(project_dir, 'dist', '游戏自动化调度工具.exe')
    
    if not os.path.exists(exe_path):
        print("exe文件未生成")
        return False
    
    # 复制到桌面
    desktop_path = get_desktop_path()
    if desktop_path:
        target_path = os.path.join(desktop_path, '游戏自动化调度工具.exe')
        shutil.copy2(exe_path, target_path)
        print(f"已复制到桌面: {target_path}")
    
    print("打包完成!")
    print(f"exe文件位置: {exe_path}")
    
    return True


def get_desktop_path():
    """获取桌面路径"""
    # Windows桌面路径
    desktop_paths = [
        os.path.join(os.path.expanduser('~'), 'Desktop'),
        os.path.join(os.path.expanduser('~'), 'OneDrive', 'Desktop'),
    ]
    
    for path in desktop_paths:
        if os.path.exists(path):
            return path
    
    return None


if __name__ == '__main__':
    success = build_exe()
    if not success:
        sys.exit(1)