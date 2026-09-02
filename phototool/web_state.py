"""Reflex state and browser-facing adapters for PhotoTool."""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import reflex as rx
from PIL import Image

from phototool.core import (
    ConversionOptions,
    CropOptions,
    ImageConverter,
    ImageConversionService,
    ResizeOptions,
    TransformOptions,
)


ICON_PRESETS = {
    "Windows 系统图标": ImageConverter.ICON_PRESETS["windows"],
    "iOS 应用图标": ImageConverter.ICON_PRESETS["ios"],
    "Android 应用图标": ImageConverter.ICON_PRESETS["android"],
    "网站 Favicon": ImageConverter.ICON_PRESETS["favicon"],
    "Apple Touch Icon": ImageConverter.ICON_PRESETS["apple_touch"],
    "Windows 10/11 磁贴": ImageConverter.ICON_PRESETS["microsoft"],
    "完整多平台图标包": sorted(
        set(ImageConverter.ICON_PRESETS["ios"] + ImageConverter.ICON_PRESETS["android"])
    ),
}


def _data_url(data: bytes, mime: str = "image/png") -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _image_to_png(image: Image.Image, maximum: int = 1400) -> bytes:
    preview = image.copy()
    preview.thumbnail((maximum, maximum), Image.Resampling.LANCZOS)
    if preview.mode not in {"RGB", "RGBA"}:
        preview = preview.convert("RGBA")
    buffer = io.BytesIO()
    preview.save(buffer, format="PNG", optimize=True)
    preview.close()
    return buffer.getvalue()


