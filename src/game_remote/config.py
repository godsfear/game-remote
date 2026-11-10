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
    def images_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def editor_url(self) -> str:
        return f"http://{self.editor_host}:{self.editor_port}/"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.log_dir, self.images_dir):
            path.mkdir(parents=True, exist_ok=True)
