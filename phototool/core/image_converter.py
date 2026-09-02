"""
ImageConverter - 图片格式转换、质量压缩和尺寸缩放工具类
使用 Pillow (PIL) 库实现
"""

from pathlib import Path
from typing import Tuple, Optional, Union, List, Dict

from PIL import Image


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
        'windows': [16, 32, 48, 256],  # Windows 系统图标
        'ios': [20, 29, 40, 58, 60, 76, 80, 87, 120, 152, 167, 180, 1024],  # iOS 应用图标
        'android': [36, 48, 72, 96, 144, 192, 512],  # Android 应用图标
        'favicon': [16, 32, 48, 64, 128, 180, 192, 256],  # 网站 favicon
        'apple_touch': [57, 60, 72, 76, 114, 120, 144, 152, 180],  # Apple Touch Icon
        'microsoft': [70, 150, 310, 310, 150, 70],  # Windows 10/11 磁贴图标
        'universal': [16, 32, 48, 64, 128, 256, 512, 1024],  # 通用尺寸
    }

    # Windows ICO 文件推荐尺寸（扩充至 1024x1024 适配 4K/8K 高分屏）
    ICO_SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]

    # 小图锐化阈值（32px 及以下需要锐化）
    SHARPEN_THRESHOLD = 32

    # 分级锐化策略（根据尺寸动态调整强度）
    SHARPEN_LEVELS = {
        16: {'radius': 0.3, 'percent': 200, 'threshold': 2},  # 极小图标，强锐化
        24: {'radius': 0.4, 'percent': 175, 'threshold': 2},  # 小图标，中强锐化
        32: {'radius': 0.5, 'percent': 150, 'threshold': 2},  # 标准小图标
    }

    # 默认 ICO 尺寸（不含超大分辨率，默认 256）
    DEFAULT_ICO_SIZES = [16, 32, 48, 64, 128, 256]

    # 遮罩形状类型
    MASK_SHAPES = ['square', 'circle', 'rounded', 'none']

    def __init__(self, image_path: Union[str, Path]):
        """
        初始化 ImageConverter

        Args:
            image_path: 图片文件路径
        """
        self.image_path = Path(image_path)
        if not self.image_path.exists():
            raise FileNotFoundError(f"图片文件不存在: {self.image_path}")

        # 增强文件头校验：使用 verify() 方法验证图像完整性
        try:
            with Image.open(self.image_path) as test_img:
                test_img.verify()
        except Exception as e:
            raise ValueError(f"文件不是有效的图像文件或已损坏: {self.image_path}\n错误: {e}")

        # 重新打开图像以进行实际处理
        self.image = Image.open(self.image_path)
        # 强制转换为 RGBA 以确保一致性
        if self.image.mode not in ('RGB', 'RGBA', 'P', 'L'):
            self.image = self.image.convert('RGBA')

        # 初始化图像缓存字典（用于批量处理优化）
        self._icon_cache: Dict[Tuple[int, str, str], Image.Image] = {}

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

    @staticmethod
    def _sharpen_small_icon(image: Image.Image, target_size: int) -> Image.Image:
        """
        对小尺寸图标应用轻微锐化滤镜，抵消缩小算法产生的模糊感

        Args:
            image: PIL Image 对象
            target_size: 目标尺寸

        Returns:
            锐化后的 Image 对象（如果需要锐化）
        """
        if target_size > ImageConverter.SHARPEN_THRESHOLD:
            return image

        # 根据尺寸获取对应的锐化参数（分级锐化策略）
        sharpen_config = ImageConverter.SHARPEN_LEVELS.get(
            target_size,
            {'radius': 0.5, 'percent': 150, 'threshold': 2}  # 默认参数
        )

        sharpened = image.filter(Image.Filter.UnsharpMask(
            radius=sharpen_config['radius'],
            percent=sharpen_config['percent'],
            threshold=sharpen_config['threshold']
        ))
        return sharpened

    def _smart_background_adapt(
            self,
            image: Image.Image,
            force_transparent: bool = True,
            target_bg_color: Optional[Tuple[int, int, int]] = None
    ) -> Image.Image:
        """
        智能背景适配：根据原图特性和目标背景色决定保留透明底还是合成纯色底

        Args:
            image: RGBA Image 对象
            force_transparent: 是否强制保留透明（True 保留透明，False 根据情况判断）
            target_bg_color: 目标背景色 RGB 元组（如 (45, 45, 45) 深灰），用于深色模式适配

        Returns:
            处理后的 Image 对象
        """
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        alpha = image.split()[3]
        alpha_data = alpha.getdata()

        # 检查 Alpha 通道的使用情况
        transparent_pixels = sum(1 for a in alpha_data if a < 128)
        total_pixels = len(alpha_data)
        transparent_ratio = transparent_pixels / total_pixels

        # 智能决策：
        # 1. 如果指定了目标背景色，预合成到该背景上（深色模式适配）
        # 2. 如果强制保留透明，或者透明比例在合理范围内（5%-95%），保留透明
        # 3. 如果原图几乎没有透明（<5%），转换为纯色底
        # 4. 始终保留透明通道，不添加任何背景色
        if target_bg_color is not None:
            # 深色模式适配：预合成到目标背景色上，消除暗晕
            bg_color = target_bg_color + (255,) if len(target_bg_color) == 3 else target_bg_color
            new_img = Image.new('RGBA', image.size, bg_color)
            new_img.paste(image, (0, 0), mask=alpha)
            return new_img
        elif force_transparent or (0.05 < transparent_ratio < 0.95):
            return image
        elif transparent_ratio <= 0.05:
            # 几乎没有透明，直接转为 RGB 白底
            rgb = image.convert('RGB')
            return rgb
        else:
            # 几乎全透明时，始终保留透明通道，不添加任何背景色
            return image

    @staticmethod
    def _apply_mask_shape(
            image: Image.Image,
            mask_shape: str = 'none',
            corner_radius: int = 20
    ) -> Image.Image:
        """
        应用现代图标遮罩形状（圆形、圆角矩形等）

        圆角实现逻辑：
        1. 创建与目标尺寸一致的灰度蒙版
        2. 绘制白色的圆角矩形区域（代表不透明）和黑色的四角区域（代表全透明）
        3. 将此蒙版作为 Alpha 通道赋予原图

        Args:
            image: RGBA Image 对象
            mask_shape: 遮罩形状 ('square', 'circle', 'rounded', 'none')
            corner_radius: 圆角半径（仅对 'rounded' 有效）

        Returns:
            应用遮罩后的 Image 对象
        """
        if mask_shape == 'none' or mask_shape == 'square':
            return image

        size = image.size
        width, height = size

        # 确保原图是 RGBA 模式
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # 创建精确的 alpha 蒙版（只使用 0 和 255，无抗锯齿）
        alpha_data = bytearray(width * height)

        if mask_shape == 'circle':
            # 圆形：计算每个像素是否在圆内
            cx, cy = width / 2, height / 2
            r = min(width, height) / 2 - 0.5
            for y in range(height):
                for x in range(width):
                    dx, dy = x - cx, y - cy
                    idx = y * width + x
                    if dx * dx + dy * dy <= r * r:
                        alpha_data[idx] = 255
                    else:
                        alpha_data[idx] = 0

        elif mask_shape == 'rounded':
            # 圆角矩形：计算每个像素是否在圆角矩形内
            r = min(corner_radius, width // 2, height // 2)
            for y in range(height):
                for x in range(width):
                    idx = y * width + x

                    # 检查四个角
                    inside = False
                    if x >= r and x < width - r:
                        # 顶部和底部边缘
                        inside = True
                    elif y >= r and y < height - r:
                        # 左侧和右侧边缘
                        inside = True
                    else:
                        # 检查四个角
                        in_top_left = (x < r and y < r and
                                       (x - r) * (x - r) + (y - r) * (y - r) <= r * r)
                        in_top_right = (x >= width - r and y < r and
                                        (x - (width - r - 1)) * (x - (width - r - 1)) + (y - r) * (y - r) <= r * r)
                        in_bottom_left = (x < r and y >= height - r and
                                          (x - r) * (x - r) + (y - (height - r - 1)) * (y - (height - r - 1)) <= r * r)
                        in_bottom_right = (x >= width - r and y >= height - r and
                                           (x - (width - r - 1)) * (x - (width - r - 1)) + (y - (height - r - 1)) * (
                                                       y - (height - r - 1)) <= r * r)

                        inside = in_top_left or in_top_right or in_bottom_left or in_bottom_right

                    alpha_data[idx] = 255 if inside else 0

        # 应用 alpha 通道
        alpha_channel = Image.frombytes('L', (width, height), bytes(alpha_data))
        image.putalpha(alpha_channel)

        return image

    def _get_smart_ico_sizes(
            self,
            size_list: List[int],
            max_upscale_ratio: float = 2.0
    ) -> List[int]:
        """
        智能过滤 ICO 尺寸列表，防止对过小的原图进行无意义的放大

        Args:
            size_list: 原始 ICO 尺寸列表
            max_upscale_ratio: 最大允许的放大比例（相对于原图尺寸）

        Returns:
            过滤后的 ICO 尺寸列表
        """
        original_width, original_height = self.image.size
        max_original = max(original_width, original_height)

        # 过滤掉大于原图 * 放大比例的尺寸，防止模糊放大
        filtered = [
            size for size in size_list
            if size <= max_original * max_upscale_ratio
        ]

        # 确保至少包含一个标准尺寸（如果有的话）
        standard_sizes = [16, 32, 48, 256]
        if not filtered and size_list:
            # 如果原图太小，强制保留最小可用尺寸
            filtered = [min(size_list)]

        return sorted(set(filtered))

    def _prepare_icon_image(
            self,
            target_size: int,
            preserve_transparency: bool = True,
            apply_sharpen: bool = True,
            mask_shape: str = 'none',
            target_bg_color: Optional[Tuple[int, int, int]] = None,
            corner_radius: int = 20
    ) -> Image.Image:
        """
        准备图标尺寸的图片（精确缩放到目标尺寸）

        Args:
            target_size: 目标尺寸（正方形）
            preserve_transparency: 是否保留透明通道
            apply_sharpen: 是否对小图应用锐化
            mask_shape: 遮罩形状 ('square', 'circle', 'rounded', 'none')
            target_bg_color: 目标背景色 RGB 元组（用于深色模式适配）
            corner_radius: 圆角半径（当 mask_shape 为 'rounded' 时生效）

        Returns:
            target_size x target_size 的 Image 对象
        """
        # 生成缓存键（用于批量处理优化）
        # 将 target_bg_color 稳定地纳入缓存键，确保不同背景策略独立缓存
        bg_color_key = str(target_bg_color) if target_bg_color is not None else 'none'
        cache_key = (target_size, 'sharp' if apply_sharpen else 'nosharp', mask_shape, bg_color_key, corner_radius)

        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key].copy()

        image = self.image.copy()
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        original_width, original_height = image.size

        # 计算缩放比例，保持宽高比
        ratio_w = target_size / original_width
        ratio_h = target_size / original_height
        # 使用较大的比例，确保图片完全填充画布（可能裁剪边缘）
        ratio = max(ratio_w, ratio_h)

        # 计算缩放后的尺寸
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)

        # 使用高质量缩放
        if new_width != original_width or new_height != original_height:
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 裁剪到目标尺寸（居中）
        if new_width > target_size or new_height > target_size:
            left = (new_width - target_size) // 2
            top = (new_height - target_size) // 2
            right = left + target_size
            bottom = top + target_size
            image = image.crop((left, top, right, bottom))

        # 小图智能锐化：32px 及以下应用分级锐化滤镜
        if apply_sharpen:
            image = self._sharpen_small_icon(image, target_size)

        # 应用现代图标遮罩（圆形、圆角矩形等）- 先于背景适配，确保圆角效果正确
        if mask_shape != 'none':
            image = self._apply_mask_shape(image, mask_shape, corner_radius)

        # 智能背景适配（支持深色模式）- 在圆角遮罩之后执行
        if preserve_transparency:
            image = self._smart_background_adapt(
                image,
                force_transparent=True,
                target_bg_color=target_bg_color
            )

        # 缓存结果
        self._icon_cache[cache_key] = image.copy()
        return image

    def generate_icon(
            self,
            output_path: Union[str, Path],
            size: int,
            output_format: str = 'PNG',
            preserve_transparency: bool = True,
            mask_shape: str = 'none',
            target_bg_color: Optional[Tuple[int, int, int]] = None,
            corner_radius: int = 20
    ) -> Path:
        """
        生成指定尺寸的高质量图标文件

        Args:
            output_path: 输出文件路径
            size: 目标尺寸（正方形）
            output_format: 输出格式 ('PNG' 或 'ICO')
            preserve_transparency: 是否保留透明通道
            mask_shape: 遮罩形状 ('square', 'circle', 'rounded', 'none')
            target_bg_color: 目标背景色 RGB 元组（用于深色模式适配）
            corner_radius: 圆角半径（当 mask_shape 为 'rounded' 时生效）

        Returns:
            生成的图标文件路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 生成图标（小图锐化 + 智能背景适配 + 遮罩支持）
        img = self._prepare_icon_image(
            size,
            preserve_transparency=preserve_transparency,
            apply_sharpen=True,
            mask_shape=mask_shape,
            target_bg_color=target_bg_color,
            corner_radius=corner_radius
        )

        if output_format.upper() == 'ICO':
            # ICO 保存异常降级：RGBA 失败时自动降级为 RGB
            try:
                img.save(
                    output_path,
                    format='ICO',
                    sizes=[(size, size)],
                    compress_level=0
                )
            except OSError:
                # 降级：将 RGBA 转换为 RGB 后重试
                rgb_img = img.convert('RGB') if img.mode == 'RGBA' else img
                rgb_img.save(
                    output_path,
                    format='ICO',
                    sizes=[(size, size)],
                    compress_level=0
                )
        else:
            img.save(output_path, format='PNG', optimize=True)

        return output_path

    def generate_multi_size_ico(
            self,
            output_path: Union[str, Path],
            sizes: List[int],
            preserve_transparency: bool = True,
            mask_shape: str = 'none',
            target_bg_color: Optional[Tuple[int, int, int]] = None,
            corner_radius: int = 20
    ) -> Path:
        """Generate one ICO containing all requested Windows-compatible sizes."""
        normalized_sizes = sorted({int(size) for size in sizes if 1 <= int(size) <= 256})
        if not normalized_sizes:
            raise ValueError("ICO 至少需要一个 1 到 256 px 的有效尺寸")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        largest_size = normalized_sizes[-1]
        image = self._prepare_icon_image(
            largest_size,
            preserve_transparency=preserve_transparency,
            apply_sharpen=True,
            mask_shape=mask_shape,
            target_bg_color=target_bg_color,
            corner_radius=corner_radius,
        )
        image.save(
            output_path,
            format='ICO',
            sizes=[(size, size) for size in normalized_sizes],
            compress_level=0,
        )
        image.close()
        return output_path

    def generate_app_icons(
            self,
            output_dir: Union[str, Path],
            preset: str = 'ios',
            include_android: bool = False,
            high_res: bool = False
    ) -> Dict[str, List[Path]]:
        """
        生成多平台应用图标集

        Args:
            output_dir: 输出目录
            preset: 主预设 ('ios', 'android', 'favicon')
            include_android: 是否同时生成 Android 图标
            high_res: 是否包含超高分辨率（512x512、1024x1024），默认 False 减小体积

        Returns:
            包含各平台图标路径的字典
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        # 根据 high_res 决定 ICO 尺寸
        ico_sizes = self.ICO_SIZES if high_res else self.DEFAULT_ICO_SIZES

        # iOS 图标
        if preset in ['ios', 'apple_touch']:
            ios_sizes = self.ICON_PRESETS['ios']
            if not high_res:
                # 默认不包含超大尺寸
                ios_sizes = [s for s in ios_sizes if s <= 512]
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
            if not high_res:
                android_sizes = [s for s in android_sizes if s <= 192]
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

            # 智能过滤 ICO 尺寸，防止对过小原图进行无意义放大
            smart_ico_sizes = self._get_smart_ico_sizes(ico_sizes)

            # 生成 PNG 和 ICO（使用高质量PNG嵌入模式 + compress_level=0 无损压缩）
            ico_images = []
            for s in smart_ico_sizes:
                img = self._prepare_icon_image(s, preserve_transparency=True, apply_sharpen=True)
                # ICO 格式支持嵌入 PNG 数据，保留透明度
                ico_images.append(img)

            if ico_images:
                ico_path = favicon_dir / 'favicon.ico'
                # ICO 保存异常降级：RGBA 失败时自动降级为 RGB
                try:
                    ico_images[0].save(
                        ico_path, format='ICO',
                        sizes=[(s, s) for s in smart_ico_sizes],
                        append_images=ico_images[1:],
                        compress_level=0
                    )
                except OSError:
                    # 降级：将 RGBA 转换为 RGB 后重试
                    rgb_images = [img.convert('RGB') if img.mode == 'RGBA' else img for img in ico_images]
                    ico_images[0].save(
                        ico_path, format='ICO',
                        sizes=[(s, s) for s in smart_ico_sizes],
                        append_images=rgb_images[1:],
                        compress_level=0
                    )
                favicon_paths.append(ico_path)
            results['favicon'] = favicon_paths

        return results

    def generate_favicon_package(
            self,
            output_dir: Union[str, Path],
            high_res: bool = False
    ) -> Dict[str, Path]:
        """
        生成完整的网站 favicon 包

        Args:
            output_dir: 输出目录
            high_res: 是否包含超高分辨率（512x512、1024x1024），默认 False 减小体积

        Returns:
            各文件路径的字典
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}
        # 基础尺寸
        base_sizes = [16, 32, 48, 64, 128, 180, 192, 256]
        if high_res:
            base_sizes.extend([512, 1024])

        for size in base_sizes:
            img = self._prepare_icon_image(size)
            out_path = output_dir / f"favicon-{size}x{size}.png"
            img.save(out_path, format='PNG', optimize=True)
            results[f'favicon_{size}'] = out_path

        # 生成 favicon.ico（使用更大的尺寸提高清晰度 + compress_level=0 无损）
        ico_sizes = self.ICO_SIZES if high_res else self.DEFAULT_ICO_SIZES
        # 智能过滤 ICO 尺寸，防止对过小原图进行无意义放大
        smart_ico_sizes = self._get_smart_ico_sizes(ico_sizes)

        ico_images = []
        for s in smart_ico_sizes:
            img = self._prepare_icon_image(s, preserve_transparency=True, apply_sharpen=True)
            # ICO 格式支持嵌入 PNG 数据，保留透明度
            ico_images.append(img)

        if ico_images:
            ico_path = output_dir / 'favicon.ico'
            # ICO 保存异常降级：RGBA 失败时自动降级为 RGB
            try:
                ico_images[0].save(
                    ico_path, format='ICO',
                    sizes=[(s, s) for s in smart_ico_sizes],
                    append_images=ico_images[1:],
                    compress_level=0
                )
            except OSError:
                # 降级：将 RGBA 转换为 RGB 后重试
                rgb_images = [img.convert('RGB') if img.mode == 'RGBA' else img for img in ico_images]
                ico_images[0].save(
                    ico_path, format='ICO',
                    sizes=[(s, s) for s in smart_ico_sizes],
                    append_images=rgb_images[1:],
                    compress_level=0
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

        if high_res:
            # 高分辨率 Android Chrome Icon
            img = self._prepare_icon_image(512)
            android_path = output_dir / 'android-chrome-512x512.png'
            img.save(android_path, format='PNG', optimize=True)
            results['android_chrome_512'] = android_path

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
