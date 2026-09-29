"""Make the exported Reflex frontend use the desktop sidecar's own origin."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIRECTORY = PROJECT_ROOT / ".web" / "build" / "client" / "assets"


def patch_reflex_environment() -> Path:
    """Replace export-time localhost URLs with browser same-origin expressions.

    The desktop shell assigns the Python sidecar a free port at runtime. Reflex
    exports its event/upload endpoints as ``localhost:8000`` by default, which
    makes stateful controls appear unresponsive in the packaged app. The
    frontend and the sidecar are served by the same process, so same-origin
    URLs are the correct runtime endpoints.
    """
    candidates = sorted(ASSET_DIRECTORY.glob("reflex-env-*.js"))
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one Reflex environment asset, found {len(candidates)}")

    asset = candidates[0]
    content = asset.read_text(encoding="utf-8")
    patched = content.replace("http://localhost:8000", "${window.location.origin}")
    patched = patched.replace(
        "ws://localhost:8000",
        '${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}',
    )
    if patched == content:
        raise RuntimeError("Reflex environment asset did not contain localhost:8000 endpoints")

    asset.write_text(patched, encoding="utf-8")
    return asset


if __name__ == "__main__":
    print(f"Patched desktop frontend endpoints: {patch_reflex_environment()}")
