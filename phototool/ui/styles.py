"""
PyQt5 样式表统一管理模块
提供全局样式配置和主题管理
"""

import sys
from pathlib import Path


def _resource_url(relative_path: str) -> str:
    """
    获取 QSS url() 可用的资源绝对路径

    Args:
        relative_path: 相对于项目根目录的路径，如 'assets/img/down.svg'

    Returns:
        可用于 QSS url() 的路径字符串
    """
    if hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parents[2]
    return str(base_path / relative_path).replace('\\', '/')


class StyleSheet:
    """样式表管理器"""

    # 主色调
    PRIMARY_COLOR = "#0078d7"
    PRIMARY_HOVER = "#106ebe"
    PRIMARY_PRESSED = "#005a9e"

    # 背景色
    BG_MAIN = "#f0f0f0"
    BG_CARD = "#ffffff"
    BG_HEADER = "#f8f8f8"

    # 边框色
    BORDER_LIGHT = "#dcdcdc"
    BORDER_MEDIUM = "#e0e0e0"
    BORDER_DARK = "#c0c0c0"

    # 文字色
    TEXT_PRIMARY = "#1a1a1a"
    TEXT_SECONDARY = "#333333"
    TEXT_MUTED = "#888888"
    TEXT_INFO = "#666666"

    # 功能色
    SUCCESS = "#2ecc71"
    WARNING = "#f39c12"
    DANGER = "#e74c3c"

    # 悬停边框色
    HOVER_COLOR = "#40A9FF"

    @classmethod
    def get_global_stylesheet(cls) -> str:
        """获取全局样式表 - 扁平化、圆角4px"""
        return f"""
/* === 全局基础 === */
QMainWindow, QWidget {{
    background-color: {cls.BG_MAIN};
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {cls.TEXT_PRIMARY};
}}

/* === 按钮 - 统一高度30px, 圆角4px === */
QPushButton {{
    background-color: {cls.BG_CARD};
    color: {cls.TEXT_PRIMARY};
    border: 1px solid #999999;
    border-radius: 4px;
    padding: 0 16px;
    min-height: 30px;
    max-height: 30px;
}}
QPushButton:hover {{
    border: 1px solid {cls.HOVER_COLOR};
    color: {cls.HOVER_COLOR};
}}
QPushButton:pressed {{
    background-color: {cls.BG_HEADER};
}}

/* 主按钮 */
#primaryBtn {{
    background-color: {cls.PRIMARY_COLOR};
    color: white;
    border: 1px solid {cls.PRIMARY_COLOR};
    border-radius: 4px;
    padding: 0 16px;
    min-height: 30px;
    font-weight: bold;
}}
#primaryBtn:hover {{
    background-color: {cls.PRIMARY_HOVER};
    border-color: {cls.PRIMARY_HOVER};
    color: white;
}}

/* 次要按钮 */
#secondaryBtn {{
    background-color: {cls.BG_CARD};
    color: {cls.TEXT_PRIMARY};
    border: 1px solid #999999;
    border-radius: 4px;
    padding: 0 16px;
    min-height: 30px;
}}
#secondaryBtn:hover {{
    border: 1px solid {cls.HOVER_COLOR};
    color: {cls.HOVER_COLOR};
}}

/* === 下拉框 === */
QComboBox {{
    background-color: {cls.BG_CARD};
    border: 1px solid #999999;
    border-radius: 4px;
    padding: 0 12px;
    min-height: 30px;
    max-height: 30px;
    min-width: 120px;
}}
QComboBox:hover {{
    border: 1px solid {cls.HOVER_COLOR};
}}
QComboBox:focus {{
    border: 1px solid {cls.HOVER_COLOR};
}}
QComboBox::drop-down {{
    border: none;
    width: 30px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}}
QComboBox::down-arrow {{
    image: url({_resource_url('assets/img/down.svg')});
    width: 16px;
    height: 16px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
    padding-right: 8px;
}}
QComboBox:on > QComboBox::down-arrow {{
    image: url({_resource_url('assets/img/down.svg')});
    transform: rotate(0deg);
}}
QComboBox:!on > QComboBox::down-arrow {{
    image: url({_resource_url('assets/img/down.svg')});
    transform: rotate(-90deg);
}}
QComboBox QAbstractItemView {{
    background: {cls.BG_CARD};
    border: 1px solid {cls.BORDER_DARK};
    border-radius: 4px;
    selection-background-color: {cls.HOVER_COLOR};
    padding: 4px;
}}

/* === 数字输入框 === */
QSpinBox {{
    background-color: {cls.BG_CARD};
    border: 1px solid #999999;
    border-radius: 4px;
    padding: 0 8px;
    min-height: 30px;
    max-height: 30px;
}}
QSpinBox:hover {{
    border: 1px solid {cls.HOVER_COLOR};
}}
QSpinBox:focus {{
    border: 1px solid {cls.HOVER_COLOR};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 20px;
    border-radius: 2px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {cls.BG_HEADER};
}}

/* === 复选框 === */
QCheckBox {{
    spacing: 8px;
    color: {cls.TEXT_PRIMARY};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #999999;
    background: {cls.BG_CARD};
}}
QCheckBox::indicator:hover {{
    border: 1px solid {cls.HOVER_COLOR};
}}
QCheckBox::indicator:checked {{
    background: {cls.PRIMARY_COLOR};
    border: 1px solid {cls.PRIMARY_COLOR};
}}

/* === 分组框 === */
QGroupBox {{
    background-color: {cls.BG_CARD};
    border: 1px solid {cls.BORDER_MEDIUM};
    border-radius: 4px;
    margin-top: 12px;
    padding: 12px 10px 8px;
    font-weight: bold;
    color: {cls.TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {cls.PRIMARY_COLOR};
}}

/* === 文件列表 === */
#fileList {{
    background: {cls.BG_CARD};
    border: 1px solid {cls.BORDER_LIGHT};
    border-radius: 4px;
    outline: none;
}}
#fileList::item {{
    padding: 8px;
    border-radius: 4px;
    margin: 1px 0;
}}
#fileList::item:selected {{
    background-color: {cls.HOVER_COLOR};
    color: white;
}}
#fileList::item:hover:!selected {{
    background-color: {cls.BG_HEADER};
}}

/* === 滑块 === */
QSlider::groove:horizontal {{
    border: none;
    height: 6px;
    background: {cls.BORDER_MEDIUM};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {cls.PRIMARY_COLOR};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
    border: 2px solid {cls.BG_CARD};
}}
QSlider::handle:horizontal:hover {{
    background: {cls.HOVER_COLOR};
}}
QSlider::sub-page:horizontal {{
    background: {cls.PRIMARY_COLOR};
    border-radius: 3px;
}}

/* === 进度条 === */
QProgressBar {{
    background: {cls.BORDER_MEDIUM};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {cls.PRIMARY_COLOR};
    border-radius: 4px;
}}

/* === 标签 === */
QLabel {{
    color: {cls.TEXT_PRIMARY};
}}
QLabel#info {{
    color: {cls.TEXT_MUTED};
    font-size: 12px;
}}

/* === 滚动条 === */
QScrollBar:vertical {{
    background: {cls.BG_MAIN};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {cls.BORDER_DARK};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {cls.HOVER_COLOR};
}}
QScrollBar:horizontal {{
    background: {cls.BG_MAIN};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {cls.BORDER_DARK};
    border-radius: 4px;
    min-width: 20px;
}}

/* === 状态栏 === */
QStatusBar {{
    background: {cls.BG_HEADER};
    border-top: 1px solid {cls.BORDER_MEDIUM};
}}

/* === 卡片面板 === */
#cardPanel {{
    background: {cls.BG_CARD};
    border-radius: 4px;
    border: 1px solid {cls.BORDER_LIGHT};
}}

/* === 卡片头部 === */
#cardHeader {{
    background: {cls.BG_HEADER};
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    border-bottom: 1px solid {cls.BORDER_MEDIUM};
}}

/* === 卡片底部 === */
#cardFooter {{
    background: {cls.BG_HEADER};
    border-top: 1px solid {cls.BORDER_MEDIUM};
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
}}

/* === 导航面板 === */
#navPanel {{
    background: {cls.BG_CARD};
    border-right: 1px solid {cls.BORDER_LIGHT};
}}

/* === 预览区域 === */
#previewArea {{
    border: 2px dashed {cls.BORDER_MEDIUM};
    border-radius: 8px;
    background: {cls.BG_HEADER};
}}

/* === 列表控件 === */
QListWidget {{
    background: {cls.BG_CARD};
    border: 1px solid {cls.BORDER_LIGHT};
    border-radius: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
    margin: 1px 0;
}}
QListWidget::item:selected {{
    background-color: {cls.HOVER_COLOR};
    color: white;
}}
QListWidget::item:hover:!selected {{
    background-color: {cls.BG_HEADER};
}}
"""

    @classmethod
    def get_button_styles(cls) -> dict:
        """获取按钮样式字典"""
        return {
            'primary': f"""
                QPushButton {{
                    background-color: {cls.PRIMARY_COLOR};
                    color: {cls.BG_CARD};
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {cls.PRIMARY_HOVER}; }}
                QPushButton:pressed {{ background-color: {cls.PRIMARY_PRESSED}; }}
            """,
            'secondary': f"""
                QPushButton {{
                    background: {cls.BG_CARD};
                    border: 1px solid {cls.BORDER_DARK};
                    border-radius: 5px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background: {cls.BG_MAIN};
                    border-color: {cls.PRIMARY_COLOR};
                    color: {cls.PRIMARY_COLOR};
                }}
            """,
            'danger': f"""
                QPushButton {{
                    background-color: {cls.DANGER};
                    color: {cls.BG_CARD};
                    border: none;
                    border-radius: 5px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{ background-color: #c0392b; }}
            """
        }

    @classmethod
    def get_dark_theme(cls) -> str:
        """获取暗色主题样式表"""
        return """
QMainWindow, QWidget {
    background-color: #2b2b2b;
    color: #e0e0e0;
    font-family: "Microsoft YaHei";
}
QGroupBox {
    background-color: #3a3a3a;
    border: 1px solid #555;
    border-radius: 8px;
    margin-top: 15px;
    padding: 18px 12px 10px;
    color: #e0e0e0;
}
QGroupBox::title { color: #4da6ff; }
#fileList { background: #3a3a3a; border: 1px solid #555; border-radius: 6px; }
#fileList::item { padding: 8px; border-radius: 4px; }
#fileList::item:selected { background: #264f78; color: #fff; }
QComboBox { background: #3a3a3a; border: 1px solid #555; border-radius: 5px; padding: 8px; color: #e0e0e0; }
QComboBox:hover { border-color: #4da6ff; }
QComboBox QAbstractItemView { background: #3a3a3a; color: #e0e0e0; }
#primaryBtn { background-color: #0d6efd; color: #fff; border: none; border-radius: 6px; padding: 10px 20px; font-weight: bold; }
#primaryBtn:hover { background-color: #0b5ed7; }
#secondaryBtn { background: #3a3a3a; color: #e0e0e0; border: 1px solid #555; border-radius: 5px; padding: 8px 16px; }
#secondaryBtn:hover { border-color: #4da6ff; color: #4da6ff; }
QCheckBox { color: #e0e0e0; }
QCheckBox::indicator { border: 2px solid #555; background: #3a3a3a; }
QCheckBox::indicator:checked { background: #0d6efd; border-color: #0d6efd; }
QSpinBox { background: #3a3a3a; border: 1px solid #555; border-radius: 5px; padding: 7px; color: #e0e0e0; }
QSlider::groove:horizontal { background: #555; height: 6px; border-radius: 3px; }
QSlider::handle:horizontal { background: #0d6efd; border-radius: 9px; }
QSlider::sub-page:horizontal { background: #0d6efd; }
QProgressBar { background: #555; border-radius: 6px; color: #fff; }
QProgressBar::chunk { background: #0d6efd; border-radius: 6px; }
QLabel { color: #e0e0e0; }
"""


def get_stylesheet(name: str = "default") -> str:
    """
    获取指定名称的样式表

    Args:
        name: 样式表名称 ("default", "dark")

    Returns:
        样式表字符串
    """
    themes = {
        "default": StyleSheet.get_global_stylesheet,
        "dark": StyleSheet.get_dark_theme,
    }
    getter = themes.get(name, StyleSheet.get_global_stylesheet)
    return getter()


# ============ 快捷样式常量 ============
PANEL_STYLE = """
    background: #ffffff;
    border-radius: 8px;
    border: 1px solid #dcdcdc;
"""

HEADER_STYLE = """
    background: #f8f8f8;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border-bottom: 1px solid #e0e0e0;
    padding: 10px 15px;
"""
