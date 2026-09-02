"""Windows desktop entry point for PhotoTool."""

from phototool.desktop_launcher import run_desktop


def main():
    return run_desktop()


if __name__ == '__main__':
    raise SystemExit(main())
