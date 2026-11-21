from __future__ import annotations

import mimetypes
import sys
from pathlib import Path

# The pages are served with the type that ``mimetypes`` names for a file, and
# on Windows it reads the registry, where any program may have written
# anything. A browser runs a script and draws a sign only when they come as
# what they are.
for _suffix, _kind in ((".js", "text/javascript"), (".css", "text/css"), (".svg", "image/svg+xml")):
    mimetypes.add_type(_kind, _suffix)


def packaged(*parts: str) -> Path:
    """A folder that ships inside the program: next to this file, or inside the exe."""
    if getattr(sys, "frozen", False):  # inside the PyInstaller exe
        return Path(sys._MEIPASS).joinpath("game_remote", *parts)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.joinpath(*parts)


def web_dir(name: str) -> Path:
    """Folder with the static files of ``editor``, ``remote`` or ``shared``."""
    return packaged("web", name)


def sample_dir(name: str) -> Path:
    """Folder of a ready-made panel: a set, as ``panels.read_set`` reads it."""
    return packaged("samples", name)
