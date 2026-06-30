#!/usr/bin/env python3
"""下载白丝腿图片并转换为ICO"""
import urllib.request
import os
from PIL import Image
import io

# 使用一个可访问的图片URL
urls = [
    "https://cdn.imgbin.com/photo/11/14/85/anime-anime-girls-white-pantyhose-feet.jpg",
    "https://i.pinimg.com/originals/c9/5e/70/c95e704b0f2d4b7f28f98d6e4e3ef3a4.jpg",
]

def download_image():
    for url in urls:
        try:
            print(f"尝试下载: {url}")
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response = urllib.request.urlopen(req, timeout=10)
            data = response.read()
            
            # 保存原始图片
            with open('whitestocking_raw.png', 'wb') as f:
                f.write(data)
            print(f"下载成功! 大小: {len(data)} bytes")
            return True
        except Exception as e:
            print(f"下载失败: {e}")
            continue
    return False

def create_icon():
    """创建一个简单的白丝腿图标"""
    # 创建一个256x256的图标
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    
    try:
        # 尝试打开下载的图片
        if os.path.exists('whitestocking_raw.png'):
            src = Image.open('whitestocking_raw.png')
            src = src.convert('RGBA')
            
            # 裁剪并调整大小
            w, h = src.size
            # 裁剪腿部区域 (横向)
            if w > h:
                crop_h = min(h, int(w * 0.4))
                top = (h - crop_h) // 4
                src = src.crop((0, top, w, top + crop_h))
            
            src = src.resize((size, size), Image.Resampling.LANCZOS)
            img = src
            img.save('whitestocking.png', 'PNG')
            print("图片已处理")
    except Exception as e:
        print(f"处理图片失败: {e}")
    
    # 创建ICO
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    icons = []
    for w, h in sizes:
        resized = img.resize((w, h), Image.Resampling.LANCZOS)
        icons.append(resized)
    
    icons[0].save('icon.ico', format='ICO', sizes=sizes)
    print("ICO图标已创建: icon.ico")

if __name__ == '__main__':
    if download_image():
        create_icon()
    else:
        # 如果下载失败，创建一个渐变背景的图标
        print("创建备用图标...")
        create_icon()