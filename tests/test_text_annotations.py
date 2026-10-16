import base64
from dataclasses import replace
import io
import json
import unittest

from PIL import Image, ImageChops

from phototool.core import (
    ConversionOptions, CropOptions, ImageConversionService, ResizeOptions,
    TextBoxOptions, TransformOptions,
)
from phototool.core.text_annotations import render_text_box, text_box_preview_layout
from phototool.web_state import PhotoToolState


class TextRenderingTests(unittest.TestCase):
    def test_resize_glyph_pixels_match_the_regular_preview(self):
        for bold in (False, True):
            for size in (16, 40, 73):
                for opacity in (0, 65, 100):
                    for text in ("\u4e2d", "A", "g", "\u00c9"):
                        with self.subTest(bold=bold, size=size, opacity=opacity, text=text):
                            options = TextBoxOptions(text=text, font_size=size / 800, opacity=opacity, bold=bold)
                            layout = text_box_preview_layout(options, (800, 600))
                            glyph = layout["glyphs"][text]
                            atlas_bytes = base64.b64decode(layout["atlas"].split(",", 1)[1])
                            with Image.open(io.BytesIO(atlas_bytes)) as atlas:
                                with atlas.crop((glyph["x"], glyph["y"], glyph["x"] + glyph["width"],
                                                 glyph["y"] + glyph["height"])) as actual:
                                    with render_text_box(options, (800, 600)) as tile:
                                        bounds = layout["lineBounds"][text]
                                        left = layout["padding"] + glyph["left"] - bounds[0]
                                        top = layout["padding"] + glyph["top"] - bounds[1]
                                        with tile.crop((left, top, left + glyph["inkWidth"],
                                                        top + glyph["inkHeight"])) as expected:
                                            self.assertEqual(actual.size, expected.size)
                                            self.assertIsNone(ImageChops.difference(actual, expected).getbbox(alpha_only=False))

    def test_automatic_height_has_equal_top_and_bottom_padding(self):
        for text, width in (("中文说明", 1), ("Agjpy", 1), ("第一行\n第二行", 1),
                            ("自动换行的中文说明Agjpy", 0.25)):
            for font_size in (0.02, 0.04, 0.07):
                for bold in (False, True):
                    with self.subTest(text=text, font_size=font_size, bold=bold):
                        options = TextBoxOptions(text=text, width=width, font_size=font_size,
                                                 bold=bold, opacity=0)
                        with render_text_box(options, (800, 1000)) as tile:
                            bounds = tile.getbbox()
                            self.assertIsNotNone(bounds)
                            self.assertEqual(bounds[1], tile.height - bounds[3])

    def test_automatic_size_has_equal_padding_on_all_four_sides(self):
        for text, width in (("\u4e2d\u6587\u8bf4\u660e", 0.45), ("Agjpy", 1),
                            ("\u7b2c\u4e00\u884c\n\u77ed", 1), ("\u81ea\u52a8\u6362\u884c\u7684\u4e2d\u6587\u8bf4\u660eAgjpy", 0.25)):
            for bold in (False, True):
                for align in ("left", "center", "right"):
                    with self.subTest(text=text, bold=bold, align=align):
                        options = TextBoxOptions(text=text, width=width, bold=bold, align=align, opacity=0)
                        with render_text_box(options, (800, 1000)) as tile:
                            left, top, right, bottom = tile.getbbox()
                            self.assertEqual((left, tile.width - right, tile.height - bottom), (top, top, top))
                            self.assertLessEqual(tile.width, round(800 * width))

    def test_automatic_height_preserves_explicit_blank_lines(self):
        options = TextBoxOptions(text="中文说明Agjpy", width=1, opacity=0)
        with render_text_box(options, (800, 600)) as single:
            with render_text_box(replace(options, text=f"{options.text}\n{options.text}"), (800, 600)) as double:
                line_spacing = double.height - single.height
                for text, leading in ((f"\n{options.text}", True), (f"{options.text}\n", False)):
                    with self.subTest(text=text), render_text_box(replace(options, text=text), (800, 600)) as tile:
                        self.assertEqual(tile.height, double.height)
                        expected_top = single.getbbox()[1] + (line_spacing if leading else 0)
                        self.assertEqual(tile.getbbox()[1], expected_top)
                        expected_bottom = single.height - single.getbbox()[3] + (0 if leading else line_spacing)
                        self.assertEqual(tile.height - tile.getbbox()[3], expected_bottom)

    def test_multiline_and_chinese_automatically_wrap(self):
        options = TextBoxOptions(text="中文说明框ABC", width=0.25, font_size=0.04)
        with render_text_box(options, (600, 800)) as wrapped, render_text_box(replace(options, width=1), (600, 800)) as single:
            self.assertGreater(wrapped.height, single.height)
            self.assertIsNotNone(wrapped.getbbox())
        with render_text_box(replace(options, text="第一行\n第二行", width=1), (600, 800)) as multiline:
            self.assertGreater(multiline.height, single.height)

    def test_transparent_background_and_blank_text(self):
        with render_text_box(TextBoxOptions(text="说明", opacity=0), (400, 300)) as tile:
            self.assertEqual(tile.getpixel((0, 0))[3], 0)
            self.assertGreater(tile.getchannel("A").getextrema()[1], 0)
        with render_text_box(TextBoxOptions(text=" \n "), (400, 300)) as tile:
            self.assertIsNone(tile.getbbox())

    def test_multiple_layers_preserve_source_and_export_modes(self):
        with Image.new("RGBA", (400, 300)) as source:
            boxes = (
                TextBoxOptions(text="底层", background="#ff0000", opacity=100),
                TextBoxOptions(text="顶层", background="#0000ff", opacity=100),
            )
            for output_format in ("PNG", "WEBP", "JPEG", "BMP"):
                with self.subTest(output_format=output_format):
                    options = ConversionOptions(output_format=output_format, text_boxes=boxes)
                    with ImageConversionService.transform_image(source, options) as result:
                        self.assertEqual(result.getpixel((45, 35))[:3], (0, 0, 255))
                        self.assertEqual(result.mode, "RGB" if output_format in {"JPEG", "BMP"} else "RGBA")
                        self.assertEqual(result.getpixel((0, 0))[:3], (255, 255, 255) if output_format in {"JPEG", "BMP"} else (0, 0, 0))
            self.assertIsNone(source.getbbox())

    def test_crop_and_transform_clip_the_same_text_as_preview(self):
        box = TextBoxOptions(text="中文说明\nTest", x=0.25, y=0.2, font_size=0.07)
        crop = CropOptions((0.15, 0.1, 0.85, 0.8))
        with Image.new("RGBA", (400, 300), (30, 60, 90, 255)) as source:
            for angle in (0, 90, 180, 270):
                for flip_h in (False, True):
                    for flip_v in (False, True):
                        with self.subTest(angle=angle, flip_h=flip_h, flip_v=flip_v):
                            transform = TransformOptions(angle, flip_h, flip_v)
                            options = ConversionOptions(output_format="PNG", transform=transform, text_boxes=(box,))
                            full = ImageConversionService.transform_image(source, options)
                            cropped_options = replace(options, crop=crop)
                            canvas_size, origin = ImageConversionService._text_viewport(source.size, cropped_options)
                            result = ImageConversionService.transform_image(source, cropped_options)
                            expected = full.crop((*origin, origin[0] + result.width, origin[1] + result.height))
                            try:
                                self.assertEqual(canvas_size, full.size)
                                self.assertIsNone(ImageChops.difference(result, expected).getbbox(alpha_only=False))
                            finally:
                                full.close()
                                result.close()
                                expected.close()

    def test_text_scales_with_image_resize(self):
        with Image.new("RGBA", (400, 300)) as source:
            options = ConversionOptions(output_format="PNG", text_boxes=(TextBoxOptions(text="说明"),))
            with ImageConversionService.transform_image(source, options) as full:
                with full.resize((200, 150), Image.Resampling.LANCZOS) as expected:
                    with ImageConversionService.transform_image(source, replace(options, resize=ResizeOptions(True, 200, 150))) as result:
                        self.assertIsNone(ImageChops.difference(expected, result).getbbox(alpha_only=False))

    def test_fixed_height_preserves_wrapping_and_clips_overflow(self):
        options = TextBoxOptions(text="第一行\n第二行\n第三行", height=0.15, opacity=0)
        with render_text_box(replace(options, height=None), (600, 400)) as automatic:
            with render_text_box(options, (600, 400)) as fixed:
                self.assertEqual(fixed.size, (270, 60))
                self.assertGreater(automatic.height, fixed.height)
                # The visible first line uses the same font and position after resizing.
                with automatic.crop((0, 0, fixed.width, 45)) as expected:
                    with fixed.crop((0, 0, fixed.width, 45)) as visible:
                        self.assertIsNone(ImageChops.difference(visible, expected).getbbox(alpha_only=False))
        for height in (0, -1, 1.1, float("nan"), float("inf")):
            with self.subTest(height=height), self.assertRaises(ValueError):
                replace(options, height=height)


