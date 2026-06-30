@echo off
chcp 65001 >nul
echo ========================================
echo    游戏自动化调度工具 - 打包脚本
echo ========================================
echo.

echo [1] 安装依赖...
pip install PyQt5 pyinstaller -q
if %errorlevel% neq 0 (
    echo 安装依赖失败
    pause
    exit /b 1
)

echo [2] 开始打包...
python build_exe.py
if %errorlevel% neq 0 (
    echo 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo    打包完成！exe已复制到桌面
echo ========================================
echo.
pause