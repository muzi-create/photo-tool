"""
图片处理工作线程
继承 QThread，通过信号机制更新主界面进度条
"""

from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from phototool.core.image_converter import ImageConverter


class ImageWorker(QThread):
    """
    图片处理工作线程

    signals:
        progress_updated(int percent, str filename): 进度更新信号
        conversion_finished(str output_path): 单个文件转换完成
        task_finished(bool success, str message): 全部任务完成
        error_occurred(str error_info): 发生错误
    """

    progress_updated = pyqtSignal(int, str)
    conversion_finished = pyqtSignal(str)
    task_finished = pyqtSignal(bool, str)
    error_occurred = pyqtSignal(str)
    current_index_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        self.output_format = "JPEG"
        self.quality = 85
        self.output_dir = ""
        self.resize_enabled = False
        self.resize_width = 1920
        self.resize_height = 1080
        self.keep_aspect_ratio = True
        self._is_running = True
        self._current_index = 0

    def set_config(self, files: list, output_format: str, quality: int,
                   output_dir: str, resize_opts: dict = None):
        """设置工作线程配置"""
        self.files = list(files)
        self.output_format = output_format.upper()
        self.quality = quality
        self.output_dir = output_dir
        self._is_running = True
        if resize_opts:
            self.resize_enabled = resize_opts.get('enabled', False)
            self.resize_width = resize_opts.get('width', 1920)
            self.resize_height = resize_opts.get('height', 1080)
            self.keep_aspect_ratio = resize_opts.get('keep_ratio', True)

    def stop(self):
        self._is_running = False

    def is_running(self) -> bool:
        return self._is_running and self.isRunning()

    def run(self):
        if not self.files:
            self.task_finished.emit(False, "没有要处理的文件")
            return
        if not self.output_dir or not Path(self.output_dir).exists():
            self.error_occurred.emit(f"输出目录无效: {self.output_dir}")
            self.task_finished.emit(False, "输出目录无效")
            return
        total = len(self.files)
        success_count = 0
        failed_count = 0
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        for index, file_path in enumerate(self.files):
            if not self._is_running:
                self.task_finished.emit(False, "任务已取消")
                return
            self._current_index = index
            filename = Path(file_path).name
            progress = int((index / total) * 100)
            self.progress_updated.emit(progress, filename)
            self.current_index_changed.emit(index + 1, total)
            try:
                output_path = self._process_single_file(file_path)
                if output_path:
                    success_count += 1
                    self.conversion_finished.emit(str(output_path))
            except Exception as e:
                failed_count += 1
                error_msg = f"处理 {filename} 时出错: {str(e)}"
                self.error_occurred.emit(error_msg)
        if failed_count == 0:
            self.task_finished.emit(True, f"全部完成! 成功处理 {success_count} 个文件")
        else:
            self.task_finished.emit(True, f"完成! 成功: {success_count}, 失败: {failed_count}")

    def _process_single_file(self, file_path: str) -> Path:
        ext_map = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp', 'BMP': '.bmp'}
        output_ext = ext_map.get(self.output_format, '.jpg')
        output_path = Path(self.output_dir) / f"{Path(file_path).stem}{output_ext}"
        with ImageConverter(file_path) as converter:
            if self.resize_enabled:
                converter.resize(
                    size=(self.resize_width, self.resize_height),
                    output_path=output_path,
                    quality=self.quality,
                    keep_aspect_ratio=self.keep_aspect_ratio
                )
            else:
                converter.convert_format(
                    output_format=self.output_format,
                    output_path=output_path,
                    quality=self.quality
                )
        return output_path

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def total_count(self) -> int:
        return len(self.files)

    def get_progress_text(self) -> str:
        return f"{self._current_index + 1}/{self.total_count}"
