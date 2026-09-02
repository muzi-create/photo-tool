# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.building.build_main import Analysis, EXE, PYZ, COLLECT
from PyInstaller.utils.hooks import collect_all, collect_submodules

root = Path(SPECPATH)
reflex_datas, reflex_bins, reflex_hidden = collect_all("reflex")
uvicorn_datas, uvicorn_bins, uvicorn_hidden = collect_all("uvicorn")
datas = [
    (str(root / ".web"), ".web"),
    (str(root / "assets"), "assets"),
    *reflex_datas,
    *uvicorn_datas,
]
hidden = sorted(set(
    reflex_hidden + uvicorn_hidden + collect_submodules("phototool") + [
        "phototool.sidecar", "phototool.phototool", "phototool.web_state",
        "uvicorn.loops.auto", "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.websockets_impl",
    ]
))
a = Analysis(
    [str(root / "phototool" / "sidecar.py")],
    pathex=[str(root)], binaries=reflex_bins + uvicorn_bins,
    datas=datas, hiddenimports=hidden, excludes=["PyQt5", "tkinter", "test", "unittest"],
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [], name="PhotoToolSidecar", console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="PhotoToolSidecar", upx=False)
