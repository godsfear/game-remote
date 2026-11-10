from __future__ import annotations

import sys
from pathlib import Path


def web_dir(name: str) -> Path:
    """Folder with the static files of ``editor``, ``remote`` or ``shared``."""
    if getattr(sys, "frozen", False):  # inside the PyInstaller exe
        return Path(sys._MEIPASS) / "game_remote" / "web" / name  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / "web" / name
