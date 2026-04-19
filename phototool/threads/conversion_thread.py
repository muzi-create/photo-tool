"""
图片格式转换工作线程
在后台线程中执行批量图片转换操作
"""

from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from PIL import Image
from phototool.core.image_converter import ImageConverter


class ConversionThread(QThread):
    """图片批量转换工作线程"""

    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output_format, quality, output_dir, resize_opts, rotate_opts,
                 single_filename=None, crop_opts=None):
        super().__init__()
        self.files = files
        self.output_format = output_format
        self.quality = quality
        self.output_dir = output_dir
        self.resize_opts = resize_opts
        self.rotate_opts = rotate_opts
        self.single_filename = single_filename
        self.crop_opts = crop_opts  # {'enabled': bool, 'rect': (x1, y1, x2, y2)}
        self._running = True

    def run(self):
        success = fail = 0
        for i, f in enumerate(self.files):
            if not self._running: break
            try:
                self.progress_updated.emit(int((i + 1) / len(self.files) * 100), Path(f).name)
                with ImageConverter(f) as converter:
                    ext = '.jpg' if self.output_format == 'JPEG' else f'.{self.output_format.lower()}'
                    if self.single_filename:
                        out_path = Path(self.output_dir) / self.single_filename
                    else:
                        out_path = Path(self.output_dir) / f"{Path(f).stem}{ext}"

                    image = converter.image.copy()
                    orig_w, orig_h = image.size

                    # 应用裁剪
                    if self.crop_opts and self.crop_opts.get('enabled'):
                        crop_ratios = self.crop_opts.get('rect')
                        if crop_ratios:
                            x1_ratio, y1_ratio, x2_ratio, y2_ratio = crop_ratios
                            x1 = max(0, int(x1_ratio * orig_w))
                            y1 = max(0, int(y1_ratio * orig_h))
                            x2 = min(orig_w, int(x2_ratio * orig_w))
                            y2 = min(orig_h, int(y2_ratio * orig_h))
                            if x2 > x1 and y2 > y1:
                                image = image.crop((x1, y1, x2, y2))

                    # 应用旋转/翻转
                    if self.rotate_opts['flip_h']:
                        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                    if self.rotate_opts['flip_v']:
                        image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                    if self.rotate_opts['angle'] != 0:
                        image = image.rotate(-self.rotate_opts['angle'], expand=True, resample=Image.Resampling.BICUBIC)

                    # 尺寸调整
                    if self.resize_opts['enabled']:
                        ratio_w = self.resize_opts['width'] / image.width
                        ratio_h = self.resize_opts['height'] / image.height
                        if self.resize_opts['keep_ratio']:
                            ratio = min(ratio_w, ratio_h)
                            new_size = (int(image.width * ratio), int(image.height * ratio))
                        else:
                            new_size = (self.resize_opts['width'], self.resize_opts['height'])
                        image = image.resize(new_size, Image.Resampling.LANCZOS)

                    # 格式处理
                    if image.mode in ('RGBA', 'P'):
                        if self.output_format == 'JPEG':
                            bg = Image.new('RGB', image.size, (255, 255, 255))
                            if image.mode == 'RGBA':
                                bg.paste(image, mask=image.split()[3])
                            else:
                                bg.paste(image)
                            image = bg
                        elif self.output_format != 'PNG' and self.output_format != 'WEBP':
                            image = image.convert('RGB')
                    elif image.mode == 'P':
                        image = image.convert('RGB')

                    save_kwargs = {'quality': self.quality} if self.output_format != 'PNG' else {}
                    if self.output_format == 'PNG':
                        save_kwargs['optimize'] = True
                    image.save(out_path, format=self.output_format, **save_kwargs)

                success += 1
            except Exception:
                fail += 1
        self.finished.emit(True, f"完成! 成功: {success}, 失败: {fail}")

    def stop(self):
        self._running = False
