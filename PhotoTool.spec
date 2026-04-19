# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置文件
# 图片批量转换工具

import os
import sys
from pathlib import Path

block_cipher = None

# 项目根目录
project_root = Path(SPECPATH)

a = Analysis(
    ['main.py'],                              # 入口文件
    pathex=[str(project_root)],               # 搜索路径
    binaries=[],
    datas=[
        # 资源文件：打包时将 assets/ 目录复制到输出根目录的 assets/ 下
        (os.path.join('assets', 'img'), os.path.join('assets', 'img')),
    ],
    hiddenimports=[
        # phototool 主包及所有子模块
        'phototool',
        'phototool.utils',
        'phototool.utils.paths',
        'phototool.core',
        'phototool.core.image_converter',
        'phototool.ui',
        'phototool.ui.styles',
        'phototool.widgets',
        'phototool.widgets.svg_toggle_btn',
        'phototool.widgets.collapsible_group',
        'phototool.widgets.crop_rubber_band',
        'phototool.widgets.drop_area',
        'phototool.views',
        'phototool.views.main_window',
        'phototool.threads',
        'phototool.threads.conversion_thread',
        'phototool.threads.image_worker',
        'phototool.threads.image_compress_worker',
        # 第三方库
        'PyQt5',
        'PyQt5.QtSvg',
        'PIL',
        'PIL._imaging',
        'PIL.Image',
        'PIL.PngImagePlugin',
        'PIL.JpegImagePlugin',
        'PIL.WebPImagePlugin',
        'PIL.BmpImagePlugin',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的大型模块，减小打包体积
        'tkinter',
        'test',
        'unittest',
        'distutils',
        'sysconfig',
        'setuptools',
        'pip',
        'email',
        'html',
        'xmlrpc',
        'pydoc',
        'doctest',
        'argparse',
        'difflib',
        'inspect',
        'asyncio',
        'concurrent',
        'multiprocessing',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PhotoTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'python3.dll',
        'python310.dll',
    ],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
