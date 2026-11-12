"""Panels: one folder per game with ``panel.json`` and its button images.

The folder is also the exchange format: zip it and you have a panel file.

    panels/
      x4/
        panel.json
        map.png
"""

from __future__ import annotations

import contextlib
import io
import json
import logging
import lzma
import re
import secrets
import shutil
import tempfile
import time
import zipfile
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from game_remote.config import system_language
from game_remote.files import replace_file
from game_remote.input.keys import Combo
from game_remote.web import sample_dir

log = logging.getLogger(__name__)

PANEL_FILE = "panel.json"
# What "format" in panel.json says. It grows by one when the file changes so
# that the program before the change cannot read it: that program then says
# "update me" (NewerFormat) instead of naming the field it stumbled over.
# Every file the program writes carries this number (see panel_text). A set
# written by hand does not: when the number grows, a file that uses what is
# new and says an older number has to be refused in Panel.
FORMAT = 1
# The ready-made panel a new user starts with: Star Citizen with the keys the
# game has by default. It ships with the program as a set, in ``samples``.
SAMPLE_ID = "star-citizen"
# Folder of the demo panel that earlier versions created on the first run.
OLD_DEMO_ID = "demo"
ID_PATTERN = r"^[A-Za-z0-9_-]{1,40}$"
IMAGE_PATTERN = r"^[A-Za-z0-9_-][A-Za-z0-9_. -]{0,80}\.(png|jpg|jpeg|webp)$"
_ID_RE = re.compile(ID_PATTERN)
_IMAGE_RE = re.compile(IMAGE_PATTERN)
# Names the editor gives to uploaded images; only these are ever cleaned up.
_UPLOAD_RE = re.compile(r"^img-[0-9a-f]{12}\.(png|jpg|webp)$")
# Device names of Windows: a folder cannot be called like one of them.
_RESERVED_RE = re.compile(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])$")
MAX_IMAGE_BYTES = 2_000_000
# A set that arrives as a zip: the whole file, one of its texts, the files it may hold
# (a picture for every button, a cover, a background and the translations).
MAX_SET_BYTES = 50_000_000
MAX_SET_TEXT_BYTES = 1_000_000
MAX_SET_FILES = 250
MAX_SCREENS = 8
UNUSED_IMAGE_SECONDS = 600


class ImageError(ValueError):
    """An uploaded file is not an image this program accepts."""


class NewerFormat(ValueError):
    """The panel was written by a newer version of the program than this one."""

    def __init__(self) -> None:
        super().__init__("made for a newer version of Game Remote: update the program")


class SameName(Exception):
    """An imported set is called like a game that is on the PC already, and
    nobody said yet whether it replaces that game or stands next to it."""

    def __init__(self, panel_id: str, name: str) -> None:
        super().__init__(f"a game called {name!r} is here already")
        self.panel_id = panel_id
        self.name = name


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
    # toggle: a short press too, and the button shows whether what it switches is on.
    type: Literal["tap", "hold", "toggle"] = "tap"
    # A toggle that is on when the program starts. The program does not see the
    # game: it counts its own presses from this state.
    on: bool = False
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    # A file in the panel folder.
    image: str | None = Field(default=None, pattern=IMAGE_PATTERN)
    # Which of the panel's screens shows the button: an index into ``screens``.
    screen: int = Field(default=0, ge=0, lt=MAX_SCREENS)

    @field_validator("keys")
    @classmethod
    def _normalise_keys(cls, value: str) -> str:
        return Combo.parse(value).serialize()

    @model_validator(mode="after")
    def _only_a_toggle_starts_on(self) -> Button:
        if self.on and self.type != "toggle":
            raise ValueError('"on" is for a button of the type "toggle"')
        return self

    @property
    def combo(self) -> Combo:
        return Combo.parse(self.keys)


