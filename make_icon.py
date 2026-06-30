#!/usr/bin/env python3
"""生成高质量ICO图标"""
from PIL import Image
import os

# 打开PNG图片
png_path = os.path.join(os.path.dirname(__file__), 'anime_icon.png')
img = Image.open(png_path)

# 确保是RGBA模式
if img.mode != 'RGBA':
    img = img.convert('RGBA')

# 调整到256x256
img = img.resize((256, 256), Image.Resampling.LANCZOS)

# 创建多种尺寸的图标
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
icons = []
for w, h in sizes:
    resized = img.resize((w, h), Image.Resampling.LANCZOS)
    icons.append(resized)

# 保存为ICO
ico_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
icons[0].save(ico_path, format='ICO', sizes=sizes)

print(f"ICO图标已生成: {ico_path}")
print(f"包含尺寸: {sizes}")