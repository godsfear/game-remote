"""Everything the two servers share."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass

from game_remote.access import load_or_create_key
from game_remote.config import Settings
from game_remote.hub import RemoteHub
from game_remote.input import InputBackend, InputController, RecordingBackend
from game_remote.input.backend import default_backend
from game_remote.input.controller import DEFAULT_TAP_MS
from game_remote.input.windows import ForegroundInfo, foreground_info
from game_remote.panels import PanelStore


@dataclass
class AppState:
    settings: Settings
    backend: InputBackend
    controller: InputController
    store: PanelStore
    hub: RemoteHub
    access_key: str
    # Set by the running program: stops both servers. None while nothing is running.
    stop: Callable[[], None] | None = None

    @property
    def fake_input(self) -> bool:
        return isinstance(self.backend, RecordingBackend)


def _foreground() -> ForegroundInfo | None:
    return foreground_info() if sys.platform == "win32" else None


def build_state(
    settings: Settings, fake_input: bool = False, tap_ms: int = DEFAULT_TAP_MS
) -> AppState:
    settings.ensure_dirs()
    backend = RecordingBackend() if fake_input else default_backend()
    controller = InputController(backend, tap_ms=tap_ms)
    store = PanelStore(settings.panels_dir, settings.trash_dir)
    store.ensure_demo()
    store.load()
    access_key = load_or_create_key(settings.data_dir)
    # With fake input nothing reaches a window, so the focus checks do not apply.
    foreground = (lambda: None) if fake_input else _foreground
    hub = RemoteHub(controller, store, access_key, foreground=foreground)
    return AppState(settings, backend, controller, store, hub, access_key)
