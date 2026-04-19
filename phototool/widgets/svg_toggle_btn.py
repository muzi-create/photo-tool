"""
SVG 切换按钮控件
支持旋转动画的 SVG 图标按钮
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRectF
from PyQt5.QtGui import QPainter
from PyQt5.QtSvg import QSvgRenderer

from phototool.utils.paths import asset_path


class SvgToggleBtn(QWidget):
    """支持旋转的 SVG 切换按钮"""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderer = None
        self._rotated = False
        self.setFixedSize(20, 20)
        self.setStyleSheet("background: transparent;")
        self._load_svg()

    def sizeHint(self):
        return QSize(20, 20)

    def minimumSizeHint(self):
        return QSize(20, 20)

    def _load_svg(self):
        svg_path = asset_path('img/down.svg')
        from pathlib import Path
        if Path(svg_path).exists():
            self._renderer = QSvgRenderer(svg_path)
            self.update()

    def set_rotated(self, rotated):
        self._rotated = rotated
        self.update()

    def paintEvent(self, event):
        if not self._renderer:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 绕中心点旋转：折叠时向左(◀)，展开时向右(▶)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(270 if not self._rotated else 0)
        painter.translate(-self.width() / 2, -self.height() / 2)
        # 渲染到正确的目标矩形
        self._renderer.render(painter, QRectF(0, 0, self.width(), self.height()))

    def mousePressEvent(self, event):
        self.clicked.emit()
