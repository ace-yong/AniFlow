#!/usr/bin/env python3
"""从壁纸创建ICO图标"""
from PIL import Image, ImageDraw
import os

def create_icon_from_wallpaper():
    source_path = r'D:\壁纸\二次元\001 (19).jpg'
    ico_path = 'icon.ico'
    
    # 打开图片
    img = Image.open(source_path)
    w, h = img.size
    print(f"原图尺寸: {w}x{h}")
    
    # 裁剪为正方形（从中间或黄金分割点）
    # 对于1920x1080，裁剪中间区域
    if w > h:
        # 横向图片，裁剪中间的正方形
        new_size = h
        left = (w - new_size) // 2
        top = 0
        right = left + new_size
        bottom = new_size
        img = img.crop((left, top, right, bottom))
    else:
        # 纵向图片，裁剪中间的正方形
        new_size = w
        left = 0
        top = (h - new_size) // 2
        right = new_size
        bottom = top + new_size
        img = img.crop((left, top, right, bottom))
    
    print(f"裁剪后尺寸: {img.size}")
    
    # 调整为256x256
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    
    # 添加轻微边框效果（可选）
    # draw = ImageDraw.Draw(img)
    # draw.rectangle([0, 0, 255, 255], outline=(255, 255, 255, 200), width=3)
    
    # 保存为ICO（多种尺寸）
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    icons = []
    for size in sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        icons.append(resized)
    
    icons[0].save(ico_path, format='ICO', sizes=sizes)
    print(f"ICO图标已创建: {ico_path}")
    
    # 同时保存一个PNG预览
    img.save('whitestocking.png', 'PNG')
    print(f"PNG预览已保存: whitestocking.png")

if __name__ == '__main__':
    create_icon_from_wallpaper()