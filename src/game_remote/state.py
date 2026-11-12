"""Everything the two servers share."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from game_remote.access import PairingCodes, remove_legacy_key
from game_remote.config import Settings
from game_remote.devices import DeviceStore
from game_remote.hub import RemoteHub
from game_remote.input import InputBackend, InputController, RecordingBackend
from game_remote.input.backend import default_backend
from game_remote.input.controller import DEFAULT_TAP_MS
from game_remote.input.windows import ForegroundInfo, OpenWindow, foreground_info, open_windows
from game_remote.panels import SAMPLE_ID, PanelStore
from game_remote.updates import latest_version
from game_remote.user_settings import UserSettings, load_user_settings, save_user_settings

log = logging.getLogger(__name__)


@dataclass
class AppState:
    settings: Settings
    backend: InputBackend
    controller: InputController
    store: PanelStore
    hub: RemoteHub
    devices: DeviceStore
    pairing: PairingCodes
    user: UserSettings
    # Programs with an open window, for binding a panel to a game.
    windows: Callable[[], list[OpenWindow]] = open_windows
    # Asks for the version of the latest release; None when it is not known.
    latest_version: Callable[[], str | None] = latest_version
    # A newer version of the program that is out, for the editor to tell about.
    update: str | None = None
    # Set to ask for the latest version now, not when its day has passed.
    check_now: asyncio.Event = field(default_factory=asyncio.Event)
    # Set by the running program: stops both servers. None while nothing is running.
    stop: Callable[[], None] | None = None

    @property
    def fake_input(self) -> bool:
        return isinstance(self.backend, RecordingBackend)


def open_devices(path: Path) -> DeviceStore:
    """Opens the list of paired devices. A file that SQLite cannot read is put
    aside, so the program still starts; the phones then pair again."""
    try:
        return DeviceStore(path)
    except sqlite3.DatabaseError:
        broken = path.with_name(path.name + ".broken")
        log.exception("Could not read %s; it is kept as %s", path, broken.name)
        os.replace(path, broken)
        return DeviceStore(path)


def _sample_windows() -> list[OpenWindow]:
    """What the window list shows in test mode, where no real window is involved."""
    return [
        OpenWindow(exe_name="notepad.exe", title="Untitled - Notepad", elevated=False),
        OpenWindow(exe_name="X4.exe", title="X4", elevated=False),
    ]


def _foreground() -> ForegroundInfo | None:
    return foreground_info() if sys.platform == "win32" else None


def build_state(
    settings: Settings, fake_input: bool = False, tap_ms: int = DEFAULT_TAP_MS
) -> AppState:
    settings.ensure_dirs()
    backend = RecordingBackend() if fake_input else default_backend()
    controller = InputController(backend, tap_ms=tap_ms)
    store = PanelStore(settings.panels_dir, settings.trash_dir)
    user = load_user_settings(settings.user_settings_path)
    if SAMPLE_ID not in user.samples:
        try:
            store.install_sample()
            user = user.model_copy(update={"samples": [*user.samples, SAMPLE_ID]})
            save_user_settings(settings.user_settings_path, user)
        except (OSError, ValueError):  # ValueError: the packaged set could not be read
            log.exception("Could not install the ready-made panel")
    store.load()
    if remove_legacy_key(settings.data_dir):
        log.info("Removed the shared key of the first prototype; phones pair again by QR code")
    devices = open_devices(settings.db_path)
    pairing = PairingCodes()
    # With fake input nothing reaches a window, so the focus checks do not apply.
    foreground = (lambda: None) if fake_input else _foreground
    hub = RemoteHub(controller, store, devices, pairing, foreground=foreground)
    hub.language = user.forced_language
    windows = _sample_windows if fake_input else open_windows
    state = AppState(settings, backend, controller, store, hub, devices, pairing, user, windows)
    if fake_input:
        # Test mode stays on the PC: nothing is asked outside it.
        state.latest_version = lambda: None
    return state
