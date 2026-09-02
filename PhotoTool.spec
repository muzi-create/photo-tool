# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller configuration for the native Windows desktop build."""

from pathlib import Path

from PyInstaller.building.build_main import Analysis, EXE, PYZ, COLLECT
from PyInstaller.utils.hooks import collect_all, collect_submodules


project_root = Path(SPECPATH)
reflex_datas, reflex_binaries, reflex_hidden = collect_all("reflex")
webview_datas, webview_binaries, webview_hidden = collect_all("webview")
uvicorn_datas, uvicorn_binaries, uvicorn_hidden = collect_all("uvicorn")

datas = [
    (str(project_root / "assets"), "assets"),
    (str(project_root / ".web"), ".web"),
    (str(project_root / "rxconfig.py"), "."),
    *reflex_datas,
    *webview_datas,
    *uvicorn_datas,
]

hiddenimports = sorted(set(
    reflex_hidden + webview_hidden + uvicorn_hidden + collect_submodules("phototool") + [
        "phototool.phototool", "phototool.web_state", "phototool.desktop_server",
        "phototool.desktop_launcher", "uvicorn.loops.auto",
        "uvicorn.protocols.http.h11_impl", "uvicorn.protocols.websockets.websockets_impl",
    ]
))

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=reflex_binaries + webview_binaries + uvicorn_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["PyQt5", "tkinter", "test", "unittest", "distutils", "setuptools", "pip"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="PhotoTool", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    icon=str(project_root / "assets" / "img" / "logo.ico"),
)

coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, name="PhotoTool")
