@echo off
chcp 65001 >nul
cd /d "%~dp0electron"
start /B python ..\gui_server.py > ..\electron\server_port.txt
timeout /t 3 /nobreak >nul
nodejs\node.exe node_modules\.bin\electron .
