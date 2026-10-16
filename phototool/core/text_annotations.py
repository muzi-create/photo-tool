"""Text-box layout shared by the editor preview and image export."""

import base64
from dataclasses import dataclass
from functools import lru_cache
import io
import math
import os
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont


@dataclass(frozen=True)
class TextBoxOptions:
    """Position and dimensions are relative to the displayed image."""

    text: str
    x: float = 0.1
    y: float = 0.1
    width: float = 0.45
    font_size: float = 0.04
    color: str = "#ffffff"
    background: str = "#000000"
    opacity: int = 65
    bold: bool = False
    align: str = "left"
    height: float | None = None

    def __post_init__(self) -> None:
        if len(self.text) > 2000:
            raise ValueError("每个说明框最多支持 2000 个字符")
        if not all(math.isfinite(value) for value in (self.x, self.y, self.width, self.font_size)):
            raise ValueError("文字位置和尺寸必须是有效数字")
        if not 0 <= self.x <= 1 or not 0 <= self.y <= 1:
            raise ValueError("文字位置必须位于图片范围内")
        if not 0 < self.width <= 1 or not 0 < self.font_size <= 1:
            raise ValueError("文字宽度和字号必须大于 0 且不超过图片宽度")
        if self.height is not None and (not math.isfinite(self.height) or not 0 < self.height <= 1):
            raise ValueError("说明框高度必须大于 0 且不超过图片高度")
        if not 0 <= self.opacity <= 100 or self.align not in {"left", "center", "right"}:
            raise ValueError("文字背景透明度或对齐方式无效")
        ImageColor.getrgb(self.color)
        ImageColor.getrgb(self.background)


