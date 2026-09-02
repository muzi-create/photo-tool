"""Native Windows desktop shell for the Reflex application."""

from __future__ import annotations

import socket
import threading
import time

import webview

from phototool.desktop_server import serve


DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 920
MIN_WIDTH = 1100
MIN_HEIGHT = 720


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
    """Start the local server and display it in a native resizable window."""
    server_thread = threading.Thread(target=serve, kwargs={"port": port}, daemon=True)
    server_thread.start()
    _wait_for_port("127.0.0.1", port)
    webview.create_window(
        "PhotoTool · 企业级图片处理工作台",
        f"http://127.0.0.1:{port}/",
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        resizable=True,
        text_select=True,
        background_color="#f4f7fb",
    )
    webview.start(debug=False)
    return 0