class PhotoToolState(rx.State):
    """Session state for the Reflex UI."""

    active_mode: str = "convert"
    file_name: str = "未选择图片"
    file_count: int = 0
    file_meta: str = "支持 PNG、JPEG、WEBP、BMP、GIF"
    preview_url: str = ""
    image_width: int = 0
    image_height: int = 0

    output_format: str = "JPEG"
    quality: int = 85
    resize_enabled: bool = False
    resize_width: int = 1920
    resize_height: int = 1080
    keep_ratio: bool = True
    rotation: int = 0
    flip_h: bool = False
    flip_v: bool = False

    crop_enabled: bool = False
    crop_mode: str = "自由选区"
    crop_ratio: str = "1:1"
    crop_x: float = 0.0
    crop_y: float = 0.0
    crop_w: float = 100.0
    crop_h: float = 100.0
    crop_pixel_x: int = 0
    crop_pixel_y: int = 0
    crop_pixel_w: int = 1920
    crop_pixel_h: int = 1080
    crop_history_count: int = 0

    icon_file_name: str = "未选择图片"
    icon_meta: str = "选择一张高清正方形图片以获得最佳效果"
    icon_preview_url: str = ""
    icon_preset: str = "Windows 系统图标"
    icon_format: str = "ICO (多尺寸)"
    icon_size: int = 256
    corner_enabled: bool = False
    corner_shape: str = "圆角矩形"
    corner_radius: int = 20
    corner_preview_url: str = ""

    status: str = "就绪"
    progress: int = 0
    processing: bool = False

    _files: list[tuple[str, bytes]] = rx.field(default_factory=list)
    _original_files: list[tuple[str, bytes]] = rx.field(default_factory=list)
    _crop_history: list[list[tuple[str, bytes]]] = rx.field(default_factory=list)
    _icon_file: tuple[str, bytes] | None = None

    @rx.var
    def has_files(self) -> bool:
        return self.file_count > 0

    @rx.var
    def has_icon_file(self) -> bool:
        return bool(self.icon_preview_url)

    @rx.var
    def transform_status(self) -> str:
        parts: list[str] = []
        if self.rotation:
            parts.append(f"旋转 {self.rotation}°")
        if self.flip_h:
            parts.append("水平翻转")
        if self.flip_v:
            parts.append("垂直翻转")
        return " · ".join(parts) or "无变换"

    @rx.var
    def crop_selection_style(self) -> dict[str, str]:
        return {
            "left": f"{self.crop_x}%",
            "top": f"{self.crop_y}%",
            "width": f"{self.crop_w}%",
            "height": f"{self.crop_h}%",
        }

    @rx.var
    def crop_summary(self) -> str:
        return (
            f"X {self.crop_pixel_x} · Y {self.crop_pixel_y} · "
            f"{self.crop_pixel_w} × {self.crop_pixel_h} px"
        )

    @rx.var
    def icon_sizes(self) -> list[str]:
        if self.icon_preset == "自定义尺寸":
            sizes = [self.icon_size]
        else:
            sizes = ICON_PRESETS.get(self.icon_preset, [256])
        return [f"{size} × {size}" for size in sizes]

    def switch_mode(self, mode: str):
        self.active_mode = mode
        self.status = "就绪"

    async def handle_upload(self, files: list[rx.UploadFile]):
        payloads: list[tuple[str, bytes]] = []
        try:
            for upload in files:
                data = await upload.read()
                with Image.open(io.BytesIO(data)) as image:
                    image.verify()
                payloads.append((upload.filename or "image", data))
        except Exception as exc:
            return rx.toast.error(f"图片读取失败：{exc}")
        if not payloads:
            return rx.toast.warning("请选择至少一张图片")
        self._files = payloads
        self._original_files = list(payloads)
        self._crop_history = []
        self.file_count = len(payloads)
        self.file_name = payloads[0][0]
        self._update_file_meta()
        self._reset_editor()
        self._load_primary_preview()
        self.status = f"已载入 {len(payloads)} 个文件"
        return rx.toast.success("图片已载入")

    def clear_files(self):
        self._files = []
        self._original_files = []
        self._crop_history = []
        self.file_name = "未选择图片"
        self.file_count = 0
        self.file_meta = "支持 PNG、JPEG、WEBP、BMP、GIF"
        self.preview_url = ""
        self.image_width = 0
        self.image_height = 0
        self._reset_editor()
        self.status = "已清除图片"
        return rx.clear_selected_files("convert_upload")

    def _reset_editor(self):
        self.rotation = 0
        self.flip_h = False
        self.flip_v = False
        self.crop_enabled = False
        self.crop_x = 0.0
        self.crop_y = 0.0
        self.crop_w = 100.0
        self.crop_h = 100.0
        self.crop_history_count = 0

    def _load_primary_preview(self):
        if not self._files:
            return
        with Image.open(io.BytesIO(self._files[0][1])) as image:
            image.load()
            self.image_width, self.image_height = image.size
            rendered = image.copy()
        if self.flip_h:
            rendered = rendered.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if self.flip_v:
            rendered = rendered.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        if self.rotation:
            rotated = rendered.rotate(-self.rotation, expand=True, resample=Image.Resampling.BICUBIC)
            rendered.close()
            rendered = rotated
        self.preview_url = _data_url(_image_to_png(rendered))
        rendered.close()
        self._sync_crop_pixels()

    def _update_file_meta(self):
        self.file_count = len(self._files)
        self.file_meta = f"{self.file_count} 个文件 · {_format_size(sum(len(item[1]) for item in self._files))}"

    def rotate_left(self):
        if self._files:
            self.rotation = (self.rotation - 90) % 360
            self._load_primary_preview()

    def rotate_right(self):
        if self._files:
            self.rotation = (self.rotation + 90) % 360
            self._load_primary_preview()

    def toggle_flip_h(self):
        if self._files:
            self.flip_h = not self.flip_h
            self._load_primary_preview()

    def toggle_flip_v(self):
        if self._files:
            self.flip_v = not self.flip_v
            self._load_primary_preview()

    def reset_transform(self):
        self.rotation = 0
        self.flip_h = False
        self.flip_v = False
        self._load_primary_preview()

    def set_output_format(self, value: str):
        self.output_format = value

    def set_resize_enabled(self, value: bool):
        self.resize_enabled = value

    def set_keep_ratio(self, value: bool):
        self.keep_ratio = value

    def change_quality(self, value: float):
        self.quality = int(float(value))

    def change_resize_width(self, value: str):
        width = max(1, min(10000, int(value or 1)))
        self.resize_width = width
        if self.keep_ratio and self.image_width:
            self.resize_height = max(1, round(width * self.image_height / self.image_width))

    def change_resize_height(self, value: str):
        height = max(1, min(10000, int(value or 1)))
        self.resize_height = height
        if self.keep_ratio and self.image_height:
            self.resize_width = max(1, round(height * self.image_width / self.image_height))

    def toggle_crop(self, enabled: bool):
        self.crop_enabled = enabled
        if enabled and self.crop_w <= 0:
            self.reset_crop_selection()

    def set_crop_mode(self, mode: str):
        self.crop_mode = mode
        if mode == "锁定比例":
            self.set_crop_ratio(self.crop_ratio)
        elif mode == "预设尺寸":
            self.apply_crop_preset("头像 500×500")

    def set_crop_ratio(self, ratio: str):
        self.crop_ratio = ratio
        ratios = {"1:1": 1.0, "4:3": 4 / 3, "16:9": 16 / 9, "3:2": 3 / 2, "2:3": 2 / 3, "9:16": 9 / 16}
        target = ratios.get(ratio)
        if target is None or not self.image_width or not self.image_height:
            return
        display_ratio = target * self.image_height / self.image_width
        width = 80.0
        height = width / display_ratio
        if height > 80:
            height = 80.0
            width = height * display_ratio
        self.crop_w, self.crop_h = width, height
        self.crop_x, self.crop_y = (100 - width) / 2, (100 - height) / 2
        self._sync_crop_pixels()

    def apply_crop_preset(self, preset: str):
        presets = {
            "头像 200×200": (200, 200), "头像 500×500": (500, 500),
            "证件照 25×35": (25, 35), "壁纸 1920×1080": (1920, 1080),
            "壁纸 2560×1440": (2560, 1440), "微信封面 900×383": (900, 383),
            "小红书 1:1": (1080, 1080), "小红书 3:4": (1080, 1440),
        }
        width, height = presets[preset]
        self.crop_pixel_w = min(width, self.image_width or width)
        self.crop_pixel_h = min(height, self.image_height or height)
        self.crop_pixel_x = max(0, (self.image_width - self.crop_pixel_w) // 2)
        self.crop_pixel_y = max(0, (self.image_height - self.crop_pixel_h) // 2)
        self._sync_crop_percentages()

    def set_crop_x(self, value: float):
        self.crop_x = max(0.0, min(100.0 - self.crop_w, float(value)))
        self._sync_crop_pixels()

    def set_crop_y(self, value: float):
        self.crop_y = max(0.0, min(100.0 - self.crop_h, float(value)))
        self._sync_crop_pixels()

    def set_crop_w(self, value: float):
        self.crop_w = max(1.0, min(100.0 - self.crop_x, float(value)))
        self._sync_crop_pixels()

    def set_crop_h(self, value: float):
        self.crop_h = max(1.0, min(100.0 - self.crop_y, float(value)))
        self._sync_crop_pixels()

    def set_crop_pixel_x(self, value: str):
        self.crop_pixel_x = max(0, min(self.image_width - 1, int(value or 0)))
        self._sync_crop_percentages()

    def set_crop_pixel_y(self, value: str):
        self.crop_pixel_y = max(0, min(self.image_height - 1, int(value or 0)))
        self._sync_crop_percentages()

    def set_crop_pixel_w(self, value: str):
        self.crop_pixel_w = max(1, min(self.image_width - self.crop_pixel_x, int(value or 1)))
        self._sync_crop_percentages()

    def set_crop_pixel_h(self, value: str):
        self.crop_pixel_h = max(1, min(self.image_height - self.crop_pixel_y, int(value or 1)))
        self._sync_crop_percentages()

    def _sync_crop_pixels(self):
        if not self.image_width or not self.image_height:
            return
        self.crop_pixel_x = round(self.crop_x * self.image_width / 100)
        self.crop_pixel_y = round(self.crop_y * self.image_height / 100)
        self.crop_pixel_w = max(1, round(self.crop_w * self.image_width / 100))
        self.crop_pixel_h = max(1, round(self.crop_h * self.image_height / 100))

    def _sync_crop_percentages(self):
        if not self.image_width or not self.image_height:
            return
        self.crop_pixel_w = min(self.crop_pixel_w, self.image_width - self.crop_pixel_x)
        self.crop_pixel_h = min(self.crop_pixel_h, self.image_height - self.crop_pixel_y)
        self.crop_x = self.crop_pixel_x * 100 / self.image_width
        self.crop_y = self.crop_pixel_y * 100 / self.image_height
        self.crop_w = self.crop_pixel_w * 100 / self.image_width
        self.crop_h = self.crop_pixel_h * 100 / self.image_height

    def apply_crop(self):
        if not self._files or not self.crop_enabled:
            return rx.toast.warning("请先启用并设置裁剪区域")
        self._crop_history.append(list(self._files))
        cropped_files: list[tuple[str, bytes]] = []
        for name, data in self._files:
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                left = round(self.crop_x * image.width / 100)
                top = round(self.crop_y * image.height / 100)
                right = round((self.crop_x + self.crop_w) * image.width / 100)
                bottom = round((self.crop_y + self.crop_h) * image.height / 100)
                cropped = image.crop((left, top, right, bottom))
                buffer = io.BytesIO()
                cropped.save(buffer, format="PNG")
                cropped.close()
            cropped_files.append((name, buffer.getvalue()))
        self._files = cropped_files
        self._update_file_meta()
        self.crop_history_count = len(self._crop_history)
        self.crop_x = self.crop_y = 0.0
        self.crop_w = self.crop_h = 100.0
        self._load_primary_preview()
        self.status = "裁剪选区已应用"
        return rx.toast.success("裁剪已应用")

    def undo_crop(self):
        if not self._crop_history or not self._files:
            return
        self._files = self._crop_history.pop()
        self._update_file_meta()
        self.crop_history_count = len(self._crop_history)
        self.reset_crop_selection()
        self._load_primary_preview()
        self.status = "已撤销上一步裁剪"

    def reset_crop(self):
        if self._files and self._original_files:
            self._files = list(self._original_files)
            self._update_file_meta()
            self._crop_history = []
            self.crop_history_count = 0
            self.reset_crop_selection()
            self._load_primary_preview()
            self.status = "已恢复原始图片"

    def reset_crop_selection(self):
        self.crop_x = self.crop_y = 0.0
        self.crop_w = self.crop_h = 100.0
        self._sync_crop_pixels()

    def _conversion_options(self) -> ConversionOptions:
        crop = None
        if self.crop_enabled and (self.crop_w < 99.999 or self.crop_h < 99.999):
            crop = (
                self.crop_x / 100,
                self.crop_y / 100,
                (self.crop_x + self.crop_w) / 100,
                (self.crop_y + self.crop_h) / 100,
            )
        return ConversionOptions(
            output_format=self.output_format,
            quality=self.quality,
            resize=ResizeOptions(self.resize_enabled, self.resize_width, self.resize_height, self.keep_ratio),
            transform=TransformOptions(self.rotation, self.flip_h, self.flip_v),
            crop=CropOptions(crop),
        )

    def convert_images(self):
        if not self._files:
            return rx.toast.warning("请先添加图片")
        self.processing = True
        self.progress = 8
        self.status = "正在转换图片…"
        try:
            options = self._conversion_options()
            results: list[tuple[str, bytes]] = []
            extension = ImageConversionService.output_extension(options.output_format)
            for index, (name, data) in enumerate(self._files):
                with Image.open(io.BytesIO(data)) as source:
                    source.load()
                    converted = ImageConversionService.transform_image(source, options)
                output = io.BytesIO()
                save_args = {"format": options.output_format}
                if options.output_format == "PNG":
                    save_args["optimize"] = True
                elif options.output_format in {"JPEG", "WEBP"}:
                    save_args["quality"] = options.quality
                converted.save(output, **save_args)
                converted.close()
                results.append((f"{Path(name).stem}{extension}", output.getvalue()))
                self.progress = round((index + 1) / len(self._files) * 90)
            self.progress = 100
            self.status = f"转换完成 · {len(results)} 个文件"
            if len(results) == 1:
                return rx.download(data=results[0][1], filename=results[0][0])
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for name, data in results:
                    bundle.writestr(name, data)
            return rx.download(data=archive.getvalue(), filename="PhotoTool_转换结果.zip")
        except Exception as exc:
            self.status = f"转换失败：{exc}"
            return rx.toast.error(self.status)
        finally:
            self.processing = False

    async def handle_icon_upload(self, files: list[rx.UploadFile]):
        if not files:
            return
        upload = files[0]
        try:
            data = await upload.read()
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            self._icon_file = (upload.filename or "icon.png", data)
            self.icon_file_name = upload.filename or "icon.png"
            self.icon_meta = _format_size(len(data))
            self.icon_preview_url = _data_url(data, upload.content_type or "image/png")
            self._refresh_corner_preview()
            return rx.toast.success("图标源图已载入")
        except Exception as exc:
            return rx.toast.error(f"图片读取失败：{exc}")

    def clear_icon(self):
        self._icon_file = None
        self.icon_file_name = "未选择图片"
        self.icon_meta = "选择一张高清正方形图片以获得最佳效果"
        self.icon_preview_url = ""
        self.corner_preview_url = ""
        return rx.clear_selected_files("icon_upload")

    def set_icon_preset(self, value: str):
        self.icon_preset = value
        self._refresh_corner_preview()

    def set_icon_format(self, value: str):
        self.icon_format = value

    def set_icon_size(self, value: str):
        self.icon_size = max(16, min(1024, int(value or 16)))
        self._refresh_corner_preview()

    def set_corner_enabled(self, value: bool):
        self.corner_enabled = value
        self._refresh_corner_preview()

    def set_corner_shape(self, value: str):
        self.corner_shape = value
        self._refresh_corner_preview()

    def set_corner_radius(self, value: str):
        self.corner_radius = max(1, min(200, int(value or 1)))
        self._refresh_corner_preview()

    def _target_icon_size(self) -> int:
        if self.icon_preset == "自定义尺寸":
            return self.icon_size
        representative = {
            "Windows 系统图标": 256, "iOS 应用图标": 180,
            "Android 应用图标": 192, "网站 Favicon": 32,
            "Apple Touch Icon": 180, "Windows 10/11 磁贴": 150,
            "完整多平台图标包": 512,
        }
        return representative.get(self.icon_preset, 256)

    def _target_icon_sizes(self) -> list[int]:
        if self.icon_preset == "自定义尺寸":
            return [self.icon_size]
        return ICON_PRESETS.get(self.icon_preset, [self._target_icon_size()])

    def _refresh_corner_preview(self):
        if not self._icon_file:
            return
        with Image.open(io.BytesIO(self._icon_file[1])) as source:
            source = source.convert("RGBA")
            side = min(source.size)
            left = (source.width - side) // 2
            top = (source.height - side) // 2
            preview = source.crop((left, top, left + side, top + side)).resize((160, 160), Image.Resampling.LANCZOS)
        if self.corner_enabled:
            shape = "rounded" if self.corner_shape == "圆角矩形" else "circle"
            radius = round(self.corner_radius * 160 / self._target_icon_size())
            preview = ImageConverter._apply_mask_shape(preview, shape, radius)
        self.corner_preview_url = _data_url(_image_to_png(preview, 160))
        preview.close()

    def generate_icon(self):
        if not self._icon_file:
            return rx.toast.warning("请先选择图标源图")
        self.processing = True
        self.progress = 10
        self.status = "正在生成图标…"
        size = self._target_icon_size()
        mask = "none"
        if self.corner_enabled:
            mask = "rounded" if self.corner_shape == "圆角矩形" else "circle"
        try:
            with TemporaryDirectory(prefix="phototool_") as folder:
                source_path = Path(folder) / self._icon_file[0]
                source_path.write_bytes(self._icon_file[1])
                with ImageConverter(source_path) as converter:
                    outputs: list[tuple[str, bytes]] = []
                    formats = ["ICO", "PNG"] if self.icon_format == "ICO + PNG" else ["ICO" if self.icon_format.startswith("ICO") else "PNG"]
                    for output_format in formats:
                        extension = ".ico" if output_format == "ICO" else ".png"
                        name = f"icon_{size}x{size}{extension}"
                        destination = Path(folder) / name
                        if output_format == "ICO" and self.icon_format.startswith("ICO"):
                            result = converter.generate_multi_size_ico(
                                destination,
                                sizes=self._target_icon_sizes(),
                                mask_shape=mask,
                                corner_radius=self.corner_radius,
                            )
                        else:
                            result = converter.generate_icon(
                                destination, size=size, output_format=output_format,
                                mask_shape=mask, corner_radius=self.corner_radius,
                            )
                        outputs.append((name, Path(result).read_bytes()))
                self.progress = 100
                self.status = "图标生成完成"
                if len(outputs) == 1:
                    return rx.download(data=outputs[0][1], filename=outputs[0][0])
                archive = io.BytesIO()
                with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                    for name, data in outputs:
                        bundle.writestr(name, data)
                return rx.download(data=archive.getvalue(), filename=f"icon_{size}x{size}.zip")
        except Exception as exc:
            self.status = f"图标生成失败：{exc}"
            return rx.toast.error(self.status)
        finally:
            self.processing = False
