@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动游戏自动化调度工具...
"C:\Users\ace\AppData\Local\Programs\Python\Python312\python.exe" gui.py
pause