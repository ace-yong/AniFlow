# -*- mode: python ; coding: utf-8 -*-

import os
import PyQt5

p = os.path.dirname(PyQt5.__file__)
plugin_files = []
for root, dirs, files in os.walk(os.path.join(p, 'Qt5', 'plugins')):
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, p)
        plugin_files.append((full, rel))

a = Analysis(
    ['gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[ (src, dst) for src, dst, _ in Tree('src', prefix='src') ] + [('icon.ico', '.'), ('wallpaper_source.jpg', '.')] + plugin_files,
    hiddenimports=['PyQt5.sip'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AniFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['*.dll'],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
