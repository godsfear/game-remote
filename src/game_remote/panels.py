"""Panels: one folder per game with ``panel.json`` and its button images.

The folder is also the exchange format: zip it and you have a panel file.

    panels/
      x4/
        panel.json
        map.png
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import secrets
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from game_remote.config import system_language
from game_remote.input.keys import Combo

log = logging.getLogger(__name__)

PANEL_FILE = "panel.json"
ID_PATTERN = r"^[A-Za-z0-9_-]{1,40}$"
IMAGE_PATTERN = r"^[A-Za-z0-9_-][A-Za-z0-9_. -]{0,80}\.(png|jpg|jpeg|webp)$"
_ID_RE = re.compile(ID_PATTERN)
_IMAGE_RE = re.compile(IMAGE_PATTERN)
# Names the editor gives to uploaded images; only these are ever cleaned up.
_UPLOAD_RE = re.compile(r"^img-[0-9a-f]{12}\.(png|jpg|webp)$")
MAX_IMAGE_BYTES = 2_000_000
UNUSED_IMAGE_SECONDS = 600


class ImageError(ValueError):
    """An uploaded file is not an image this program accepts."""


def image_extension(data: bytes) -> str | None:
    """File extension for PNG, JPEG or WebP data, judged by its first bytes."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


class Button(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    label: str = Field(default="", max_length=40)
    # KeyboardEvent.code values joined by "+", e.g. "ControlLeft+KeyR".
    keys: str
    # tap: a short press. hold: the keys stay down while the finger is on the button.
    type: Literal["tap", "hold"] = "tap"
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    # A file in the panel folder.
    image: str | None = Field(default=None, pattern=IMAGE_PATTERN)

    @field_validator("keys")
    @classmethod
    def _normalise_keys(cls, value: str) -> str:
        return Combo.parse(value).serialize()

    @property
    def combo(self) -> Combo:
        return Combo.parse(self.keys)


class Panel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal[1] = 1
    name: str = Field(min_length=1, max_length=60)
    columns: int = Field(default=3, ge=1, le=8)
    # Optional exe name of the game, e.g. "X4.exe". When set, presses are
    # rejected unless that program has focus.
    window: str | None = Field(default=None, max_length=260)
    # Picture of the game for the list of games; a file in the panel folder.
    cover: str | None = Field(default=None, pattern=IMAGE_PATTERN)
    buttons: list[Button] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def _unique_button_ids(self) -> Panel:
        seen: set[str] = set()
        for button in self.buttons:
            if button.id in seen:
                raise ValueError(f"button id {button.id!r} is used twice")
            seen.add(button.id)
        return self

    def button(self, button_id: str) -> Button | None:
        return next((b for b in self.buttons if b.id == button_id), None)


@dataclass(frozen=True)
class LoadedPanel:
    id: str
    folder: Path
    panel: Panel

    def full(self) -> dict:
        """Everything, for the editor on the PC."""
        return {"id": self.id, **self.panel.model_dump()}

    def public(self) -> dict:
        """What the phone needs to draw the panel. Key combos stay on the PC."""
        return {
            "id": self.id,
            "name": self.panel.name,
            "columns": self.panel.columns,
            "cover": f"/panel-files/{self.id}/{self.panel.cover}" if self.panel.cover else None,
            "buttons": [
                {
                    "id": b.id,
                    "label": b.label,
                    "type": b.type,
                    "color": b.color,
                    "image": f"/panel-files/{self.id}/{b.image}" if b.image else None,
                }
                for b in self.panel.buttons
            ],
        }

    def image_path(self, name: str, used_only: bool = True) -> Path | None:
        """Path of an image of this panel.

        The phone only gets files the panel shows (``used_only``). The editor
        also needs a picture that was uploaded a moment ago and is not saved
        into the panel yet.
        """
        used = name == self.panel.cover or any(b.image == name for b in self.panel.buttons)
        if not _IMAGE_RE.match(name) or (used_only and not used):
            return None
        path = self.folder / name
        return path if path.is_file() else None


def short_error(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        return f"{where}: {first['msg']}" if where else first["msg"]
    return str(exc)


class PanelStore:
    """Reads every panel folder. Files with mistakes are reported, not fatal."""

    def __init__(self, root: Path, trash: Path | None = None) -> None:
        self.root = root
        # Deleted panels are moved here, not erased.
        self.trash = trash or root.parent / "trash"
        self.panels: dict[str, LoadedPanel] = {}
        self.errors: dict[str, str] = {}
        # Grows every time the panels are read again; the editor uses it to
        # notice changes it did not make itself.
        self.revision = 0
        self._signature: tuple = ()

    def _files(self) -> list[Path]:
        if not self.root.is_dir():
            return []
        return sorted(p for p in self.root.glob(f"*/{PANEL_FILE}") if p.is_file())

    def signature(self) -> tuple:
        """Changes whenever a panel file is added, removed or edited."""
        result = []
        for path in self._files():
            try:
                stat = path.stat()
            except OSError:
                continue
            result.append((str(path), stat.st_mtime_ns, stat.st_size))
        return tuple(result)

    def load(self) -> None:
        panels: dict[str, LoadedPanel] = {}
        errors: dict[str, str] = {}
        signature = self.signature()
        for path in self._files():
            panel_id = path.parent.name
            if not _ID_RE.match(panel_id):
                errors[panel_id] = "folder name: use only letters, digits, - and _"
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                panels[panel_id] = LoadedPanel(panel_id, path.parent, Panel.model_validate(data))
            except (OSError, ValueError) as exc:
                errors[panel_id] = short_error(exc)
                log.warning("Panel %s was not loaded: %s", panel_id, errors[panel_id])
        self.panels, self.errors, self._signature = panels, errors, signature
        self.revision += 1

    def reload_if_changed(self) -> bool:
        if self.signature() == self._signature:
            return False
        self.load()
        return True

    def get(self, panel_id: str) -> LoadedPanel | None:
        return self.panels.get(panel_id)

    def public(self) -> list[dict]:
        return [p.public() for p in self.panels.values()]

    # -- changes made by the editor ---------------------------------------------

    def exists(self, panel_id: str) -> bool:
        return bool(_ID_RE.match(panel_id)) and (self.root / panel_id / PANEL_FILE).is_file()

    def save(self, panel_id: str, panel: Panel) -> None:
        """Write the panel file and read the panels again."""
        if not _ID_RE.match(panel_id):
            raise ValueError(f"bad panel id {panel_id!r}")
        folder = self.root / panel_id
        folder.mkdir(parents=True, exist_ok=True)
        text = json.dumps(panel.model_dump(exclude_none=True), ensure_ascii=False, indent=2)
        # Write next to the file and swap, so a crash never leaves half a file.
        temporary = folder / (PANEL_FILE + ".tmp")
        temporary.write_text(text + "\n", encoding="utf-8")
        for attempt in range(5):
            try:
                os.replace(temporary, folder / PANEL_FILE)
                break
            except PermissionError:  # Windows: antivirus or an editor holds the file
                if attempt == 4:
                    raise
                time.sleep(0.05)
        self._remove_unused_uploads(folder, panel)
        self.load()

    def add_image(self, panel_id: str, data: bytes) -> str:
        """Store an uploaded picture in the panel folder; returns its file name."""
        if not self.exists(panel_id):
            raise KeyError(panel_id)
        if len(data) > MAX_IMAGE_BYTES:
            raise ImageError("too_large")
        extension = image_extension(data)
        if extension is None:
            raise ImageError("not_an_image")
        name = f"img-{secrets.token_hex(6)}.{extension}"
        (self.root / panel_id / name).write_bytes(data)
        return name

    @staticmethod
    def _remove_unused_uploads(folder: Path, panel: Panel) -> None:
        """Delete replaced pictures. A fresh upload is kept: the page may not
        have saved the panel that points to it yet."""
        used = {button.image for button in panel.buttons} | {panel.cover}
        for path in folder.glob("img-*"):
            if not _UPLOAD_RE.match(path.name) or path.name in used:
                continue
            with contextlib.suppress(OSError):
                if time.time() - path.stat().st_mtime > UNUSED_IMAGE_SECONDS:
                    path.unlink()

    def create(self, name: str) -> str:
        """Create an empty panel; returns its id (the folder name)."""
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30].strip("-") or "game"
        panel_id, number = base, 1
        while (self.root / panel_id).exists():
            number += 1
            panel_id = f"{base}-{number}"
        self.save(panel_id, Panel(name=name))
        return panel_id

    def delete(self, panel_id: str) -> bool:
        """Move the panel folder to the trash folder."""
        if not self.exists(panel_id):
            return False
        self.trash.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target, number = self.trash / f"{panel_id}-{stamp}", 1
        while target.exists():
            number += 1
            target = self.trash / f"{panel_id}-{stamp}-{number}"
        shutil.move(str(self.root / panel_id), str(target))
        self.load()
        return True

    def ensure_demo(self) -> bool:
        """On the very first run, create a demo panel so the phone has something to show."""
        if self.root.is_dir() and any(self.root.iterdir()):
            return False
        folder = self.root / "demo"
        folder.mkdir(parents=True, exist_ok=True)
        panel = demo_panel(russian=system_language() == "ru")
        text = json.dumps(panel.model_dump(exclude_none=True), ensure_ascii=False, indent=2)
        (folder / PANEL_FILE).write_text(text + "\n", encoding="utf-8")
        return True


def demo_panel(russian: bool) -> Panel:
    labels = (
        ("Карта", "Инвентарь", "Пауза", "Вперёд", "Бег", "Прыжок")
        if russian
        else ("Map", "Inventory", "Pause", "Forward", "Run", "Jump")
    )
    spec = (
        ("map", "KeyM", "tap", "#2b5fd9"),
        ("inventory", "KeyI", "tap", "#7a4fd1"),
        ("pause", "Escape", "tap", "#8a8f9c"),
        ("forward", "KeyW", "hold", "#2f9e62"),
        ("run", "ShiftLeft", "hold", "#c9822b"),
        ("jump", "Space", "tap", "#c44f6a"),
    )
    return Panel(
        name="Демо" if russian else "Demo",
        columns=3,
        buttons=[
            Button(id=bid, label=label, keys=keys, type=kind, color=color)
            for label, (bid, keys, kind, color) in zip(labels, spec, strict=True)
        ],
    )