class Panel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Every format this program reads; FORMAT is the newest of them.
    format: Literal[1] = 1
    # Only in a panel that is shared as a set (see PanelSet): the language its
    # texts are in, e.g. "en". A panel in the user's own folder does not carry it.
    language: str | None = Field(default=None, pattern=r"^[a-z]{2}$")
    name: str = Field(min_length=1, max_length=60)
    columns: int = Field(default=3, ge=1, le=8)
    # Optional exe name of the game, e.g. "X4.exe". When set, presses are
    # rejected unless that program has focus.
    window: str | None = Field(default=None, max_length=260)
    # Picture of the game for the list of games; a file in the panel folder.
    cover: str | None = Field(default=None, pattern=IMAGE_PATTERN)
    # Picture behind the buttons on the phone; a file in the panel folder.
    background: str | None = Field(default=None, pattern=IMAGE_PATTERN)
    # fill: the buttons share the whole screen. square: they stay square and
    # sit in the middle, so a background shows around them.
    shape: Literal["fill", "square"] = "fill"
    # Names of the screens the buttons are grouped into; the phone switches
    # between them with tabs. Empty: every button is on the one screen.
    screens: list[Annotated[str, Field(min_length=1, max_length=24)]] = Field(
        default_factory=list, max_length=MAX_SCREENS
    )
    buttons: list[Button] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def _unique_button_ids(self) -> Panel:
        seen: set[str] = set()
        for button in self.buttons:
            if button.id in seen:
                raise ValueError(f"button id {button.id!r} is used twice")
            seen.add(button.id)
        return self

    @model_validator(mode="after")
    def _buttons_on_existing_screens(self) -> Panel:
        count = max(1, len(self.screens))
        for button in self.buttons:
            if button.screen >= count:
                raise ValueError(f"button {button.id!r} is on a screen the panel does not have")
        return self

    def button(self, button_id: str) -> Button | None:
        return next((b for b in self.buttons if b.id == button_id), None)

    def images(self) -> set[str]:
        """Names of the picture files the panel shows."""
        names = {self.cover, self.background, *(b.image for b in self.buttons)}
        return {name for name in names if name}


