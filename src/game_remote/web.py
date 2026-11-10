from __future__ import annotations

from importlib import resources
from pathlib import Path


def web_dir(name: str) -> Path:
    """Folder with static files for ``editor`` or ``remote`` (works inside PyInstaller too)."""
    return Path(str(resources.files("game_remote") / "web" / name))
