@echo off
chcp 65001 >nul
title 游戏自动化调度工具 - 打包程序

echo ================================================
echo    游戏自动化调度工具 - 一键打包程序
echo ================================================
echo.

:: 设置Python路径
set PYTHON_PATH=C:\Users\ace\AppData\Local\Programs\Python\Python312\python.exe

:: 检查Python
echo [检查] 验证Python环境...
if not exist "%PYTHON_PATH%" (
    echo [错误] 找不到Python，请先安装Python 3.12
    pause
    exit /b 1
)

:: 进入脚本目录
cd /d "%~dp0"

:: 安装依赖
echo.
echo [1/4] 安装依赖包...
"%PYTHON_PATH%" -m pip install PyQt5 pyinstaller -q
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo [OK] 依赖安装完成

:: 生成图标
echo.
echo [2/4] 生成二次元风格图标...
"%PYTHON_PATH%" create_icon_simple.py >nul 2>&1
if not exist "icon.ico" (
    echo [警告] 图标生成失败，将使用默认图标
    set ICON_FLAG=
) else (
    set ICON_FLAG=--icon=icon.ico
)
echo [OK] 图标生成完成

:: 打包
echo.
echo [3/4] 打包exe程序（这可能需要几分钟...）
if exist "icon.ico" (
    "%PYTHON_PATH%" -m PyInstaller --name=游戏自动化调度工具 --windowed --onefile --clean --noconfirm --icon=icon.ico --add-data=config;config gui.py
) else (
    "%PYTHON_PATH%" -m PyInstaller --name=游戏自动化调度工具 --windowed --onefile --clean --noconfirm --add-data=config;config gui.py
)

if %errorlevel% neq 0 (
    echo [错误] 打包失败
    pause
    exit /b 1
)
echo [OK] 打包完成

:: 复制到桌面
echo.
echo [4/4] 复制到桌面...
set DESKTOP=%USERPROFILE%\Desktop
if exist "%USERPROFILE%\OneDrive\Desktop" (
    set DESKTOP=%USERPROFILE%\OneDrive\Desktop
)

copy /Y "dist\游戏自动化调度工具.exe" "%DESKTOP%\" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 已复制到桌面: %DESKTOP%\游戏自动化调度工具.exe
) else (
    echo [警告] 无法复制到桌面，但exe已生成在 dist 目录
)

:: 完成
echo.
echo ================================================
echo                  打包完成！
echo ================================================
echo.
echo exe文件位置:
if exist "%DESKTOP%\游戏自动化调度工具.exe" (
    echo   桌面: %DESKTOP%\游戏自动化调度工具.exe
)
echo   项目: %~dp0dist\游戏自动化调度工具.exe
echo.
echo 按任意键退出...
pause >nul