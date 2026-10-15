"""Windows desktop entry point for PhotoTool."""

from phototool.dependencies import main as check_dependencies


def main():
    if check_dependencies(["--profile", "preview"]):
        return 1
    from phototool.desktop_launcher import run_desktop

    return run_desktop()


if __name__ == '__main__':
    raise SystemExit(main())
