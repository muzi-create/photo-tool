"""
拖拽文件添加区域控件
支持拖拽图片文件到区域进行添加
"""

from pathlib import Path
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal


class DropArea(QWidget):
    """支持拖拽文件添加的区域"""
    file_dropped = pyqtSignal(str)

    SUPPORTED_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif'}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            has_images = any(
                Path(url.toLocalFile()).suffix.lower() in self.SUPPORTED_EXTS
                for url in event.mimeData().urls()
                if url.isLocalFile()
            )
            if has_images:
                event.acceptProposedAction()
                self.setStyleSheet("""
                    QWidget#previewDropZone {
                        border: 2px dashed #4a9eff;
                        background: #e8f4ff;
                    }
                """)
                return
        super().dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        self.setStyleSheet("")
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if Path(file_path).suffix.lower() in self.SUPPORTED_EXTS:
                        self.file_dropped.emit(file_path)
                        event.acceptProposedAction()
                        return
        super().dropEvent(event)
