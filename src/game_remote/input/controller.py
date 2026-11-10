"""Turns button actions (tap, hold, release) into ordered key events.

Several buttons and several phones can hold keys at the same time, so every
key has a reference count: it goes down when the first holder presses it and
up when the last holder lets go. ``release_all`` lets go of everything one
source (a phone connection) holds; it runs when a connection drops so no key
stays stuck down.
"""

from __future__ import annotations

import asyncio
from collections import Counter

from game_remote.input.backend import InputBackend, KeyEvent
from game_remote.input.keys import Combo, scan_code

DEFAULT_TAP_MS = 40


class InputController:
    def __init__(self, backend: InputBackend, tap_ms: int = DEFAULT_TAP_MS) -> None:
        self._backend = backend
        self._tap_ms = tap_ms
        self._counts: Counter[str] = Counter()
        # source -> list of combos it currently holds (a combo may repeat).
        self._holds: dict[str, list[Combo]] = {}

    @property
    def held_keys(self) -> set[str]:
        return {k for k, n in self._counts.items() if n > 0}

    def _press(self, combo: Combo) -> None:
        events = []
        for key in combo.keys:
            if self._counts[key] == 0:
                events.append(KeyEvent(key, scan_code(key), down=True))
            self._counts[key] += 1
        if events:
            self._backend.send(events)

    def _release(self, combo: Combo) -> None:
        events = []
        for key in reversed(combo.keys):
            if self._counts[key] <= 0:
                continue
            self._counts[key] -= 1
            if self._counts[key] == 0:
                del self._counts[key]
                events.append(KeyEvent(key, scan_code(key), down=False))
        if events:
            self._backend.send(events)

    async def tap(self, combo: Combo, hold_ms: int | None = None) -> None:
        """Press and release, keeping the keys down long enough for a game to notice."""
        self._press(combo)
        try:
            await asyncio.sleep((self._tap_ms if hold_ms is None else hold_ms) / 1000)
        finally:
            self._release(combo)

    def hold(self, source: str, combo: Combo) -> None:
        self._press(combo)
        self._holds.setdefault(source, []).append(combo)

    def unhold(self, source: str, combo: Combo) -> bool:
        """Release one hold of ``combo`` by ``source``. Returns False if it was not held."""
        combos = self._holds.get(source)
        if not combos or combo not in combos:
            return False
        combos.remove(combo)
        if not combos:
            del self._holds[source]
        self._release(combo)
        return True

    def is_held(self, source: str, combo: Combo) -> bool:
        return combo in self._holds.get(source, [])

    def release_all(self, source: str | None = None) -> None:
        """Release what ``source`` holds, or everything when ``source`` is None."""
        sources = list(self._holds) if source is None else [source]
        for src in sources:
            for combo in reversed(self._holds.pop(src, [])):
                self._release(combo)
