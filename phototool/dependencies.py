"""Check and collect dependencies declared in requirements.txt."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib
from pathlib import Path
import re
import subprocess
import sys


REQUIREMENTS_PATH = Path(__file__).resolve().parents[1] / "requirements.txt"
DIRECTIVES = ("import", "preview-import", "build-import", "collect-submodules")
MODULE_NAME = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", re.ASCII)


def unique(names) -> tuple[str, ...]:
    return tuple(dict.fromkeys(names))


@dataclass(frozen=True)
class DependencyConfig:
    runtime: tuple[str, ...]
    preview: tuple[str, ...]
    build: tuple[str, ...]
    collections: tuple[str, ...]

    def modules(self, profile: str) -> tuple[str, ...]:
        names = [*self.runtime, *self.collections]
        if profile in ("preview", "all"):
            names.extend(self.preview)
        if profile in ("build", "all"):
            names.extend(self.build)
        return unique(names)


def read_dependency_config(path: Path = REQUIREMENTS_PATH) -> DependencyConfig:
    groups = {directive: [] for directive in DIRECTIVES}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.lstrip().startswith("#"):
            continue
        name, separator, value = line.lstrip()[1:].strip().partition(":")
        if name not in groups:
            continue
        modules = value.split()
        if not separator or not modules or any(not MODULE_NAME.fullmatch(module) for module in modules):
            raise ValueError(f"{path}:{number}: invalid {name} directive")
        groups[name].extend(modules)
    if not groups["import"]:
        raise ValueError(f"{path}: no runtime import directives found")
    return DependencyConfig(*(unique(groups[name]) for name in DIRECTIVES))


def collect_bundle_imports(config: DependencyConfig) -> tuple[str, ...]:
    from PyInstaller.utils.hooks import collect_submodules

    names = [*config.runtime, *config.collections]
    for package in config.collections:
        # The default is to warn and skip a package on import failure. A broken
        # required component must stop the build instead of producing an exe.
        names.extend(collect_submodules(package, on_error="raise"))
    return unique(names)


def import_failures(modules) -> list[tuple[str, str]]:
    failures = []
    for module in modules:
        try:
            importlib.import_module(module)
        except Exception as error:
            failures.append((module, f"{type(error).__name__}: {error}"))
    return failures


def failure_message(failures) -> str:
    details = "\n".join(f"  {module}: {error}" for module, error in failures)
    install = subprocess.list2cmdline([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)])
    return f"Dependency imports failed:\n{details}\nInstall with the same Python interpreter:\n  {install}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("runtime", "preview", "build", "all"), default="all")
    args = parser.parse_args(argv)
    try:
        config = read_dependency_config()
        modules = config.modules(args.profile)
        failures = import_failures(modules)
        if failures:
            print(failure_message(failures), file=sys.stderr)
            return 1
        if args.profile in ("build", "all"):
            modules = unique((*modules, *collect_bundle_imports(config)))
            failures = import_failures(modules)
            if failures:
                print(failure_message(failures), file=sys.stderr)
                return 1
    except Exception as error:
        print(f"Dependency check failed: {error}", file=sys.stderr)
        return 1
    result = subprocess.run([sys.executable, "-m", "pip", "check"], check=False)
    if result.returncode:
        return result.returncode
    print(f"Dependency imports passed: {len(modules)} modules ({args.profile}); Python: {sys.executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
