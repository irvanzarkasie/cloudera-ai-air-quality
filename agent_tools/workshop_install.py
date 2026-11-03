"""Smart dependency install for CAI notebooks (skip / wheelhouse / PyPI)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _pip(*args: str) -> None:
    subprocess.check_call([sys.executable, "-m", "pip", "install", *args])


def wheelhouse_dir(root: Path) -> Path | None:
    env = os.environ.get("AIRAWARE_WHEELHOUSE")
    if env:
        p = Path(env)
        return p if p.is_dir() else None
    tag = os.environ.get("WHEELHOUSE_TAG", "cai-py311-linux")
    candidate = root / "wheelhouse" / tag
    if candidate.is_dir() and any(candidate.glob("*.whl")):
        return candidate
    return None


def _install_req(root: Path, req_file: str, *, allow_pypi: bool = True) -> None:
    wh = wheelhouse_dir(root)
    path = root / req_file
    if not path.is_file():
        raise FileNotFoundError(path)
    if wh:
        print(f"Using offline wheelhouse: {wh}")
        _pip("--no-index", f"--find-links={wh}", "-r", str(path))
    elif allow_pypi:
        _pip("-r", str(path))
    else:
        raise RuntimeError(f"Missing wheels for {req_file}; set AIRAWARE_WHEELHOUSE or allow PyPI.")


def _minimal_imports_ok() -> bool:
    """All packages from requirements-minimal.txt (CAI base images often preinstall pandas only)."""
    needed = ("pandas", "requests", "folium", "pydantic", "dotenv")
    for name in needed:
        try:
            __import__(name)
        except ImportError:
            return False
    return True


def ensure_minimal(root: Path | None = None, *, allow_pypi: bool = True) -> None:
    root = root or Path.cwd()
    if _minimal_imports_ok():
        print("requirements-minimal: already satisfied")
        return
    _install_req(root, "requirements-minimal.txt", allow_pypi=allow_pypi)


def ensure_crewai(root: Path | None = None, *, allow_pypi: bool = True) -> None:
    root = root or Path.cwd()
    try:
        import crewai  # noqa: F401
    except ImportError:
        _install_req(root, "requirements-crewai-addon.txt", allow_pypi=allow_pypi)
    else:
        print("requirements-crewai-addon: already satisfied")


def ensure_workshop_deps(root: Path | None = None, *, allow_pypi: bool = True) -> None:
    root = root or Path.cwd()
    ensure_minimal(root, allow_pypi=allow_pypi)
    ensure_crewai(root, allow_pypi=allow_pypi)


if __name__ == "__main__":
    ensure_workshop_deps(Path.cwd())
    print("ensure_workshop_deps: ok")
