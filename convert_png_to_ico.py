#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将PNG图片转换为ICO图标
"""
import struct
import os
import sys

def read_png(filename):
    """读取PNG文件并解析像素数据"""
    import zlib
    
    with open(filename, 'rb') as f:
        # 验证PNG签名
        signature = f.read(8)
        if signature != b'\x89PNG\r\n\x1a\n':
            raise ValueError("不是有效的PNG文件")
        
        width = 0
        height = 0
        bit_depth = 0
        color_type = 0
        compressed_data = b''
        
        while True:
            chunk_len = struct.unpack('>I', f.read(4))[0]
            chunk_type = f.read(4)
            chunk_data = f.read(chunk_len)
            chunk_crc = f.read(4)
            
            if chunk_type == b'IHDR':
                width = struct.unpack('>I', chunk_data[0:4])[0]
                height = struct.unpack('>I', chunk_data[4:8])[0]
                bit_depth = chunk_data[8]
                color_type = chunk_data[9]
            elif chunk_type == b'IDAT':
                compressed_data += chunk_data
            elif chunk_type == b'IEND':
                break
        
        # 解压缩
        raw_data = zlib.decompress(compressed_data)
        
        # 根据颜色类型解析像素
        pixels = []
        bytes_per_pixel = 4 if color_type == 6 else 3  # RGBA or RGB
        
        pos = 0
        for y in range(height):
            filter_byte = raw_data[pos]
            pos += 1
            row = []
            for x in range(width):
                if bytes_per_pixel == 4:
                    r, g, b, a = raw_data[pos:pos+4]
                else:
                    r, g, b = raw_data[pos:pos+3]
                    a = 255
                row.append((r, g, b, a))
                pos += bytes_per_pixel
            pixels.append(row)
        
        return pixels, width, height

def create_ico_from_png(png_file, ico_file):
    """从PNG创建ICO文件"""
    try:
        pixels, width, height = read_png(png_file)
    except Exception as e:
        print(f"读取PNG失败: {e}")
        return False
    
    # 调整大小到256x256或更小
    max_size = 256
    if width > max_size or height > max_size:
        # 简单缩放
        scale = max_size / max(width, height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        new_pixels = []
        for y in range(new_height):
            row = []
            for x in range(new_width):
                orig_x = int(x / scale)
                orig_y = int(y / scale)
                row.append(pixels[orig_y][orig_x])
            new_pixels.append(row)
        pixels = new_pixels
        width = new_width
        height = new_height
    
    print(f"图片尺寸: {width}x{height}")
    
    # 写入ICO文件
    with open(ico_file, 'wb') as f:
        # ICO头
        f.write(struct.pack('<HHH', 0, 1, 1))
        
        # 图像目录 (使用PNG格式存储)
        data_size = os.path.getsize(png_file)
        f.write(struct.pack('<BBBBHHII',
            width if width < 256 else 0,  # 256用0表示
            height if height < 256 else 0,
            0, 0, 1, 32,
            data_size + 40, 40))
        
        # BITMAPINFOHEADER
        f.write(struct.pack('<IIIHHIIIIII',
            40, width, height * 2, 1, 32, 0,
            width * height * 4, 0, 0, 0, 0))
        
        # 直接写入PNG数据作为图标
        with open(png_file, 'rb') as pf:
            f.write(pf.read())
    
    print(f"ICO图标已创建: {ico_file}")
    return True

def main():
    png_file = os.path.join(os.path.dirname(__file__), 'anime_icon.png')
    ico_file = os.path.join(os.path.dirname(__file__), 'icon.ico')
    
    print("正在将PNG转换为ICO...")
    if create_ico_from_png(png_file, ico_file):
        print("转换成功！")
    else:
        print("转换失败，尝试备用方法...")
        # 备用方法：直接使用PNG
        import shutil
        shutil.copy(png_file, ico_file.replace('.ico', '.png'))
        print("PNG图标已保存")

if __name__ == '__main__':
    main()