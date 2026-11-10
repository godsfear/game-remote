"""Where the app keeps its data and which ports it listens on."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

APP_DIR_NAME = "GameRemote"
DEFAULT_EDITOR_PORT = 8730
DEFAULT_REMOTE_PORT = 8731


def default_data_dir() -> Path:
    override = os.environ.get("GAME_REMOTE_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_DIR_NAME
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "game-remote"


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


@dataclass
class Settings:
    data_dir: Path = field(default_factory=default_data_dir)
    # The editor can change buttons and approve phones, so it only listens on
    # the PC itself. The remote panel listens on the home network.
    editor_host: str = "127.0.0.1"
    editor_port: int = field(
        default_factory=lambda: _env_int("GAME_REMOTE_EDITOR_PORT", DEFAULT_EDITOR_PORT)
    )
    remote_host: str = "0.0.0.0"
    remote_port: int = field(
        default_factory=lambda: _env_int("GAME_REMOTE_REMOTE_PORT", DEFAULT_REMOTE_PORT)
    )
    open_browser: bool = True

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "game-remote.sqlite3"

    @property
    def panels_dir(self) -> Path:
        return self.data_dir / "panels"

    @property
    def editor_url(self) -> str:
        return f"http://{self.editor_host}:{self.editor_port}/"

    def remote_url(self, host: str, key: str) -> str:
        """Link for the phone. The key sits in the fragment, which browsers never send
        to a server or put in a Referer header; the page moves it to its own storage."""
        return f"http://{host}:{self.remote_port}/#k={key}"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.log_dir, self.panels_dir):
            path.mkdir(parents=True, exist_ok=True)


def system_language() -> str:
    """Interface language of the PC: "ru" or "en". Used where no browser is
    involved (the tray menu, the demo panel)."""
    if sys.platform == "win32":
        import ctypes

        try:
            # The low ten bits are the primary language; 0x19 is Russian.
            primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
        except (AttributeError, OSError):
            return "en"
        return "ru" if primary == 0x19 else "en"
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name)
        if value:
            return "ru" if value.lower().startswith("ru") else "en"
    return "en"
