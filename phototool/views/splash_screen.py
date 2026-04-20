"""
启动画面 - 显示应用加载进度
"""

from PyQt5.QtWidgets import QSplashScreen, QProgressBar, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QFont, QPixmap, QPainter, QLinearGradient, QColor


class SplashScreen(QSplashScreen):
    """自定义启动画面，带进度条"""

    def __init__(self):
        # 创建纯色背景
        pixmap = QPixmap(400, 300)
        pixmap.fill(Qt.white)
        super().__init__(pixmap)

        self.setWindowFlag(Qt.WindowStaysOnTopHint)

        # 进度值 0-100
        self._progress = 0
        self._message = "正在启动..."
        self._title = "图片转换工具"

        # 创建状态标签
        self.status_label = QLabel(self._message, self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Microsoft YaHei", 10))
        self.status_label.setStyleSheet("color: #888; background: transparent;")
        self.status_label.adjustSize()
        self.status_label.move(200 - self.status_label.width() // 2, 200)

        # 创建进度条
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedSize(280, 8)
        self.progress_bar.move(60, 175)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background: #e8e8e8;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a9eff, stop:1 #6bb5ff);
            }
        """)

    def set_progress(self, value, message=""):
        """设置进度和状态文本"""
        self._progress = max(0, min(100, value))
        self.progress_bar.setValue(self._progress)
        if message:
            self._message = message
            self.status_label.setText(message)
            self.status_label.adjustSize()
            self.status_label.move(200 - self.status_label.width() // 2, 200)
        self.update()

    def drawContents(self, painter):
        """绘制启动画面内容"""
        super().drawContents(painter)

        painter.setPen(Qt.NoPen)

        # Logo "PT"
        painter.setFont(QFont("Microsoft YaHei", 48, QFont.Bold))
        painter.setPen(QColor("#4a9eff"))
        painter.drawText(QRect(0, 50, 400, 70), Qt.AlignCenter, "PT")

        # 标题
        painter.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        painter.setPen(QColor("#333333"))
        painter.drawText(QRect(0, 120, 400, 30), Qt.AlignCenter, self._title)
