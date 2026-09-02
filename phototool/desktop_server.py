"""Run the compiled Reflex ASGI application in the desktop process."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


def resource_root() -> Path:
    """Return the directory containing bundled Reflex assets."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[1]


def serve(port: int = 8765) -> None:
    """Serve the compiled Reflex app on localhost for the webview."""
    root = resource_root()
    os.chdir(root)
    from reflex.environment import environment
    from phototool.phototool import app

    environment.REFLEX_MOUNT_FRONTEND_COMPILED_APP.set(True)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        loop="asyncio",
        factory=True,
    )
