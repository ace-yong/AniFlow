#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成二次元风格图标
"""
import os
import sys

# 尝试导入PIL
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("需要安装Pillow: pip install Pillow")
    sys.exit(1)


def create_icon():
    """创建二次元风格图标"""
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 背景圆角矩形 - 渐变蓝紫色
    padding = 10
    corners = [padding, padding, size - padding, size - padding]
    
    # 绘制渐变背景
    for i in range(size):
        y = i
        ratio = i / size
        r = int(30 + ratio * 50)
        g = int(60 + ratio * 80)
        b = int(180 - ratio * 60)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    
    # 绘制圆形背景
    center = size // 2
    radius = size // 2 - 20
    draw.ellipse([center - radius, center - radius, center + radius, center + radius],
                 fill=(255, 255, 255, 230))
    
    # 绘制游戏手柄轮廓（代表自动化）
    handle_color = (70, 130, 180, 255)  # 钢蓝色
    handle_width = 15
    
    # 手柄主体
    draw.rounded_rectangle([60, 90, 196, 166], radius=40, outline=handle_color, width=handle_width)
    
    # 手柄摇杆区域
    draw.ellipse([80, 100, 120, 140], fill=handle_color)
    draw.ellipse([136, 100, 176, 140], fill=handle_color)
    
    # 绘制装饰星星
    star_positions = [(40, 40), (200, 50), (50, 200), (190, 190)]
    for x, y in star_positions:
        draw_star(draw, x, y, 12, handle_color)
    
    # 绘制文字 "GAME"
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()
    
    # 用圆形背景包裹文字
    draw.ellipse([95, 155, 161, 185], fill=(255, 100, 100, 255))
    draw.text((105, 158), "A", fill=(255, 255, 255, 255), font=font)
    
    return img


def draw_star(draw, x, y, size, color):
    """绘制星星"""
    points = []
    for i in range(10):
        angle = i * 36 - 90
        r = size if i % 2 == 0 else size // 2
        px = x + r * (angle == 0 and 1 or (1 if angle == 180 else 0.5 if angle in [36, 144] else 0.866 if angle in [72, 108] else 0))
        py = y + r * (angle == 270 and 1 or (1 if angle == 90 else 0.5 if angle in [18, 162] else 0.866 if angle in [54, 126] else 0))
        points.append((px, py))
    
    # 简化的星星
    draw.polygon([(x, y - size), (x + size * 0.3, y - size * 0.3), 
                  (x + size, y - size * 0.3), (x + size * 0.5, y + size * 0.2),
                  (x + size * 0.7, y + size), (x, y + size * 0.4),
                  (x - size * 0.7, y + size), (x - size * 0.5, y + size * 0.2),
                  (x - size, y - size * 0.3), (x - size * 0.3, y - size * 0.3)], 
                 fill=color)


def main():
    # 创建图标
    icon = create_icon()
    
    # 保存为PNG
    icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
    icon.save(icon_path, 'PNG')
    print(f"图标已保存: {icon_path}")
    
    # 转换为ICO格式
    ico_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    
    # 创建不同尺寸的图标
    sizes = [256, 128, 64, 48, 32, 16]
    icons = []
    for s in sizes:
        icons.append(icon.resize((s, s), Image.Resampling.LANCZOS))
    
    # 保存ICO
    icons[0].save(ico_path, format='ICO', sizes=[(s, s) for s in sizes])
    print(f"ICO图标已保存: {ico_path}")
    
    return ico_path


if __name__ == '__main__':
    main()