class TextEditorTests(unittest.TestCase):
    def setUp(self):
        self.state = PhotoToolState(_reflex_internal_init=True)
        buffer = io.BytesIO()
        with Image.new("RGB", (600, 400), "white") as source:
            source.save(buffer, format="PNG")
        self.state._files = [("source.png", buffer.getvalue())]
        self.state.file_count = 1
        self.state._load_primary_preview()

    def test_add_edit_move_select_delete_and_reset(self):
        state = self.state
        state.add_text_box()
        first_id = state.text_selected_id
        state.change_text_content("中文说明\n第二行")
        state.change_text_font_size("28")
        state.change_text_background("#123456")
        state.change_text_opacity(40)
        state.change_text_align("center")
        state.change_text_bold(True)
        state.move_text_box(json.dumps({"id": first_id, "x": 90, "y": 95}))
        self.assertLessEqual(state.text_x + state.text_width, 100)
        self.assertLess(state.text_y, 95)
        self.assertEqual(state.text_boxes[0].text, "中文说明\n第二行")
        self.assertTrue(state.text_boxes[0].bold)
        state.add_text_box()
        state.select_text_box(first_id)
        self.assertEqual(state.text_font_size, 28)
        self.assertEqual(state.text_background, "#123456")
        self.assertEqual(state.text_opacity, 40)
        state.delete_text_box()
        self.assertEqual(len(state.text_boxes), 1)
        self.assertNotEqual(state.text_selected_id, first_id)
        state.clear_files()
        self.assertEqual(state.text_boxes, [])
        self.assertFalse(state.has_selected_text)

    def test_preview_tile_matches_export_at_source_resolution(self):
        state = self.state
        state.add_text_box()
        state.change_text_content("导出一致性\nABC")
        state.rotate_right()
        state.move_text_box(json.dumps({"id": state.text_selected_id, "x": 30, "y": 40, "width": 35, "height": 25}))
        box = state.text_boxes[0]
        tile_data = base64.b64decode(box.preview_url.split(",", 1)[1])
        with Image.open(io.BytesIO(state._files[0][1])) as source:
            options = state._conversion_options()
            with ImageConversionService.transform_image(source, replace(options, output_format="PNG")) as result:
                with ImageConversionService.transform_image(source, replace(options, output_format="PNG", text_boxes=())) as expected:
                    with Image.open(io.BytesIO(tile_data)) as tile:
                        layout = json.loads(box.preview_layout)
                        self.assertEqual((layout["canvasWidth"], layout["canvasHeight"]), result.size)
                        self.assertEqual((layout["width"], layout["height"]), tile.size)
                        self.assertEqual(layout["fontSize"], state.text_font_size)
                        self.assertTrue(layout["fontFamily"])
                        expected = expected.convert("RGBA")
                        expected.alpha_composite(tile, (round(box.x * expected.width / 100), round(box.y * expected.height / 100)))
                        self.assertIsNone(ImageChops.difference(result, expected).getbbox(alpha_only=False))
                        expected.close()

    def test_drag_payload_is_atomic_and_rejects_invalid_values(self):
        state = self.state
        state.add_text_box()
        original = state.text_boxes[0]
        for payload in ("bad json", "null", "{}", "[]", json.dumps({"id": original.id, "x": "NaN", "y": 5}), json.dumps({"id": "unknown", "x": 2, "y": 3})):
            state.move_text_box(payload)
        self.assertEqual(state.text_boxes[0], original)
        state.move_text_box(json.dumps({"id": original.id, "x": 25, "y": 35}))
        self.assertEqual((state.text_x, state.text_y), (25, 35))

    def test_delayed_edit_stays_with_its_box_after_selection_changes(self):
        state = self.state
        state.add_text_box()
        first_id = state.text_selected_id
        state.add_text_box()
        second_id = state.text_selected_id
        state.change_text_content("第一框的延迟输入", first_id)
        state.change_text_font_size("28", first_id)
        self.assertEqual(state.text_boxes[0].text, "第一框的延迟输入")
        self.assertEqual(state.text_boxes[0].font_size, 28)
        self.assertEqual(state.text_selected_id, second_id)
        self.assertEqual(state.text_content, "请输入文字说明")

    def test_resize_survives_editing_and_moving_then_restores_auto_height(self):
        state = self.state
        state.add_text_box()
        first_id = state.text_selected_id
        state.move_text_box(json.dumps({"id": first_id, "x": 20, "y": 30, "width": 35, "height": 40}))
        self.assertEqual((state.text_width, state.text_height, state.text_x, state.text_y), (35, 40, 20, 30))
        state.change_text_content("调整说明框\n第二行")
        self.assertEqual(state.text_height, 40)
        state.move_text_box(json.dumps({"id": first_id, "x": 80, "y": 90}))
        self.assertEqual((state.text_x, state.text_y), (65, 60))
        self.assertEqual((state.text_width, state.text_height), (35, 40))
        state.add_text_box()
        second_id = state.text_selected_id
        state.change_text_height("25", first_id)
        self.assertEqual(state.text_boxes[0].height, 25)
        self.assertIsNone(state.text_boxes[1].height)
        state.select_text_box(first_id)
        state.auto_text_height(first_id)
        self.assertIsNone(state.text_boxes[0].height)
        self.assertNotEqual(state.text_height, 25)
        self.assertNotEqual(state.text_selected_id, second_id)

    def test_setting_height_preserves_the_automatically_fitted_width(self):
        state = self.state
        state.add_text_box()
        state.change_text_content("\u77ed\u8bf4\u660e")
        fitted_width = state.text_width
        self.assertLess(fitted_width, 45)
        state.change_text_height("30")
        self.assertAlmostEqual(state.text_width, fitted_width, places=1)
        self.assertEqual(state.text_height, 30)
        state.auto_text_height(state.text_selected_id)
        self.assertAlmostEqual(state.text_width, fitted_width, places=1)

    def test_invalid_resize_does_not_partially_move_the_box(self):
        state = self.state
        state.add_text_box()
        original = state.text_boxes[0]
        payload = {"id": original.id, "x": 20, "y": 30, "width": 35, "height": 40}
        for invalid in ({"width": 0}, {"height": -1}, {"width": float("nan")}, {"height": float("inf")}, {"height": 101}, {"width": None}):
            with self.subTest(invalid=invalid):
                state.move_text_box(json.dumps({**payload, **invalid}))
                self.assertEqual(state.text_boxes[0], original)
        del payload["height"]
        state.move_text_box(json.dumps(payload))
        self.assertEqual(state.text_boxes[0], original)


if __name__ == "__main__":
    unittest.main()
