"""Application bootstrap helpers for PhotoTool."""

import subprocess
import sys
from typing import Optional, Sequence


def run(argv: Optional[Sequence[str]] = None) -> int:
    """Start the native desktop shell, with a Reflex CLI fallback for dev."""
    if argv and argv[0] == "--web":
        return subprocess.call([sys.executable, "-m", "reflex", "run", *argv[1:]])
    from phototool.desktop_launcher import run_desktop
    return run_desktop()
