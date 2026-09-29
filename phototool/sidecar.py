"""Python sidecar entry point used by the Tauri desktop shell."""

from __future__ import annotations

import argparse
import asyncio
import mimetypes
import os
from pathlib import Path
import sys
import tempfile
import traceback

import uvicorn


def configure_static_mime_types() -> None:
    """Ensure browser modules have the correct MIME type on Windows."""
    # Windows registry entries can map .js to text/plain. Starlette uses
    # mimetypes.guess_type for static assets, and browsers reject such modules.
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/javascript", ".mjs")


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[1]


def runtime_log_path() -> Path:
    """Return a writable diagnostics path without blocking server startup.

    Enterprise endpoint protection can deny writes under LOCALAPPDATA. Logging
    is optional, so always fall back to the PyInstaller extraction directory
    instead of failing before Uvicorn starts.
    """
    configured_dir = os.environ.get("PHOTOTOOL_LOG_DIR")
    candidates = [
        Path(configured_dir) if configured_dir else None,
        Path(os.environ.get("LOCALAPPDATA", "")) / "PhotoTool" / "logs",
        Path(tempfile.gettempdir()) / "PhotoTool" / "logs",
        project_root(),
    ]
    for directory in candidates:
        if directory is None:
            continue
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return directory / "sidecar.log"
        except OSError:
            continue
    # `project_root` is always the final practical fallback; defer any unusual
    # write error to the guarded logging helper below.
    return project_root() / "sidecar.log"


def write_log(path: Path, message: str) -> None:
    """Write diagnostics opportunistically; logs must never stop the app."""
    try:
        with path.open("a", encoding="utf-8") as log:
            log.write(message)
    except OSError:
        pass


async def serve_http(server: uvicorn.Server, log_path: Path) -> None:
    """Run Uvicorn inside the standard Windows asyncio loop."""
    def log_loop_error(_loop: asyncio.AbstractEventLoop, context: dict) -> None:
        error = context.get("exception")
        details = "".join(traceback.format_exception(error)) if error else repr(context)
        write_log(log_path, f"async event error: {details}\n")

    asyncio.get_running_loop().set_exception_handler(log_loop_error)
    write_log(log_path, "event loop running; starting HTTP server\n")
    await server.serve()


def bind_reflex_app(app, log_path: Path) -> None:
    """Allow Reflex event handlers to find an already imported frozen app."""
    from reflex.app import default_backend_exception_handler
    from reflex.config import get_config

    # Reflex validates the app by looking for .py files on disk. PyInstaller
    # stores them in its archive; our explicit app import has already succeeded.
    get_config()._app_name_is_valid = True

    def log_backend_error(error: Exception):
        write_log(log_path, "backend event error:\n" + "".join(traceback.format_exception(error)))
        return default_backend_exception_handler(error)

    app.backend_exception_handler = log_backend_error


class LoggedServer(uvicorn.Server):
    """Uvicorn server with startup checkpoints for frozen-process support."""

    def __init__(self, config: uvicorn.Config, log_path: Path) -> None:
        super().__init__(config)
        self._phototool_log_path = log_path

    async def serve(self, sockets=None) -> None:
        write_log(self._phototool_log_path, "Uvicorn serve entered\n")
        with self.capture_signals():
            write_log(self._phototool_log_path, "Uvicorn signal handlers installed\n")
            await self._serve(sockets)

    async def _serve(self, sockets=None) -> None:
        write_log(self._phototool_log_path, "Uvicorn internal startup entered\n")
        await super()._serve(sockets)

    async def startup(self, sockets=None) -> None:
        write_log(self._phototool_log_path, "Uvicorn port binding entered\n")
        await super().startup(sockets)
        write_log(self._phototool_log_path, f"Uvicorn port binding complete={self.started}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="PhotoTool Python sidecar")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    log_path = runtime_log_path()
    try:
        configure_static_mime_types()
        os.chdir(project_root())
        write_log(log_path, f"starting port={args.port} root={project_root()} frozen={getattr(sys, 'frozen', False)}\n")
        from reflex.environment import environment

        # Reflex uses its internal ``__REFLEX_SKIP_COMPILE`` environment key.
        # Set it through the EnvVar API; setting ``REFLEX_SKIP_COMPILE`` has no
        # effect and makes a frozen Sidecar try to rebuild the frontend.
        environment.REFLEX_SKIP_COMPILE.set(True)
        environment.REFLEX_MOUNT_FRONTEND_COMPILED_APP.set(True)
        from phototool.phototool import app
        from reflex.utils import prerequisites
        write_log(
            log_path,
            "initializing ASGI application "
            f"skip_compile={environment.REFLEX_SKIP_COMPILE.get()} "
            f"web_dir={prerequisites.get_web_dir()}\n",
        )
        asgi_app = app()
        bind_reflex_app(app, log_path)
        write_log(log_path, "ASGI application initialized; starting HTTP server\n")
        # Avoid Uvicorn's automatic protocol and event-loop discovery. Those
        # choices are loaded dynamically and can be absent from a PyInstaller
        # executable even though they are available in a source checkout.
        # Explicitly loading the configuration also gives useful diagnostics
        # when a packaged dependency is missing.
        config = uvicorn.Config(
            asgi_app,
            host="127.0.0.1",
            port=args.port,
            log_level="warning",
            log_config=None,
            access_log=False,
            factory=False,
            loop="asyncio",
            http="h11",
            ws="websockets",
            lifespan="off",
        )
        write_log(log_path, "loading HTTP server configuration\n")
        config.load()
        write_log(log_path, "HTTP server configuration loaded\n")
        write_log(log_path, "event loop selected; binding HTTP port\n")
        server = LoggedServer(config, log_path)
        # Avoid Server.run here: current Uvicorn chooses an asyncio.Runner
        # loop factory dynamically. In a one-file executable that selection
        # can block before the loop begins. The standard asyncio loop is fully
        # sufficient for this single local server.
        asyncio.run(serve_http(server, log_path))
    except Exception:
        write_log(log_path, traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
