"""
ImageConverter - 图片格式转换、质量压缩和尺寸缩放工具类
使用 Pillow (PIL) 库实现
"""

from PIL import Image
from pathlib import Path
from typing import Tuple, Optional, Union, List, Dict


class ImageConverter:
    """图片处理工具类，支持格式转换、质量压缩和尺寸缩放"""

    # 支持的输出格式及其默认质量
    SUPPORTED_FORMATS = {
        'JPEG': {'ext': '.jpg', 'default_quality': 85},
        'PNG': {'ext': '.png', 'default_quality': 90},
        'WEBP': {'ext': '.webp', 'default_quality': 85},
        'BMP': {'ext': '.bmp', 'default_quality': 100},
    }

    # 企业级图标尺寸预设
    ICON_PRESETS = {
        'windows': [16, 32, 48, 256],           # Windows 系统图标
        'ios': [20, 29, 40, 58, 60, 76, 80, 87, 120, 152, 167, 180, 1024],  # iOS 应用图标
        'android': [36, 48, 72, 96, 144, 192, 512],  # Android 应用图标
        'favicon': [16, 32, 48, 64, 128, 180, 192, 256],  # 网站 favicon
        'apple_touch': [57, 60, 72, 76, 114, 120, 144, 152, 180],  # Apple Touch Icon
        'microsoft': [70, 150, 310, 310, 150, 70],  # Windows 10/11 磁贴图标
        'universal': [16, 32, 48, 64, 128, 256, 512, 1024],  # 通用尺寸
    }

    # Windows ICO 文件推荐尺寸
    ICO_SIZES = [16, 32, 48, 64, 128, 256]

    def __init__(self, image_path: Union[str, Path]):
        """
        初始化 ImageConverter

        Args:
            image_path: 图片文件路径
        """
        self.image_path = Path(image_path)
        if not self.image_path.exists():
            raise FileNotFoundError(f"图片文件不存在: {self.image_path}")
        self.image = Image.open(self.image_path)

    @staticmethod
    def _ensure_rgb_mode(image: Image.Image, preserve_transparency: bool = False) -> Image.Image:
        """
        确保图片处于 RGB 模式，处理透明通道问题

        Args:
            image: PIL Image 对象
            preserve_transparency: 是否保留透明通道（对于输出格式不支持时设为 False）

        Returns:
            转换后的 Image 对象
        """
        # 如果已关闭透明通道的 GIF，不处理
        if hasattr(image, 'info') and 'transparency' in image.info and image.mode == 'P':
            pass

        # RGBA -> RGB（处理 PNG 转 JPG 等情况）
        if image.mode == 'RGBA':
            # 创建白色背景
            background = Image.new('RGB', image.size, (255, 255, 255))
            # 将原图的不透明区域合成到白色背景上
            background.paste(image, mask=image.split()[3])  # 使用 alpha 通道作为 mask
            return background

        # P 模式（调色板模式，带透明色）
        elif image.mode == 'P':
            try:
                # 尝试获取透明色索引
                transparency = image.info.get('transparency')
                if transparency is not None:
                    # 转换为 RGBA 再处理
                    rgba_image = image.convert('RGBA')
                    background = Image.new('RGB', rgba_image.size, (255, 255, 255))
                    background.paste(rgba_image, mask=rgba_image.split()[3])
                    return background
            except (KeyError, ValueError):
                pass
            return image.convert('RGB')

        # L 模式（灰度图）-> RGB
        elif image.mode == 'L':
            return image.convert('RGB')

        # LA 模式（灰度+透明）-> RGB
        elif image.mode == 'LA':
            rgba_image = image.convert('RGBA')
            background = Image.new('RGB', rgba_image.size, (255, 255, 255))
            background.paste(rgba_image, mask=rgba_image.split()[3])
            return background

        # 其他模式（如 CMYK）直接转换
        elif image.mode not in ('RGB', 'RGBX'):
            return image.convert('RGB')

        return image

    @staticmethod
    def _get_output_path(
        original_path: Path,
        suffix: str,
        output_dir: Optional[Path] = None,
        new_ext: Optional[str] = None
    ) -> Path:
        """
        生成输出文件路径

        Args:
            original_path: 原图路径
            suffix: 文件名后缀
            output_dir: 输出目录，None 则使用原图目录
            new_ext: 新的扩展名

        Returns:
            输出文件路径
        """
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            stem = original_path.stem + suffix
            ext = new_ext or original_path.suffix.lower()
            return output_dir / f"{stem}{ext}"

        stem = original_path.stem + suffix
        ext = new_ext or original_path.suffix.lower()
        return original_path.parent / f"{stem}{ext}"

    def convert_format(
        self,
        output_format: str,
        output_path: Optional[Union[str, Path]] = None,
        quality: Optional[int] = None,
        preserve_transparency: bool = False
    ) -> Path:
        """
        转换图片格式

        Args:
            output_format: 目标格式 ('JPEG', 'PNG', 'WEBP', 'BMP')
            output_path: 输出文件路径，None 则自动生成
            quality: 图片质量 1-100，None 则使用默认值
            preserve_transparency: 是否保留透明通道（PNG/WEBP）

        Returns:
            输出文件路径
        """
        output_format = output_format.upper()
        if output_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的格式: {output_format}")

        # 确定输出路径
        if output_path is None:
            new_ext = self.SUPPORTED_FORMATS[output_format]['ext']
            output_path = self._get_output_path(self.image_path, '_converted', new_ext=new_ext)
        else:
            output_path = Path(output_path)

        # 获取质量参数
        if quality is None:
            quality = self.SUPPORTED_FORMATS[output_format]['default_quality']

        # 处理透明通道
        image = self.image
        if output_format in ('JPEG', 'BMP'):
            # JPEG 和 BMP 不支持透明通道，必须填充
            image = self._ensure_rgb_mode(image, preserve_transparency=False)
        elif not preserve_transparency and image.mode == 'RGBA':
            # 用户选择不保留透明通道
            image = self._ensure_rgb_mode(image, preserve_transparency=False)

        # 保存图片
        save_kwargs = {'quality': quality} if output_format != 'PNG' else {}
        if output_format == 'PNG':
            save_kwargs['optimize'] = True

        image.save(output_path, format=output_format, **save_kwargs)
        return output_path

    def compress(
        self,
        output_path: Optional[Union[str, Path]] = None,
        quality: int = 85,
        max_size_kb: Optional[int] = None
    ) -> Path:
        """
        压缩图片质量

        Args:
            output_path: 输出文件路径，None 则自动生成
            quality: 初始压缩质量 1-100
            max_size_kb: 目标最大文件大小(KB)，会自动调整质量达到目标

        Returns:
            输出文件路径
        """
        if output_path is None:
            output_path = self._get_output_path(self.image_path, '_compressed')
        else:
            output_path = Path(output_path)

        image = self._ensure_rgb_mode(self.image)

        if max_size_kb is not None:
            # 迭代压缩直到达到目标大小
            min_quality = 10
            current_quality = quality

            while current_quality >= min_quality:
                image.save(output_path, format=self._get_format_from_ext(output_path.suffix),
                          quality=current_quality, optimize=True)
                file_size = output_path.stat().st_size / 1024  # KB

                if file_size <= max_size_kb:
                    break

                current_quality -= 5
            else:
                # 如果达到最小质量仍超过目标大小，使用最小质量保存
                image.save(output_path, format=self._get_format_from_ext(output_path.suffix),
                          quality=min_quality, optimize=True)
        else:
            image.save(output_path, format=self._get_format_from_ext(output_path.suffix),
                      quality=quality, optimize=True)

        return output_path

    def resize(
        self,
        size: Tuple[int, int],
        output_path: Optional[Union[str, Path]] = None,
        quality: int = 85,
        keep_aspect_ratio: bool = False,
        resample: Optional[str] = None
    ) -> Path:
        """
        调整图片尺寸

        Args:
            size: 目标尺寸 (width, height)
            output_path: 输出文件路径，None 则自动生成
            quality: 输出图片质量
            keep_aspect_ratio: 是否保持宽高比（使用 size 作为最大尺寸）
            resample: 重采样方法 ('NEAREST', 'BILINEAR', 'BICUBIC', 'LANCZOS')

        Returns:
            输出文件路径
        """
        if output_path is None:
            output_path = self._get_output_path(self.image_path, f'_resized{size[0]}x{size[1]}')
        else:
            output_path = Path(output_path)

        # 获取重采样方法
        resample_methods = {
            'NEAREST': Image.Resampling.NEAREST,
            'BILINEAR': Image.Resampling.BILINEAR,
            'BICUBIC': Image.Resampling.BICUBIC,
            'LANCZOS': Image.Resampling.LANCZOS,
        }

        if resample and resample.upper() in resample_methods:
            resample_mode = resample_methods[resample.upper()]
        else:
            resample_mode = Image.Resampling.LANCZOS  # 默认使用高质量

        # 计算最终尺寸
        original_width, original_height = self.image.size

        if keep_aspect_ratio:
            # 保持宽高比，计算缩放后的尺寸
            ratio_w = size[0] / original_width
            ratio_h = size[1] / original_height
            ratio = min(ratio_w, ratio_h)  # 使用较小的比例确保不超出目标尺寸
            new_size = (int(original_width * ratio), int(original_height * ratio))
        else:
            new_size = size

        # 创建缩略图
        resized_image = self.image.resize(new_size, resample=resample_mode)
        resized_image = self._ensure_rgb_mode(resized_image)

        # 保存
        resized_image.save(output_path, quality=quality, optimize=True)

        return output_path

    def thumbnail(
        self,
        max_size: Tuple[int, int],
        output_path: Optional[Union[str, Path]] = None,
        quality: int = 85
    ) -> Path:
        """
        生成缩略图（保持宽高比，不变形）

        Args:
            max_size: 最大尺寸 (max_width, max_height)
            output_path: 输出文件路径，None 则自动生成
            quality: 输出图片质量

        Returns:
            输出文件路径
        """
        if output_path is None:
            output_path = self._get_output_path(self.image_path, '_thumb')
        else:
            output_path = Path(output_path)

        # 复制图片以避免修改原图
        image = self.image.copy()
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        image = self._ensure_rgb_mode(image)
        image.save(output_path, quality=quality, optimize=True)

        return output_path

    @staticmethod
    def _get_format_from_ext(ext: str) -> str:
        """根据扩展名获取格式"""
        ext_map = {
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG',
            '.png': 'PNG',
            '.webp': 'WEBP',
            '.bmp': 'BMP',
        }
        return ext_map.get(ext.lower(), 'JPEG')

    def rotate(self, angle: float, output_path: Optional[Union[str, Path]] = None,
               expand: bool = True, quality: int = 95) -> Path:
        """
        旋转图片

        Args:
            angle: 旋转角度（正数逆时针，负数顺时针）
            output_path: 输出文件路径
            expand: 是否扩展画布以容纳旋转后的图片
            quality: 输出质量（仅对 JPEG 有效）

        Returns:
            输出文件路径
        """
        if output_path is None:
            output_path = self._get_output_path(self.image_path, f'_rotated{angle}')
        else:
            output_path = Path(output_path)

        image = self.image.copy()
        rotated = image.rotate(angle, expand=expand, resample=Image.Resampling.BICUBIC)
        rotated = self._ensure_rgb_mode(rotated)
        rotated.save(output_path, quality=quality, optimize=True)

        return output_path

    def crop(self, box: Tuple[int, int, int, int], output_path: Optional[Union[str, Path]] = None,
             quality: int = 95) -> Path:
        """
        裁剪图片

        Args:
            box: 裁剪区域 (left, top, right, bottom)
            output_path: 输出文件路径
            quality: 输出质量

        Returns:
            输出文件路径
        """
        if output_path is None:
            output_path = self._get_output_path(self.image_path, '_cropped')
        else:
            output_path = Path(output_path)

        image = self.image.copy()
        cropped = image.crop(box)
        cropped = self._ensure_rgb_mode(cropped)
        cropped.save(output_path, quality=quality, optimize=True)

        return output_path

    def flip_horizontal(self, output_path: Optional[Union[str, Path]] = None,
                        quality: int = 95) -> Path:
        """水平翻转"""
        if output_path is None:
            output_path = self._get_output_path(self.image_path, '_flipped_h')
        else:
            output_path = Path(output_path)

        image = self.image.copy()
        flipped = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        flipped = self._ensure_rgb_mode(flipped)
        flipped.save(output_path, quality=quality, optimize=True)

        return output_path

    def flip_vertical(self, output_path: Optional[Union[str, Path]] = None,
                      quality: int = 95) -> Path:
        """垂直翻转"""
        if output_path is None:
            output_path = self._get_output_path(self.image_path, '_flipped_v')
        else:
            output_path = Path(output_path)

        image = self.image.copy()
        flipped = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        flipped = self._ensure_rgb_mode(flipped)
        flipped.save(output_path, quality=quality, optimize=True)

        return output_path

    def get_info(self) -> dict:
        """获取图片信息"""
        return {
            'path': str(self.image_path),
            'format': self.image.format,
            'mode': self.image.mode,
            'size': self.image.size,
            'width': self.image.width,
            'height': self.image.height,
            'file_size_kb': round(self.image_path.stat().st_size / 1024, 2),
        }

    def _prepare_icon_image(self, target_size: int) -> Image.Image:
        """
        准备图标尺寸的图片（精确缩放到目标尺寸）

        Args:
            target_size: 目标尺寸（正方形）

        Returns:
            target_size x target_size 的 Image 对象
        """
        image = self.image.copy()
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        original_width, original_height = image.size

        # 计算缩放比例，保持宽高比
        ratio_w = target_size / original_width
        ratio_h = target_size / original_height
        # 使用较小的比例，确保图片完整填充
        ratio = min(ratio_w, ratio_h)

        # 计算缩放后的尺寸
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)

        # 使用高质量缩放
        if new_width != original_width or new_height != original_height:
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 创建正方形画布并居中放置
        canvas = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 0))
        x = (target_size - new_width) // 2
        y = (target_size - new_height) // 2
        canvas.paste(image, (x, y), image if image.mode == 'RGBA' else None)

        return canvas

    def generate_icon(
        self,
        output_path: Union[str, Path],
        size: int,
        output_format: str = 'PNG'
    ) -> Path:
        """
        生成指定尺寸的高质量图标文件

        Args:
            output_path: 输出文件路径
            size: 目标尺寸（正方形）
            output_format: 输出格式 ('PNG' 或 'ICO')

        Returns:
            生成的图标文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 生成图标
        img = self._prepare_icon_image(size)

        if output_format.upper() == 'ICO':
            # ICO 需要 RGB 模式
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
            else:
                rgb_img = img.convert('RGB')
            rgb_img.save(output_path, format='ICO', sizes=[(size, size)])
        else:
            img.save(output_path, format='PNG', optimize=True)

        return output_path

    def generate_app_icons(
        self,
        output_dir: Union[str, Path],
        preset: str = 'ios',
        include_android: bool = False
    ) -> Dict[str, List[Path]]:
        """
        生成多平台应用图标集

        Args:
            output_dir: 输出目录
            preset: 主预设 ('ios', 'android', 'favicon')
            include_android: 是否同时生成 Android 图标

        Returns:
            包含各平台图标路径的字典
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        # iOS 图标
        if preset in ['ios', 'apple_touch']:
            ios_sizes = self.ICON_PRESETS['ios']
            ios_dir = output_dir / 'ios'
            ios_dir.mkdir(exist_ok=True)
            ios_paths = []
            for size in ios_sizes:
                img = self._prepare_icon_image(size)
                out_path = ios_dir / f"icon_{size}x{size}.png"
                img.save(out_path, format='PNG', optimize=True)
                ios_paths.append(out_path)
            results['ios'] = ios_paths

        # Android 图标
        if preset == 'android' or include_android:
            android_sizes = self.ICON_PRESETS['android']
            android_dir = output_dir / 'android'
            android_dir.mkdir(exist_ok=True)
            android_paths = []
            for size in android_sizes:
                img = self._prepare_icon_image(size)
                out_path = android_dir / f"icon_{size}x{size}.png"
                img.save(out_path, format='PNG', optimize=True)
                android_paths.append(out_path)
            results['android'] = android_paths

        # Favicon 图标
        if preset == 'favicon' or include_android:
            favicon_dir = output_dir / 'favicon'
            favicon_dir.mkdir(exist_ok=True)
            favicon_paths = []

            # 生成 PNG 和 ICO
            ico_sizes = self.ICO_SIZES
            ico_images = []
            for s in ico_sizes:
                img = self._prepare_icon_image(s)
                if img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[3])
                    ico_images.append(rgb_img)
                else:
                    ico_images.append(img.convert('RGB'))
            ico_path = favicon_dir / 'favicon.ico'
            ico_images[0].save(
                ico_path, format='ICO',
                sizes=[(s, s) for s in ico_sizes],
                append_images=ico_images[1:]
            )
            favicon_paths.append(ico_path)
            results['favicon'] = favicon_paths

        return results

    def generate_favicon_package(self, output_dir: Union[str, Path]) -> Dict[str, Path]:
        """
        生成完整的网站 favicon 包

        Args:
            output_dir: 输出目录

        Returns:
            各文件路径的字典
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}
        sizes = [16, 32, 48, 64, 128, 180, 192, 256]

        for size in sizes:
            img = self._prepare_icon_image(size)
            out_path = output_dir / f"favicon-{size}x{size}.png"
            img.save(out_path, format='PNG', optimize=True)
            results[f'favicon_{size}'] = out_path

        # 生成 favicon.ico
        ico_sizes = [16, 32, 48, 256]
        ico_images = []
        for s in ico_sizes:
            img = self._prepare_icon_image(s)
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                ico_images.append(rgb_img)
            else:
                ico_images.append(img.convert('RGB'))
        ico_path = output_dir / 'favicon.ico'
        ico_images[0].save(
            ico_path, format='ICO',
            sizes=[(s, s) for s in ico_sizes],
            append_images=ico_images[1:]
        )
        results['favicon_ico'] = ico_path

        # Apple Touch Icon
        img = self._prepare_icon_image(180)
        apple_path = output_dir / 'apple-touch-icon.png'
        img.save(apple_path, format='PNG', optimize=True)
        results['apple_touch'] = apple_path

        # Android Chrome Icon
        img = self._prepare_icon_image(192)
        android_path = output_dir / 'android-chrome-192x192.png'
        img.save(android_path, format='PNG', optimize=True)
        results['android_chrome'] = android_path

        return results

    def resize_to_square(
        self,
        size: int,
        output_path: Optional[Union[str, Path]] = None,
        background_color: Optional[Tuple[int, int, int, int]] = (0, 0, 0, 0)
    ) -> Path:
        """
        将图片调整为正方形（居中，保留透明）

        Args:
            size: 目标尺寸
            output_path: 输出路径
            background_color: 背景色 RGBA

        Returns:
            输出路径
        """
        if output_path is None:
            output_path = self._get_output_path(self.image_path, f'_square{size}', new_ext='.png')
        else:
            output_path = Path(output_path)

        img = self.image.copy()
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # 创建正方形画布
        new_img = Image.new('RGBA', (size, size), background_color)

        # 缩放图片
        img.thumbnail((size, size), Image.Resampling.LANCZOS)

        # 居中
        x = (size - img.width) // 2
        y = (size - img.height) // 2
        new_img.paste(img, (x, y))

        new_img.save(output_path, format='PNG', optimize=True)
        return output_path

    def close(self):
        """关闭图片，释放资源"""
        self.image.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
