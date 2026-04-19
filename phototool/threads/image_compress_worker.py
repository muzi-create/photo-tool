"""
图片压缩工作线程
在后台线程中执行批量图片压缩操作
"""

from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from phototool.core.image_converter import ImageConverter


class ImageCompressWorker(QThread):
    """图片压缩工作线程"""

    progress_updated = pyqtSignal(int, str)
    compression_finished = pyqtSignal(str, int, int)  # path, original_size, new_size
    task_finished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        self.output_dir = ""
        self.quality = 85
        self.max_size_kb = None
        self._is_running = True

    def set_config(self, files: list, output_dir: str, quality: int = 85, max_size_kb: int = None):
        self.files = list(files)
        self.output_dir = output_dir
        self.quality = quality
        self.max_size_kb = max_size_kb
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        if not self.files:
            self.task_finished.emit(False, "没有要处理的文件")
            return
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        success = 0
        for i, f in enumerate(self.files):
            if not self._is_running:
                self.task_finished.emit(False, "任务已取消")
                return
            self.progress_updated.emit(int((i + 1) / len(self.files) * 100), Path(f).name)
            try:
                with ImageConverter(f) as converter:
                    output_path = Path(self.output_dir) / f"{Path(f).stem}_compressed.jpg"
                    orig_size = Path(f).stat().st_size // 1024
                    converter.compress(str(output_path), self.quality, self.max_size_kb)
                    new_size = output_path.stat().st_size // 1024
                    self.compression_finished.emit(str(output_path), orig_size, new_size)
                success += 1
            except Exception as e:
                print(f"压缩失败 {f}: {e}")
        self.task_finished.emit(True, f"完成! 成功压缩 {success} 个文件")
