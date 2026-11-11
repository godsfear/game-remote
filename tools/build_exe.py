"""Builds the single-file program with PyInstaller.

    pip install -e ".[dev]"
    python tools/build_exe.py

The result is dist/GameRemote.exe on Windows. On other systems the same
command builds dist/GameRemote, which is only useful to check the build.
"""

from __future__ import annotations

import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "build"


def write_icon() -> Path | None:
    """The exe icon is the tray icon, drawn by the same code."""
    try:
        from game_remote.tray import make_icon_image
    except ImportError:
        return None
    try:
        image = make_icon_image(256)
    except ImportError:  # Pillow is only installed on Windows
        return None
    WORK.mkdir(exist_ok=True)
    path = WORK / "GameRemote.ico"
    image.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])
    return path


def main() -> None:
    args = [
        str(ROOT / "tools" / "exe_entry.py"),
        "--name=GameRemote",
        "--onefile",
        "--noconsole",
        "--noconfirm",
        "--clean",
        f"--paths={ROOT / 'src'}",
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={WORK}",
        f"--specpath={WORK}",
        f"--add-data={ROOT / 'src' / 'game_remote' / 'web'}:game_remote/web",
        f"--add-data={ROOT / 'src' / 'game_remote' / 'samples'}:game_remote/samples",
        # Uvicorn picks its event loop, HTTP and WebSocket code by name at run time.
        "--collect-submodules=uvicorn",
        "--collect-submodules=websockets",
    ]
    if sys.platform == "win32":
        args.append("--hidden-import=pystray._win32")
        icon = write_icon()
        if icon:
            args.append(f"--icon={icon}")
    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    main()
