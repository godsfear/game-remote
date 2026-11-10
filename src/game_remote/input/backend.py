"""Where key events go: Windows SendInput in the app, a recorder in tests."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Protocol

from game_remote.input.keys import ScanCode


@dataclass(frozen=True)
class KeyEvent:
    key: str
    scan: ScanCode
    down: bool


class InputBackend(Protocol):
    def send(self, events: list[KeyEvent]) -> None:
        """Inject events in order. Raises InputError if Windows refused them."""
        ...


class InputError(RuntimeError):
    pass


class RecordingBackend:
    """Keeps every event in memory. Used in tests and on non-Windows machines."""

    def __init__(self) -> None:
        self.events: list[KeyEvent] = []

    def send(self, events: list[KeyEvent]) -> None:
        self.events.extend(events)

    def trace(self) -> list[str]:
        """Events as ``"+KeyM"`` / ``"-KeyM"`` strings for readable assertions."""
        return [("+" if e.down else "-") + e.key for e in self.events]

    def clear(self) -> None:
        self.events.clear()


def default_backend() -> InputBackend:
    if sys.platform == "win32":
        from game_remote.input.sendinput import SendInputBackend

        return SendInputBackend()
    return RecordingBackend()
