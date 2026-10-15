# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.building.build_main import Analysis, EXE, PYZ
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)
reflex_datas = collect_data_files("reflex")
uvicorn_datas = collect_data_files("uvicorn")
datas = [
    (str(root / ".web"), ".web"),
    (str(root / "assets"), "assets"),
    # Reflex reloads this at application initialization. Without it the frozen
    # process silently falls back to an empty configuration and attempts a
    # development frontend rebuild instead of serving the exported assets.
    (str(root / "rxconfig.py"), "."),
    *reflex_datas,
    *uvicorn_datas,
]
hidden = [
        "reflex", "reflex.app", "reflex.environment", "reflex.compiler",
        "reflex.state", "reflex.utils", "reflex.utils.exec", "reflex.utils.prerequisites",
        "reflex.plugins", "reflex.plugins.sitemap", "reflex.components",
        "reflex.components.component", "reflex.components.base.meta", "reflex.vars", "reflex.vars.base",
        "phototool.phototool", "phototool.web_state", "phototool.core",
        "phototool.core.conversion", "phototool.core.image_converter", "phototool.sidecar",
        "uvicorn.loops.asyncio", "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.websockets_impl",
    ]
hidden += collect_submodules("reflex.components.base")
hidden += collect_submodules("reflex.components.radix")
hidden += collect_submodules("reflex.components.lucide")
hidden += collect_submodules("reflex.components.el")
hidden += collect_submodules("reflex.components.core")
a = Analysis(
    [str(root / "phototool" / "sidecar.py")],
    pathex=[str(root)], binaries=[],
    datas=datas, hiddenimports=hidden,
    excludes=[
        "PyQt5", "tkinter", "test", "unittest", "torch", "scipy", "pandas",
        "matplotlib", "plotly", "lxml", "zmq", "pyarrow", "openpyxl", "jupyter",
        "IPython", "nbformat", "pytest",
    ],
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [], name="PhotoToolSidecar", console=False, upx=False)
