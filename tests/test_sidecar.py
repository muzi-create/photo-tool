import mimetypes
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from starlette.responses import FileResponse

from phototool.sidecar import bind_reflex_app, configure_static_mime_types


class AsyncDatabaseRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_sqlalchemy_async_session_runs_sync_callback(self):
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSession() as session:
            result = await session.run_sync(lambda sync_session: sync_session.info)
            self.assertEqual(result, {})


class StaticAssetMimeTests(unittest.TestCase):
    def test_javascript_modules_are_served_as_javascript(self):
        configure_static_mime_types()

        for suffix in ("js", "mjs"):
            with self.subTest(suffix=suffix):
                self.assertEqual(
                    mimetypes.guess_type(f"module.{suffix}")[0],
                    "text/javascript",
                )
                response = FileResponse(f"module.{suffix}")
                self.assertEqual(response.headers["content-type"], "text/javascript; charset=utf-8")


class FrozenAppLookupTests(unittest.TestCase):
    def test_event_app_lookup_without_source_files(self):
        from phototool.phototool import app
        from reflex.config import get_config
        from reflex.utils import prerequisites

        config = get_config()
        was_valid = config._app_name_is_valid
        handler = app.backend_exception_handler
        try:
            config._app_name_is_valid = False
            with patch.object(prerequisites, "get_module_path", return_value=None):
                with self.assertRaises(ModuleNotFoundError):
                    prerequisites.get_and_validate_app()
                with TemporaryDirectory() as directory:
                    bind_reflex_app(app, Path(directory) / "sidecar.log")
                    self.assertIs(prerequisites.get_and_validate_app().app, app)
        finally:
            config._app_name_is_valid = was_valid
            app.backend_exception_handler = handler
