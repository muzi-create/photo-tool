"""Native Windows desktop shell for the Reflex application."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import webview

from phototool import __version__
from phototool.desktop_server import serve


DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 920
MIN_WIDTH = 1100
MIN_HEIGHT = 720


class _DesktopWindowControls:
    """Expose fullscreen controls to the source preview's keyboard handler."""

    def __init__(self):
        self._window = None
        self._fullscreen = True
        self._lock = threading.Lock()

    def set_fullscreen(self, fullscreen: bool | None = None) -> None:
        with self._lock:
            desired = not self._fullscreen if fullscreen is None else fullscreen
            if self._window is not None and desired != self._fullscreen:
                self._window.toggle_fullscreen()
                self._fullscreen = desired


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.4):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"PhotoTool 本地服务启动超时: {host}:{port}")


def run_desktop(port: int = 8765) -> int:
    """Start the local server and display it in a native fullscreen window."""
    server_thread = threading.Thread(target=serve, kwargs={"port": port}, daemon=True)
    server_thread.start()
    _wait_for_port("127.0.0.1", port)
    # PyWebView disables downloads by default. Enable its native save dialog
    # for the data URLs emitted by Reflex after conversion and icon generation.
    webview.settings["ALLOW_DOWNLOADS"] = True
    controls = _DesktopWindowControls()
    window = webview.create_window(
        f"PhotoTool v{__version__} · 个人图片处理工作台",
        f"http://127.0.0.1:{port}/",
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        fullscreen=True,
        resizable=True,
        js_api=controls,
        text_select=True,
        background_color="#f4f7fb",
    )
    controls._window = window
    shortcuts = (Path(__file__).resolve().parents[1] / "assets" / "desktop_window.js").read_text(encoding="utf-8")
    window.events.loaded += lambda: window.evaluate_js(shortcuts)
    webview.start(debug=False)
    return 0
