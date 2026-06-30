#!/usr/bin/env python3
"""创建一个精美的白丝腿图标"""
from PIL import Image, ImageDraw
import math

def create_white_leg_icon():
    size = 256
    
    # 创建渐变背景
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 绘制渐变圆形背景（紫色系，符合二次元风格）
    center = size // 2
    for r in range(center, 0, -1):
        ratio = r / center
        # 紫色渐变
        purple = int(138 * ratio)
        pink = int(43 * ratio)
        blue = int(255 * ratio)
        alpha = int(255 * ratio * 0.8)
        draw.ellipse([center - r, center - r, center + r, center + r], 
                    fill=(purple, pink, blue, alpha))
    
    # 绘制白丝腿的简化轮廓
    # 腿部位置和形状
    leg_left_x = center - 35
    leg_right_x = center + 35
    leg_top = center - 60
    leg_bottom = center + 80
    
    # 绘制左腿（白丝效果）
    leg_width = 25
    for i in range(leg_width):
        offset = i - leg_width // 2
        # 白丝渐变
        white_level = 255
        gray_level = int(255 - (abs(offset) / (leg_width // 2)) * 40)
        alpha = 255
        
        # 绘制腿部轮廓
        x1 = leg_left_x + offset - 5
        x2 = leg_left_x + offset + 5
        y1 = leg_top + abs(offset) * 0.3
        y2 = leg_bottom - abs(offset) * 0.1
        
        draw.line([(x1, y1), (x2, y2)], fill=(gray_level, gray_level, white_level, alpha), width=2)
    
    # 绘制右腿
    for i in range(leg_width):
        offset = i - leg_width // 2
        gray_level = int(255 - (abs(offset) / (leg_width // 2)) * 40)
        alpha = 255
        
        x1 = leg_right_x + offset - 5
        x2 = leg_right_x + offset + 5
        y1 = leg_top + abs(offset) * 0.3
        y2 = leg_bottom - abs(offset) * 0.1
        
        draw.line([(x1, y1), (x2, y2)], fill=(gray_level, gray_level, white_level, alpha), width=2)
    
    # 绘制大腿轮廓（更圆润）
    # 左大腿
    for angle in range(0, 180):
        rad = math.radians(angle)
        x = leg_left_x - 15 + int(20 * math.sin(rad))
        y = leg_top + 10 + int(35 * (1 - math.cos(rad)) / 2)
        draw.point((x, y), fill=(250, 250, 255, 255))
    
    # 右大腿
    for angle in range(0, 180):
        rad = math.radians(angle)
        x = leg_right_x - 15 + int(20 * math.sin(rad))
        y = leg_top + 10 + int(35 * (1 - math.cos(rad)) / 2)
        draw.point((x, y), fill=(250, 250, 255, 255))
    
    # 绘制裙子下摆的装饰
    skirt_y = leg_top - 5
    for x in range(leg_left_x - 30, leg_right_x + 30):
        wave = int(5 * math.sin((x - center) * 0.1))
        draw.point((x, skirt_y + wave), fill=(255, 200, 220, 200))
    
    # 保存PNG
    img.save('whitestocking.png', 'PNG')
    
    # 创建ICO（多种尺寸）
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    icons = []
    for w, h in sizes:
        resized = img.resize((w, h), Image.Resampling.LANCZOS)
        icons.append(resized)
    
    icons[0].save('icon.ico', format='ICO', sizes=sizes)
    print("白丝腿图标已创建!")
    print("- PNG: whitestocking.png")
    print("- ICO: icon.ico")

if __name__ == '__main__':
    create_white_leg_icon()