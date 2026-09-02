"""Qt adapter for batch image conversion."""

from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from phototool.core.conversion import ConversionOptions, ImageConversionService


class ConversionThread(QThread):
    """图片批量转换工作线程"""

    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output_dir, options, single_filename=None, parent=None):
        super().__init__(parent)
        self.files = tuple(files)
        self.output_dir = Path(output_dir)
        self.options = options
        self.single_filename = single_filename
        self._running = True

        if not isinstance(options, ConversionOptions):
            raise TypeError("options 必须是 ConversionOptions")

    def run(self):
        success_count = 0
        failure_count = 0
        errors = []
        total = len(self.files)
        if total == 0:
            self.finished.emit(False, "没有要处理的文件")
            return

        for index, source_path in enumerate(self.files):
            if not self._running:
                self.finished.emit(False, "任务已取消")
                return
            try:
                self.progress_updated.emit(
                    int((index + 1) / total * 100), Path(source_path).name
                )
                output_path = self._output_path(source_path)
                ImageConversionService.convert_file(
                    source_path, output_path, self.options
                )
                success_count += 1
            except Exception as exc:
                failure_count += 1
                errors.append(f"{Path(source_path).name}: {exc}")

        succeeded = failure_count == 0
        message = f"完成! 成功: {success_count}, 失败: {failure_count}"
        if errors:
            message += f"\n首个错误: {errors[0]}"
        self.finished.emit(succeeded, message)

    def _output_path(self, source_path):
        if self.single_filename:
            return self.output_dir / self.single_filename
        extension = ImageConversionService.output_extension(
            self.options.output_format
        )
        return self.output_dir / f"{Path(source_path).stem}{extension}"

    def stop(self):
        self._running = False
