#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建二次元风格图标 - 不依赖PIL
使用纯Python生成PPM/ICO格式
"""
import struct
import os


def create_ppm_image():
    """创建简单的PPM格式图片"""
    width, height = 64, 64
    
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            # 渐变背景
            r = int(30 + (y / height) * 50)
            g = int(60 + (y / height) * 80)
            b = int(180 - (y / height) * 60)
            
            # 圆形区域 - 白色背景
            cx, cy = width // 2, height // 2
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if dist < 28:
                r, g, b = 255, 255, 255
            
            # 游戏手柄形状
            if 18 <= y <= 46 and 16 <= x <= 48:
                if 22 <= y <= 42:
                    r, g, b = 70, 130, 180  # 手柄主体
                if (x - 24) ** 2 + (y - 32) ** 2 < 64 or (x - 40) ** 2 + (y - 32) ** 2 < 64:
                    r, g, b = 70, 130, 180  # 摇杆
            
            # 星星装饰
            if abs(x - 12) + abs(y - 12) < 5 or abs(x - 52) + abs(y - 12) < 5:
                r, g, b = 255, 200, 100
            
            row.append((r, g, b))
        pixels.append(row)
    
    return pixels, width, height


def write_ppm(filename, pixels, width, height):
    """写入PPM文件"""
    with open(filename, 'wb') as f:
        f.write(b'P6\n')
        f.write(f'{width} {height}\n'.encode())
        f.write(b'255\n')
        for row in pixels:
            for r, g, b in row:
                f.write(bytes([r, g, b]))


def create_ico(filename, pixels, width, height):
    """创建ICO文件"""
    # ICO文件结构
    with open(filename, 'wb') as f:
        # ICO头
        f.write(struct.pack('<HHH', 0, 1, 1))  # Reserved, Type(1=ICO), Count
        
        # 图像目录
        f.write(struct.pack('<BBBBHHII', 
            width, height, 0, 0, 1, 32,  # 宽高, 颜色数, 保留, 颜色平面, 每像素位数
            len(pixels) * width * 3 + 40, 40))  # 大小, 偏移
        
        # BITMAPINFOHEADER
        f.write(struct.pack('<IIIHHIIIIII',
            40, width, height * 2, 1, 24, 0,  # 大小, 宽高*2, 平面, 位数
            0, 0, 0, 0))  # 压缩, 图像大小, x/y分辨率, 颜色数
        
        # 像素数据 (BGR格式, 从下到上)
        for y in range(height - 1, -1, -1):
            for x in range(width):
                r, g, b = pixels[y][x]
                f.write(bytes([b, g, r]))


def main():
    print("正在生成二次元风格图标...")
    
    # 创建图片数据
    pixels, width, height = create_ppm_image()
    
    # 保存PPM
    ppm_path = os.path.join(os.path.dirname(__file__), 'icon.ppm')
    write_ppm(ppm_path, pixels, width, height)
    print(f"PPM已保存: {ppm_path}")
    
    # 保存ICO
    ico_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    create_ico(ico_path, pixels, width, height)
    print(f"ICO图标已保存: {ico_path}")
    
    # 保存为ASCII PNM便于查看
    pnm_path = os.path.join(os.path.dirname(__file__), 'icon.txt')
    with open(pnm_path, 'w') as f:
        for row in pixels:
            for r, g, b in row:
                brightness = (r + g + b) // 3
                if brightness < 64:
                    f.write('█')
                elif brightness < 128:
                    f.write('▓')
                elif brightness < 192:
                    f.write('░')
                else:
                    f.write(' ')
            f.write('\n')
    print(f"ASCII预览已保存: {pnm_path}")
    
    print("图标生成完成!")
    return ico_path


if __name__ == '__main__':
    main()