@dataclass(frozen=True)
class LoadedPanel:
    id: str
    folder: Path
    panel: Panel

    def _version(self, name: str) -> int | None:
        """A number that changes when the file of the picture does: its time."""
        try:
            return (self.folder / name).stat().st_mtime_ns // 1_000_000
        except OSError:
            return None

    def _url(self, name: str | None) -> str | None:
        """Address of a picture of this panel. It carries the time of the file,
        so a page that is open fetches a picture again when it changed, also
        when the new file has the name of the old one."""
        if not name:
            return None
        version = self._version(name)
        return f"/panel-files/{self.id}/{name}" + (f"?v={version}" if version else "")

    def versions(self) -> dict[str, int | None]:
        """The time of every picture of the panel, by file name. The editor
        puts it into its addresses, like ``_url`` does for the phone."""
        return {name: self._version(name) for name in sorted(self.panel.images())}

    def full(self) -> dict:
        """Everything, for the editor on the PC."""
        return {"id": self.id, **self.panel.model_dump()}

    def public(self) -> dict:
        """What the phone needs to draw the panel. Key combos stay on the PC."""
        return {
            "id": self.id,
            "name": self.panel.name,
            "columns": self.panel.columns,
            "shape": self.panel.shape,
            "cover": self._url(self.panel.cover),
            "background": self._url(self.panel.background),
            "screens": self.panel.screens,
            "buttons": [
                {
                    "id": b.id,
                    "label": b.label,
                    "type": b.type,
                    "on": b.on,
                    "color": b.color,
                    "image": self._url(b.image),
                    "screen": b.screen,
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
        used = name in self.panel.images()
        if not _IMAGE_RE.match(name) or (used_only and not used):
            return None
        path = self.folder / name
        return path if path.is_file() else None


def parse_panel(data: object) -> Panel:
    """The panel that a ``panel.json`` holds. A file of a newer version is told
    apart from a file with a mistake: its other fields are not even looked at."""
    newer = isinstance(data, dict) and isinstance(data.get("format"), (int, float))
    if newer and data["format"] > FORMAT:
        raise NewerFormat
    return Panel.model_validate(data)


def panel_text(panel: Panel) -> str:
    """The panel as ``panel.json`` holds it. A panel without screens is written
    without their fields, so the version before screens still reads the file;
    the same goes for a button that is not a toggle that starts on."""
    data = panel.model_dump(exclude_none=True)
    # A file this program writes is of this program's format, whatever number
    # the panel came with: an older program must see that it is not for it.
    data["format"] = FORMAT
    if not panel.screens:
        del data["screens"]
    for button in data["buttons"]:
        if not panel.screens:
            del button["screen"]
        if not button["on"]:
            del button["on"]
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def short_error(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        return f"{where}: {first['msg']}" if where else first["msg"]
    return str(exc)


# -- sets: a panel as people share it ---------------------------------------------

_TRANSLATION_RE = re.compile(r"^panel\.([a-z]{2})\.json$")
# panel.json and whatever looks like a translation; read_set says if one is misnamed.
_SET_TEXT_RE = re.compile(r"^panel(\.[A-Za-z0-9_-]+)?\.json$")


class Translation(BaseModel):
    """The texts of a panel in one more language: ``panel.ru.json`` next to
    ``panel.json``. Keys and pictures are the same in every language."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=60)
    # Every screen of the panel, in the panel's order.
    screens: list[Annotated[str, Field(min_length=1, max_length=24)]] | None = None
    # Button id -> label. A button that is not listed keeps the label it has.
    labels: dict[str, Annotated[str, Field(max_length=40)]] = Field(default_factory=dict)


@dataclass(frozen=True)
class PanelSet:
    """A panel as people share it: the folder of a game with its pictures and,
    next to ``panel.json``, the same texts in other languages."""

    folder: Path
    panel: Panel
    translations: dict[str, Translation]

    def in_language(self, *wanted: str) -> Panel:
        """The panel a user gets: in the first of the ``wanted`` languages the
        set has, else in English, else in the language the set was written in.
        From then on it is a plain panel in one language."""
        for language in (*wanted, "en"):
            if language == self.panel.language:
                break
            texts = self.translations.get(language)
            if texts is not None:
                return self.panel.model_copy(
                    update={
                        "language": None,
                        "name": texts.name or self.panel.name,
                        "screens": texts.screens or self.panel.screens,
                        "buttons": [
                            button.model_copy(
                                update={"label": texts.labels.get(button.id, button.label)}
                            )
                            for button in self.panel.buttons
                        ],
                    }
                )
        return self.panel.model_copy(update={"language": None})


def read_set(folder: Path) -> PanelSet:
    """Reads a set and checks that it is whole. A ValueError names the file
    that is wrong."""

    def read(name: str, parse: Callable[[object], BaseModel]) -> BaseModel:
        try:
            return parse(json.loads((folder / name).read_text(encoding="utf-8-sig")))
        except NewerFormat:
            raise  # not a mistake in a file: the whole set asks for another program
        except OSError as exc:  # without the path: for an import it is a temporary folder
            raise ValueError(f"{name}: {exc.strerror or exc}") from exc
        except ValueError as exc:
            raise ValueError(f"{name}: {short_error(exc)}") from exc

    if not (folder / PANEL_FILE).is_file():
        raise ValueError(f"there is no {PANEL_FILE} in the set")
    panel = read(PANEL_FILE, parse_panel)
    for name in sorted(panel.images()):
        if not (folder / name).is_file():
            raise ValueError(f"{PANEL_FILE}: the picture {name} is not in the set")
    translations: dict[str, Translation] = {}
    for path in sorted(folder.glob("panel.*.json")):
        match = _TRANSLATION_RE.match(path.name)
        if match is None:
            raise ValueError(f"{path.name}: a translation is called like panel.ru.json")
        texts = read(path.name, Translation.model_validate)
        if match[1] == panel.language:
            raise ValueError(f"{path.name}: {PANEL_FILE} is in this language already")
        if texts.screens is not None and len(texts.screens) != len(panel.screens):
            raise ValueError(f"{path.name}: the panel has {len(panel.screens)} screens")
        unknown = sorted(set(texts.labels) - {button.id for button in panel.buttons})
        if unknown:
            raise ValueError(f"{path.name}: the panel has no button {unknown[0]!r}")
        translations[match[1]] = texts
    return PanelSet(folder, panel, translations)


def pack_set(loaded: LoadedPanel, language: str | None) -> bytes:
    """The panel as a zip that another PC can import: ``panel.json``, marked
    with the language its texts are in, and the pictures it shows.

    A picture whose file is gone is left out of ``panel.json`` too: the phone
    shows that button without a picture, and the set stays whole."""
    found = {name for name in loaded.panel.images() if (loaded.folder / name).is_file()}

    def kept(name: str | None) -> str | None:
        return name if name in found else None

    source = loaded.panel
    panel = source.model_copy(
        update={
            "language": language,
            "cover": kept(source.cover),
            "background": kept(source.background),
            "buttons": [b.model_copy(update={"image": kept(b.image)}) for b in source.buttons],
        }
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(PANEL_FILE, panel_text(panel))
        for name in sorted(found):
            archive.write(loaded.folder / name, name)
    return out.getvalue()


# What a damaged zip raises, depending on where the damage is and how the file
# was compressed. ValueError and OSError come from deep inside ``zipfile`` and
# the decompressors, with texts that say nothing to a user.
_BAD_ZIP = (zipfile.BadZipFile, zlib.error, lzma.LZMAError, EOFError, ValueError, OSError)


def unpack_set(data: bytes, folder: Path) -> None:
    """Writes the files of a zipped set into the empty ``folder``.

    The zip comes from a stranger. Only the texts and pictures of a set are
    taken, each under its own name: the folders inside the zip do not matter
    and cannot lead out of ``folder``. Sizes are counted while reading, not
    taken from what the zip declares. A ValueError says what is wrong.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (*_BAD_ZIP, RuntimeError, NotImplementedError) as exc:
        raise ValueError("not a zip file this program can read") from exc
    with archive:
        taken = 0
        for info in archive.infolist():
            name = info.filename.replace("\\", "/").rsplit("/", 1)[-1]
            text = bool(_SET_TEXT_RE.match(name))
            # Windows ignores spaces before the dot when it looks for a device name.
            device = _RESERVED_RE.match(name.split(".")[0].strip().lower())
            if info.is_dir() or device or not (text or _IMAGE_RE.match(name)):
                continue  # a readme, a licence, the folders themselves
            taken += 1
            if taken > MAX_SET_FILES:
                raise ValueError("too many files in the set")
            if (folder / name).exists():
                raise ValueError(f"{name}: twice in the zip")
            limit = MAX_SET_TEXT_BYTES if text else MAX_IMAGE_BYTES
            try:
                with archive.open(info) as source:
                    content = source.read(limit + 1)
            except NotImplementedError as exc:  # before RuntimeError: it is one
                raise ValueError(f"{name}: packed in a way this program cannot read") from exc
            except RuntimeError as exc:
                raise ValueError(f"{name}: the zip file has a password") from exc
            except _BAD_ZIP as exc:
                raise ValueError(f"{name}: the zip file is damaged") from exc
            if len(content) > limit:
                raise ValueError(f"{name}: the file is too large")
            if not text and image_extension(content) is None:
                raise ValueError(f"{name}: not a PNG, JPEG or WebP picture")
            (folder / name).write_bytes(content)


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
        # True while import_set works in its thread: the watcher leaves the
        # folder alone, and the new panel is announced once, by the import.
        self._importing = False

    def _files(self) -> list[Path]:
        if not self.root.is_dir():
            return []
        # A folder that starts with a dot is a draft of install_set, not a game.
        return sorted(
            path
            for path in self.root.glob(f"*/{PANEL_FILE}")
            if path.is_file() and not path.parent.name.startswith(".")
        )

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
                panels[panel_id] = LoadedPanel(panel_id, path.parent, parse_panel(data))
            except (OSError, ValueError) as exc:
                errors[panel_id] = short_error(exc)
                log.warning("Panel %s was not loaded: %s", panel_id, errors[panel_id])
        self.panels, self.errors, self._signature = panels, errors, signature
        self.revision += 1

    def reload_if_changed(self) -> bool:
        if self._importing or self.signature() == self._signature:
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
        # Write next to the file and swap, so a crash never leaves half a file.
        temporary = folder / (PANEL_FILE + ".tmp")
        temporary.write_text(panel_text(panel), encoding="utf-8")
        replace_file(temporary, folder / PANEL_FILE)
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
        used = panel.images()
        for path in folder.glob("img-*"):
            if not _UPLOAD_RE.match(path.name) or path.name in used:
                continue
            with contextlib.suppress(OSError):
                if time.time() - path.stat().st_mtime > UNUSED_IMAGE_SECONDS:
                    path.unlink()

    def create(self, name: str) -> str:
        """Create an empty panel; returns its id (the folder name)."""
        panel_id = self._free_id(name)
        self.save(panel_id, Panel(name=name))
        return panel_id

    def _free_id(self, name: str) -> str:
        """A folder name made from the name of the game that is not taken yet."""
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30].strip("-") or "game"
        if _RESERVED_RE.match(base):  # Windows cannot make a folder called "con" or "com1"
            base = f"game-{base}"
        panel_id, number = base, 1
        while (self.root / panel_id).exists():
            number += 1
            panel_id = f"{base}-{number}"
        return panel_id

    def import_set(
        self, data: bytes, *languages: str, same_name: Literal["add", "replace", "ask"] = "add"
    ) -> str:
        """Make the set in a zip a panel, in the first of ``languages`` the set
        has; returns its id. A ValueError says what is wrong with the file.

        ``same_name`` is what to do when a game of that name is here already:
        "add" the set next to it, "replace" the game (it goes to the trash
        folder, the set takes its place and its id), or "ask", which changes
        nothing and raises SameName.
        """
        self._importing = True
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
                unpack_set(data, Path(temporary))
                panel_set = read_set(Path(temporary))
                name = panel_set.in_language(*languages).name
                # Several games may share the name; the first of them stands for all.
                twin = next(
                    (
                        loaded.id
                        for loaded in self.panels.values()
                        if loaded.panel.name.strip().casefold() == name.strip().casefold()
                    ),
                    None,
                )
                if twin and same_name == "ask":
                    raise SameName(twin, name)
                replace = bool(twin) and same_name == "replace"
                panel_id = twin if replace else self._free_id(panel_set.panel.name)
                self.install_set(panel_set, panel_id, *languages, replace=replace)
            self.load()
        finally:
            self._importing = False
        return panel_id

    def delete(self, panel_id: str) -> bool:
        """Move the panel folder to the trash folder."""
        if not self.exists(panel_id):
            return False
        self._to_trash(panel_id)
        self.load()
        return True

    def _to_trash(self, panel_id: str) -> Path:
        """Moves the folder of the panel to the trash folder; returns where it is now."""
        self.trash.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target, number = self.trash / f"{panel_id}-{stamp}", 1
        while target.exists():
            number += 1
            target = self.trash / f"{panel_id}-{stamp}-{number}"
        shutil.move(str(self.root / panel_id), str(target))
        return target

    def install_sample(self) -> bool:
        """Put the ready-made panel next to the user's own, so the phone has
        something to show. The caller remembers that it was done: a sample the
        user deleted does not come back.

        The demo panel of earlier versions gives way to it, unless it was edited.
        """
        if self._untouched_old_demo():
            self._to_trash(OLD_DEMO_ID)
            log.info("The demo panel of the earlier version was moved to the trash folder")
        if (self.root / SAMPLE_ID).exists():
            return False
        self.install_set(read_set(sample_dir(SAMPLE_ID)), SAMPLE_ID, system_language())
        return True

    def install_set(
        self, panel_set: PanelSet, panel_id: str, *languages: str, replace: bool = False
    ) -> None:
        """Make a set one of the user's panels, in one language (see
        ``PanelSet.in_language``). The caller chooses an id that is free, or
        says that the set replaces the panel of that id: then the old one is
        moved to the trash folder once the new one is ready."""
        panel = panel_set.in_language(*languages)
        # Built aside and moved in whole, so a failure leaves no half of a panel.
        draft = self.root / f".{panel_id}.tmp"
        shutil.rmtree(draft, ignore_errors=True)
        try:
            draft.mkdir(parents=True)
            for name in sorted(panel.images()):
                shutil.copyfile(panel_set.folder / name, draft / name)
            (draft / PANEL_FILE).write_text(panel_text(panel), encoding="utf-8")
            trashed = self._to_trash(panel_id) if replace else None
            try:
                replace_file(draft, self.root / panel_id)
            except OSError:
                # The old panel comes back: an import that failed changes nothing.
                if trashed is not None:
                    with contextlib.suppress(OSError):
                        shutil.move(str(trashed), str(self.root / panel_id))
                raise
        except OSError:
            shutil.rmtree(draft, ignore_errors=True)
            raise

    def _untouched_old_demo(self) -> bool:
        folder = self.root / OLD_DEMO_ID
        try:
            if [path.name for path in folder.iterdir()] != [PANEL_FILE]:
                return False
            data = json.loads((folder / PANEL_FILE).read_text(encoding="utf-8-sig"))
            panel = Panel.model_validate(data)
        except (OSError, ValueError):
            return False
        return panel in (demo_panel(russian=True), demo_panel(russian=False))


def demo_panel(russian: bool) -> Panel:
    """The panel earlier versions created on the first run. Kept to recognise
    one that nobody edited, and as a plain panel for the tests."""
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
