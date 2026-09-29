import tempfile
import unittest
from pathlib import Path

from PIL import Image

from phototool.core.conversion import (
    ConversionOptions,
    CropOptions,
    ImageConversionService,
    ResizeOptions,
    TransformOptions,
)
from phototool.core.image_converter import ImageConverter


class ConversionOptionsTests(unittest.TestCase):
    def test_normalizes_output_format(self):
        options = ConversionOptions(output_format="png")

        self.assertEqual(options.output_format, "PNG")

    def test_rejects_invalid_crop_rectangle(self):
        with self.assertRaises(ValueError):
            CropOptions(rect=(0.8, 0.0, 0.2, 1.0))

    def test_rejects_invalid_quality(self):
        with self.assertRaises(ValueError):
            ConversionOptions(quality=0)


class ImageConversionServiceTests(unittest.TestCase):
    def test_crop_transform_and_resize_pipeline(self):
        source = Image.new("RGB", (200, 100), "red")
        options = ConversionOptions(
            output_format="PNG",
            crop=CropOptions(rect=(0.0, 0.0, 0.5, 1.0)),
            transform=TransformOptions(angle=90),
            resize=ResizeOptions(
                enabled=True,
                width=50,
                height=50,
                keep_aspect_ratio=True,
            ),
        )

        result = ImageConversionService.transform_image(source, options)
        self.addCleanup(result.close)
        self.addCleanup(source.close)

        self.assertEqual(result.size, (50, 50))

    def test_right_angle_rotation_swaps_dimensions_without_resampling(self):
        source = Image.new("RGB", (3, 2))
        source.putdata([
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (0, 255, 255), (255, 0, 255),
        ])
        options = ConversionOptions(
            output_format="PNG",
            transform=TransformOptions(angle=90),
        )

        result = ImageConversionService.transform_image(source, options)
        self.addCleanup(result.close)
        self.addCleanup(source.close)

        self.assertEqual(result.size, (2, 3))
        self.assertEqual(result.getpixel((1, 0)), (255, 0, 0))

    def test_transparent_image_gets_white_background_for_jpeg(self):
        source = Image.new("RGBA", (4, 4), (255, 0, 0, 0))
        options = ConversionOptions(output_format="JPEG")

        result = ImageConversionService.transform_image(source, options)
        self.addCleanup(result.close)
        self.addCleanup(source.close)

        self.assertEqual(result.mode, "RGB")
        self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))

    def test_convert_file_creates_destination_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "source.png"
            output_path = root / "nested" / "result.webp"
            Image.new("RGB", (12, 8), "blue").save(source_path)

            result = ImageConversionService.convert_file(
                source_path,
                output_path,
                ConversionOptions(output_format="WEBP", quality=80),
            )

            self.assertEqual(result, output_path)
            self.assertTrue(output_path.is_file())
            with Image.open(output_path) as converted:
                self.assertEqual(converted.size, (12, 8))


class ImageConverterIconTests(unittest.TestCase):
    def test_generates_multi_size_ico(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "source.png"
            output_path = root / "icon.ico"
            Image.new("RGBA", (256, 256), (23, 105, 224, 255)).save(source_path)

            with ImageConverter(source_path) as converter:
                converter.generate_multi_size_ico(output_path, [16, 32, 48, 256])

            with Image.open(output_path) as icon:
                self.assertEqual(icon.format, "ICO")
                self.assertEqual(
                    icon.ico.sizes(),
                    {(16, 16), (32, 32), (48, 48), (256, 256)},
                )


if __name__ == "__main__":
    unittest.main()
