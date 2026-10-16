"""Composable image-conversion pipeline used by UI-independent code."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple, Union

from PIL import Image

from .text_annotations import TextBoxOptions, apply_text_boxes


PathLike = Union[str, Path]
CropRect = Tuple[float, float, float, float]


@dataclass(frozen=True)
class ResizeOptions:
    """Optional output-size constraints."""

    enabled: bool = False
    width: int = 1920
    height: int = 1080
    keep_aspect_ratio: bool = True

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("目标宽度和高度必须大于 0")


@dataclass(frozen=True)
class TransformOptions:
    """Rotation and mirroring applied after cropping."""

    angle: int = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False


@dataclass(frozen=True)
class CropOptions:
    """Crop rectangle expressed as ratios of the source image."""

    rect: Optional[CropRect] = None

    def __post_init__(self) -> None:
        if self.rect is None:
            return
        x1, y1, x2, y2 = self.rect
        if not all(0.0 <= value <= 1.0 for value in self.rect):
            raise ValueError("裁剪比例必须位于 0 到 1 之间")
        if x2 <= x1 or y2 <= y1:
            raise ValueError("裁剪区域必须具有有效的宽度和高度")


@dataclass(frozen=True)
class ConversionOptions:
    """All options required to convert one image."""

    output_format: str = "JPEG"
    quality: int = 85
    resize: ResizeOptions = field(default_factory=ResizeOptions)
    transform: TransformOptions = field(default_factory=TransformOptions)
    crop: CropOptions = field(default_factory=CropOptions)
    text_boxes: tuple[TextBoxOptions, ...] = ()

    def __post_init__(self) -> None:
        normalized_format = self.output_format.upper()
        if normalized_format not in ImageConversionService.EXTENSIONS:
            raise ValueError(f"不支持的格式: {self.output_format}")
        if not 1 <= self.quality <= 100:
            raise ValueError("图片质量必须位于 1 到 100 之间")
        object.__setattr__(self, "output_format", normalized_format)


class ImageConversionService:
    """Apply a deterministic conversion pipeline to Pillow images."""

    EXTENSIONS = {
        "JPEG": ".jpg",
        "PNG": ".png",
        "WEBP": ".webp",
        "BMP": ".bmp",
    }

    @classmethod
    def output_extension(cls, output_format: str) -> str:
        try:
            return cls.EXTENSIONS[output_format.upper()]
        except KeyError as exc:
            raise ValueError(f"不支持的格式: {output_format}") from exc

    @classmethod
    def convert_file(
        cls,
        source_path: PathLike,
        output_path: PathLike,
        options: ConversionOptions,
    ) -> Path:
        """Load, transform, and save one image without UI dependencies."""
        source = Path(source_path)
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(source) as source_image:
            source_image.load()
            image = cls.transform_image(source_image, options)
            try:
                cls._save(image, destination, options)
            finally:
                image.close()
        return destination

    @classmethod
    def transform_image(
        cls, image: Image.Image, options: ConversionOptions
    ) -> Image.Image:
        """Return a transformed copy, leaving the supplied image untouched."""
        result = image.copy()
        text_canvas, text_origin = cls._text_viewport(image.size, options)
        result = cls._crop(result, options.crop)
        result = cls._transform(result, options.transform)
        if options.transform.angle % 90:
            text_canvas, text_origin = result.size, (0, 0)
        result = apply_text_boxes(result, options.text_boxes, text_canvas, text_origin)
        result = cls._resize(result, options.resize)
        return cls._prepare_mode(result, options.output_format)

    @staticmethod
    def _text_viewport(size: tuple[int, int], options: ConversionOptions) -> tuple[tuple[int, int], tuple[int, int]]:
        """Locate a cropped image within the full, rotated preview canvas."""
        width, height = size
        x1, y1, x2, y2 = options.crop.rect or (0, 0, 1, 1)
        left, top, right, bottom = int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height)
        if options.transform.flip_horizontal:
            left, right = width - right, width - left
        if options.transform.flip_vertical:
            top, bottom = height - bottom, height - top
        angle = options.transform.angle % 360
        if angle == 90:
            return (height, width), (height - bottom, left)
        if angle == 180:
            return size, (width - right, height - bottom)
        if angle == 270:
            return (height, width), (top, width - right)
        return size, (left, top)

    @staticmethod
    def _crop(image: Image.Image, options: CropOptions) -> Image.Image:
        if options.rect is None:
            return image
        x1, y1, x2, y2 = options.rect
        box = (
            max(0, int(x1 * image.width)),
            max(0, int(y1 * image.height)),
            min(image.width, int(x2 * image.width)),
            min(image.height, int(y2 * image.height)),
        )
        cropped = image.crop(box)
        image.close()
        return cropped

    @staticmethod
    def _transform(image: Image.Image, options: TransformOptions) -> Image.Image:
        if options.flip_horizontal:
            transformed = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            image.close()
            image = transformed
        if options.flip_vertical:
            transformed = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            image.close()
            image = transformed
        if options.angle:
            quarter_turns = {
                90: Image.Transpose.ROTATE_270,
                180: Image.Transpose.ROTATE_180,
                270: Image.Transpose.ROTATE_90,
            }
            transpose = quarter_turns.get(options.angle % 360)
            if transpose is not None:
                transformed = image.transpose(transpose)
            else:
                transformed = image.rotate(
                    -options.angle,
                    expand=True,
                    resample=Image.Resampling.BICUBIC,
                )
            image.close()
            image = transformed
        return image

    @staticmethod
    def _resize(image: Image.Image, options: ResizeOptions) -> Image.Image:
        if not options.enabled:
            return image
        if options.keep_aspect_ratio:
            ratio = min(options.width / image.width, options.height / image.height)
            target_size = (
                max(1, round(image.width * ratio)),
                max(1, round(image.height * ratio)),
            )
        else:
            target_size = (options.width, options.height)
        resized = image.resize(target_size, Image.Resampling.LANCZOS)
        image.close()
        return resized

    @staticmethod
    def _prepare_mode(image: Image.Image, output_format: str) -> Image.Image:
        if output_format not in {"JPEG", "BMP"}:
            return image
        if image.mode in {"RGBA", "LA", "P"}:
            rgba_image = image.convert("RGBA")
            background = Image.new("RGB", image.size, "white")
            background.paste(rgba_image, mask=rgba_image.getchannel("A"))
            rgba_image.close()
            image.close()
            return background
        if image.mode != "RGB":
            converted = image.convert("RGB")
            image.close()
            return converted
        return image

    @staticmethod
    def _save(
        image: Image.Image, output_path: Path, options: ConversionOptions
    ) -> None:
        save_options = {}
        if options.output_format == "PNG":
            save_options["optimize"] = True
        elif options.output_format in {"JPEG", "WEBP"}:
            save_options["quality"] = options.quality
        image.save(output_path, format=options.output_format, **save_options)