@lru_cache(maxsize=32)
def _font(size: int, bold: bool) -> ImageFont.FreeTypeFont:
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = [
        windows_fonts / ("msyhbd.ttc" if bold else "msyh.ttc"),
        windows_fonts / "simhei.ttf",
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


@lru_cache(maxsize=256)
def _ink_bounds(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int, int, int]:
    """Visible glyph bounds relative to the text baseline, without font side bearings."""
    mask_bounds = font.getmask(text).getbbox()
    if mask_bounds is None:
        return (0, 0, 0, 0)
    left, top, _, _ = font.getbbox(text, anchor="ls")
    return (left + mask_bounds[0], top + mask_bounds[1],
            left + mask_bounds[2], top + mask_bounds[3])


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Wrap CJK and Latin text, preserving explicit line breaks."""
    lines = []
    for paragraph in text.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4).split("\n"):
        line = ""
        for character in paragraph:
            candidate = line + character
            if line and font.getlength(candidate) > width:
                bounds = _ink_bounds(candidate, font)
                if bounds[2] - bounds[0] > width:
                    lines.append(line)
                    line = ""
            line += character
        lines.append(line)
    return lines


def _glyph_clips(character: str, font: ImageFont.FreeTypeFont) -> list[tuple[int, int, int, int]]:
    """Merge ink runs into clip rectangles; empty sprite pixels must not erase nearby glyphs."""
    mask = font.getmask(character)
    width, height = mask.size
    pixels = bytes(mask)
    clips = []
    active = {}
    for y in range(height):
        current = {}
        x = 0
        while x < width:
            if not pixels[y * width + x]:
                x += 1
                continue
            start = x
            while x < width and pixels[y * width + x]:
                x += 1
            key = (start, x - start)
            if key in active:
                index = active[key]
                left, top, run_width, run_height = clips[index]
                clips[index] = (left, top, run_width, run_height + 1)
            else:
                index = len(clips)
                clips.append((start, y, x - start, 1))
            current[key] = index
        active = current
    return clips


@lru_cache(maxsize=8)
def _preview_glyphs(text: str, size: int, bold: bool, color: str, background: str, opacity: int) -> dict:
    """Cache Pillow glyph pixels so live resizing never substitutes browser fonts."""
    font = _font(size, bold)
    text = text.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4)
    characters = list(dict.fromkeys(text.replace("\n", "")))
    bounds = {char: font.getbbox(char, anchor="ls") for char in characters}
    area = sum(max(1, box[2] - box[0] + 2) * max(1, box[3] - box[1] + 2) for box in bounds.values())
    # Bound atlas memory even for 2000 distinct characters at the maximum font size.
    atlas_scale = min(1.0, math.sqrt(4_000_000 / max(1, area)))
    background_color = (*ImageColor.getrgb(background)[:3], round(opacity * 255 / 100))
    glyphs = {}
    atlas_width = max(1, min(2048, math.ceil(math.sqrt(area) * atlas_scale)))
    x = y = row_height = 0
    for char, box in bounds.items():
        width, height = max(0, box[2] - box[0]), max(0, box[3] - box[1])
        sprite_width, sprite_height = max(1, round(width * atlas_scale)), max(1, round(height * atlas_scale))
        if x and x + sprite_width + 2 > atlas_width:
            x, y, row_height = 0, y + row_height, 0
        glyphs[char] = {
            "x": x + 1, "y": y + 1, "width": sprite_width, "height": sprite_height,
            "left": box[0], "top": box[1], "inkWidth": width, "inkHeight": height,
            "advance": font.getlength(char),
            "visibleBounds": _ink_bounds(char, font),
            "clips": _glyph_clips(char, font),
        }
        x += sprite_width + 2
        row_height = max(row_height, sprite_height + 2)
        atlas_width = max(atlas_width, x)
    with Image.new("RGBA", (atlas_width, max(1, y + row_height))) as atlas:
        for char, glyph in glyphs.items():
            if not glyph["inkWidth"] or not glyph["inkHeight"]:
                continue
            with Image.new("RGBA", (glyph["inkWidth"], glyph["inkHeight"]), background_color) as sprite:
                ImageDraw.Draw(sprite).text((-glyph["left"], -glyph["top"]), char,
                                           font=font, fill=ImageColor.getrgb(color), anchor="ls")
                if sprite.size == (glyph["width"], glyph["height"]):
                    atlas.paste(sprite, (glyph["x"], glyph["y"]))
                else:
                    with sprite.resize((glyph["width"], glyph["height"]), Image.Resampling.LANCZOS) as resized:
                        atlas.paste(resized, (glyph["x"], glyph["y"]))
        buffer = io.BytesIO()
        atlas.save(buffer, format="PNG")
    pairs = {text[index:index + 2] for index in range(len(text) - 1) if "\n" not in text[index:index + 2]}
    kerning = {pair: font.getlength(pair) - glyphs[pair[0]]["advance"] - glyphs[pair[1]]["advance"]
               for pair in pairs}
    return {"atlas": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii"),
            "glyphs": glyphs, "kerning": kerning}


def text_box_preview_layout(options: TextBoxOptions, canvas_size: tuple[int, int]) -> dict:
    """Font metrics and Pillow glyphs for the browser's temporary resize preview."""
    font = _font(max(1, round(canvas_size[0] * options.font_size)), options.bold)
    return {
        "canvasWidth": canvas_size[0], "canvasHeight": canvas_size[1],
        "fontFamily": font.getname()[0], "fontSize": font.size,
        "padding": max(1, round(font.size * 0.35)),
        "lineHeight": max(1, math.ceil(sum(font.getmetrics()) * 1.15)),
        "bold": options.bold, "color": options.color,
        "background": options.background, "opacity": options.opacity,
        "align": options.align,
        "lineBounds": {line: _ink_bounds(line, font) for line in
                       _wrap_text(options.text, font, max(1, round(canvas_size[0] * options.width)
                                  - 2 * max(1, round(font.size * 0.35))))},
        **_preview_glyphs(options.text, font.size, options.bold, options.color, options.background, options.opacity),
    }


def render_text_box(options: TextBoxOptions, canvas_size: tuple[int, int]) -> Image.Image:
    """Render one transparent tile at the source resolution, including its background."""
    width = max(1, round(canvas_size[0] * options.width))
    font = _font(max(1, round(canvas_size[0] * options.font_size)), options.bold)
    padding = min(max(1, round(font.size * 0.35)), max(0, (width - 1) // 2))
    lines = _wrap_text(options.text, font, max(1, width - 2 * padding))
    bounds = [_ink_bounds(line, font) for line in lines]
    ascent, descent = font.getmetrics()
    line_height = max(1, math.ceil((ascent + descent) * 1.15))
    last_bounds = next((box for box in reversed(bounds) if box[3] > box[1]), (0, 0, 0, 0))
    text_height = (len(lines) - 1) * line_height + last_bounds[3] - last_bounds[1]
    if options.height is None:
        text_width = max((box[2] - box[0] for box in bounds), default=0)
        width = max(1, min(width, text_width + 2 * padding))
    height = max(1, min(canvas_size[1], round(canvas_size[1] * options.height)
                        if options.height is not None else text_height + 2 * padding))
    tile = Image.new("RGBA", (width, height))
    if not options.text.strip():
        return tile
    draw = ImageDraw.Draw(tile)
    background = (*ImageColor.getrgb(options.background)[:3], round(options.opacity * 255 / 100))
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=padding, fill=background)
    color = ImageColor.getrgb(options.color)
    for index, (line, box) in enumerate(zip(lines, bounds)):
        top = padding + index * line_height
        if top >= height:
            break
        line_width = box[2] - box[0]
        left = padding
        if options.align == "center":
            left = (width - line_width) // 2
        elif options.align == "right":
            left = width - padding - line_width
        draw.text((left - box[0], top - box[1]), line, font=font, fill=color, anchor="ls")
    return tile


def text_box_position(options: TextBoxOptions, canvas_size: tuple[int, int], tile_size: tuple[int, int]) -> tuple[int, int]:
    """Keep the complete box on the image, including after changing its text."""
    return (
        max(0, min(canvas_size[0] - tile_size[0], round(options.x * canvas_size[0]))),
        max(0, min(canvas_size[1] - tile_size[1], round(options.y * canvas_size[1]))),
    )


def apply_text_boxes(
    image: Image.Image,
    boxes: tuple[TextBoxOptions, ...],
    canvas_size: tuple[int, int] | None = None,
    origin: tuple[int, int] = (0, 0),
) -> Image.Image:
    """Composite in display order; origin accounts for a pending crop."""
    if not boxes:
        return image
    canvas_size = canvas_size or image.size
    result = image.convert("RGBA")
    image.close()
    for box in boxes:
        if not box.text.strip():
            continue
        with render_text_box(box, canvas_size) as tile:
            left, top = text_box_position(box, canvas_size, tile.size)
            result.alpha_composite(tile, (left - origin[0], top - origin[1]))
    return result
