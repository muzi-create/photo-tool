"""Python sidecar entry point used by the Tauri desktop shell."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import uvicorn


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="PhotoTool Python sidecar")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    os.chdir(project_root())
    from reflex.environment import environment
    from phototool.phototool import app
    environment.REFLEX_MOUNT_FRONTEND_COMPILED_APP.set(True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", factory=True)


if __name__ == "__main__":
    main()
