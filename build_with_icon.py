#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整打包脚本 - 生成二次元图标并打包exe到桌面
"""
import os
import sys
import struct
import shutil
import subprocess


def create_icon():
    """创建二次元风格ICO图标"""
    size = 64
    pixels = []
    
    for y in range(size):
        row = []
        for x in range(size):
            # 渐变背景
            r = int(30 + (y / size) * 50)
            g = int(60 + (y / size) * 80)
            b = int(180 - (y / size) * 60)
            
            cx, cy = size // 2, size // 2
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            
            # 圆形白色背景
            if dist < 28:
                r, g, b = 255, 255, 255
            
            # 手柄主体
            if 18 <= y <= 46 and 16 <= x <= 48:
                if 22 <= y <= 42:
                    r, g, b = 70, 130, 180
            
            # 摇杆
            if (x - 24) ** 2 + (y - 32) ** 2 < 36 or (x - 40) ** 2 + (y - 32) ** 2 < 36:
                r, g, b = 70, 130, 180
            
            # 星星装饰
            if abs(x - 12) + abs(y - 12) < 5 or abs(x - 52) + abs(y - 12) < 5:
                r, g, b = 255, 200, 100
            if abs(x - 12) + abs(y - 52) < 5 or abs(x - 52) + abs(y - 52) < 5:
                r, g, b = 255, 200, 100
            
            row.append((r, g, b))
        pixels.append(row)
    
    # 写入ICO文件
    ico_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    
    with open(ico_path, 'wb') as f:
        # ICO头
        f.write(struct.pack('<HHH', 0, 1, 1))
        
        # 图像目录
        f.write(struct.pack('<BBBBHHII',
            size, size, 0, 0, 1, 32,
            size * size * 3 + 40, 40))
        
        # BITMAPINFOHEADER
        f.write(struct.pack('<IIIHHIIIIII',
            40, size, size * 2, 1, 24, 0, 0, 0, 0, 0, 0))
        
        # 像素数据 (BGR)
        for y in range(size - 1, -1, -1):
            for x in range(size):
                r, g, b = pixels[y][x]
                f.write(bytes([b, g, r]))
    
    print(f"图标已生成: {ico_path}")
    return ico_path


def build_exe_with_icon(icon_path):
    """使用图标打包exe"""
    print("开始打包...")
    
    pyinstaller_cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=游戏自动化调度工具',
        '--windowed',
        '--onefile',
        '--clean',
        '--noconfirm',
        f'--icon={icon_path}',
        '--add-data=config;config',
        'gui.py'
    ]
    
    print("执行PyInstaller...")
    result = subprocess.run(
        pyinstaller_cmd,
        cwd=os.path.dirname(__file__),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("打包失败:")
        print(result.stderr)
        return False
    
    return True


def copy_to_desktop(exe_path):
    """复制exe到桌面"""
    desktop_paths = [
        os.path.join(os.path.expanduser('~'), 'Desktop'),
        os.path.join(os.path.expanduser('~'), 'OneDrive', 'Desktop'),
    ]
    
    for desktop in desktop_paths:
        if os.path.exists(desktop):
            target = os.path.join(desktop, '游戏自动化调度工具.exe')
            shutil.copy2(exe_path, target)
            print(f"已复制到桌面: {target}")
            return True
    
    return False


def main():
    print("=" * 50)
    print("   游戏自动化调度工具 - 打包程序")
    print("=" * 50)
    print()
    
    # 1. 生成图标
    print("[1/3] 生成二次元风格图标...")
    icon_path = create_icon()
    
    # 2. 打包exe
    print("\n[2/3] 打包exe程序...")
    project_dir = os.path.dirname(__file__)
    dist_dir = os.path.join(project_dir, 'dist')
    
    success = build_exe_with_icon(icon_path)
    
    if not success:
        print("打包失败!")
        input("按任意键退出...")
        return
    
    # 3. 复制到桌面
    print("\n[3/3] 复制到桌面...")
    exe_path = os.path.join(dist_dir, '游戏自动化调度工具.exe')
    
    if os.path.exists(exe_path):
        if copy_to_desktop(exe_path):
            print("\n" + "=" * 50)
            print("   打包完成！")
            print("=" * 50)
            print(f"\nexe文件位置: {exe_path}")
            print("桌面快捷方式已创建!")
        else:
            print("无法复制到桌面，但exe已生成在dist目录")
    else:
        print(f"找不到exe文件: {exe_path}")
    
    print("\n按任意键退出...")
    input()


if __name__ == '__main__':
    main()