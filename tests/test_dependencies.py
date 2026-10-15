from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from phototool.dependencies import (
    DependencyConfig,
    collect_bundle_imports,
    import_failures,
    main,
    read_dependency_config,
)


class DependencyManifestTests(unittest.TestCase):
    def test_reads_import_directives_without_treating_pip_requirements_as_modules(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "requirements.txt"
            path.write_text(
                "Pillow>=10\n# import: PIL.Image PIL.Image\n"
                "# preview-import: webview\n# build-import: PyInstaller\n"
                "# collect-submodules: reflex.components.core\n",
                encoding="utf-8",
            )
            config = read_dependency_config(path)

        self.assertEqual(config.runtime, ("PIL.Image",))
        self.assertNotIn("webview", config.modules("build"))
        self.assertIn("webview", config.modules("preview"))
        self.assertIn("PyInstaller", config.modules("build"))
        self.assertEqual(config.collections, ("reflex.components.core",))

    def test_rejects_invalid_import_directive_with_its_line_number(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "requirements.txt"
            path.write_text("Pillow>=10\n# import: PIL.*\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r":2: invalid import directive"):
                read_dependency_config(path)

    def test_reports_all_missing_modules_and_stops_before_installation_check(self):
        config = DependencyConfig(
            ("json", "phototool_missing_greenlet", "phototool_missing_websockets"), (), (), (),
        )
        errors = StringIO()
        with patch("phototool.dependencies.read_dependency_config", return_value=config):
            with patch("phototool.dependencies.subprocess.run") as run:
                with redirect_stderr(errors):
                    self.assertEqual(main(["--profile", "runtime"]), 1)
                run.assert_not_called()
        self.assertIn("phototool_missing_greenlet", errors.getvalue())
        self.assertIn("phototool_missing_websockets", errors.getvalue())
        self.assertIn("-m pip install -r", errors.getvalue())

    def test_declared_runtime_modules_import_successfully(self):
        config = read_dependency_config()
        self.assertEqual(import_failures(config.modules("runtime")), [])

    def test_missing_recursive_package_cannot_disappear_from_bundle_checks(self):
        config = DependencyConfig(("json",), (), (), ("phototool_missing_components",))
        with patch("PyInstaller.utils.hooks.collect_submodules", return_value=[]):
            modules = collect_bundle_imports(config)
        self.assertEqual(
            [module for module, _error in import_failures(modules)],
            ["phototool_missing_components"],
        )
