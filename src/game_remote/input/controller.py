"""Turns button actions (tap, hold, release) into ordered key events.

Several buttons and several phones can hold keys at the same time, so every
key has a reference count: it goes down when the first holder presses it and
up when the last holder lets go. ``release_all`` lets go of everything one
source (a phone connection) holds; it runs when a connection drops so no key
stays stuck down.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import Counter
from collections.abc import Coroutine

from game_remote.input.backend import InputBackend, InputError, KeyEvent
from game_remote.input.keys import Combo, scan_code

DEFAULT_TAP_MS = 40


class InputController:
    def __init__(self, backend: InputBackend, tap_ms: int = DEFAULT_TAP_MS) -> None:
        self._backend = backend
        self._tap_ms = tap_ms
        self._counts: Counter[str] = Counter()
        # source -> list of combos it currently holds (a combo may repeat).
        self._holds: dict[str, list[Combo]] = {}
        # Keys whose release Windows refused: they may still be down.
        self._stuck: set[str] = set()

    @property
    def held_keys(self) -> set[str]:
        return {k for k, n in self._counts.items() if n > 0} | self._stuck

    def _press(self, combo: Combo) -> None:
        fresh = [key for key in combo.keys if self._counts[key] == 0]
        if fresh:
            try:
                self._backend.send([KeyEvent(key, scan_code(key), down=True) for key in fresh])
            except InputError:
                # Nothing is counted as held, or every later press of these keys
                # would be taken for "already down" and never reach Windows.
                # Windows may have taken a part of the events before it refused,
                # so the keys of this press are let go as well.
                ups = [KeyEvent(key, scan_code(key), down=False) for key in reversed(fresh)]
                with contextlib.suppress(InputError):
                    self._backend.send(ups)
                raise
        for key in combo.keys:
            self._counts[key] += 1
        self._stuck.difference_update(fresh)

    def _release(self, combo: Combo) -> None:
        keys = []
        for key in reversed(combo.keys):
            if self._counts[key] <= 0:
                continue
            self._counts[key] -= 1
            if self._counts[key] == 0:
                del self._counts[key]
                keys.append(key)
        self._send_up(keys)

    def _send_up(self, keys: list[str]) -> None:
        if not keys:
            return
        try:
            self._backend.send([KeyEvent(key, scan_code(key), down=False) for key in keys])
        except InputError:
            self._stuck.update(keys)
            raise
        self._stuck.difference_update(keys)

    async def tap(self, combo: Combo, hold_ms: int | None = None) -> None:
        """Press and release, keeping the keys down long enough for a game to notice."""
        await self.start_tap(combo, hold_ms)

    def start_tap(self, combo: Combo, hold_ms: int | None = None) -> Coroutine[None, None, None]:
        """Press now and return the rest of the tap (wait, then release) to await.

        Pressing right away lets the caller report a failed press to the phone.
        """
        self._press(combo)
        return self._finish_tap(combo, hold_ms)

    async def _finish_tap(self, combo: Combo, hold_ms: int | None) -> None:
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
        """Release what ``source`` holds, or everything when ``source`` is None.

        One refused release does not stop the rest; the error is raised at the end.
        Releasing everything also tries again the keys Windows refused to let go.
        """
        sources = list(self._holds) if source is None else [source]
        failure: InputError | None = None
        for src in sources:
            for combo in reversed(self._holds.pop(src, [])):
                try:
                    self._release(combo)
                except InputError as exc:
                    failure = exc
        if source is None:
            try:
                self._send_up(sorted(self._stuck))
            except InputError as exc:
                failure = exc
        if failure is not None:
            raise failure
