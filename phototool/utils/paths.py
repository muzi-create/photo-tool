"""
资源路径工具

兼容开发环境和 PyInstaller 打包环境：
- 开发时：基于项目根目录
- 打包后：基于 sys._MEIPASS 临时解压目录
"""

import sys
from pathlib import Path


def resource_path(relative_path: str) -> str:
    """
    获取资源文件的绝对路径

    Args:
        relative_path: 相对于项目根目录的路径，如 'assets/img/down.svg'

    Returns:
        资源文件的绝对路径字符串
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后，资源解压到 sys._MEIPASS 目录
        base_path = Path(sys._MEIPASS)
    else:
        # 开发环境，基于项目根目录（main.py 所在目录）
        base_path = Path(__file__).resolve().parents[2]
    return str(base_path / relative_path)


def asset_path(asset_relative_path: str) -> str:
    """
    获取 assets 目录下资源的绝对路径

    Args:
        asset_relative_path: 相对于 assets 目录的路径，如 'img/down.svg'

    Returns:
        资源文件的绝对路径字符串
    """
    return resource_path(str(Path('assets') / asset_relative_path))
