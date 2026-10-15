# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
from PyInstaller.building.build_main import Analysis, EXE, PYZ
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH)
sys.path.insert(0, str(root))
from phototool.dependencies import (
    collect_bundle_imports, failure_message, import_failures, read_dependency_config,
)

# Installation, import checks and frozen imports share requirements.txt.
hidden = list(collect_bundle_imports(read_dependency_config(root / "requirements.txt")))
failures = import_failures(hidden)
if failures:
    raise SystemExit(failure_message(failures))

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
