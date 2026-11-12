"""The channel between phones and the PC.

Protocol (JSON over WebSocket):

    phone -> PC   {"type": "pair", "code": "...", "name": "Pixel 7"}   first visit
    PC -> phone   {"type": "paired", "key": "..."}           the phone keeps the key
    phone -> PC   {"type": "hello", "key": "..."}            every later visit
    PC -> phone   {"type": "welcome", "panels": [...], "language": "ru" | null,
                   "active": ["x4"] | null}
    phone -> PC   {"type": "down", "id": 7, "panel": "x4", "button": "map"}
    phone -> PC   {"type": "up",   "id": 8, "panel": "x4", "button": "map"}
    PC -> phone   {"type": "ack",  "id": 7, "ok": true}
                  {"type": "ack",  "id": 7, "ok": false, "reason": "elevated"}
    phone -> PC   {"type": "ping", "t": 123.4}
    PC -> phone   {"type": "pong", "t": 123.4}
    PC -> phone   {"type": "panels", "panels": [...]}        panels were edited
    PC -> phone   {"type": "settings", "language": "ru" | null}
    PC -> phone   {"type": "released"}                       held keys were let go
    phone -> PC   {"type": "flip", "id": 9, "panel": "x4", "button": "lights"}
    PC -> phone   {"type": "lit", "panel": "x4", "button": "lights", "on": true}
    PC -> phone   {"type": "active", "panels": ["x4"]}       another window is active
    PC -> phone   {"type": "stopped", "panel": "x4", "button": "dock", "reason": "not_focused"}
    phone -> PC   {"type": "stop", "id": 9, "panel": "x4", "button": "dock"}   end this macro
    phone -> PC   {"type": "stop"}                           end the macros I started

"language" is the interface language chosen on the PC; null means that the
phone uses the language of its own browser.

The first message must be "pair" with the one-time code from the QR link or
"hello" with the key that pairing gave this phone. Anything else closes the
connection: CLOSE_BAD_CODE for a used or old code, CLOSE_BAD_KEY for an unknown
key, which is also what a phone gets when it is removed on the PC.

The phone names a button, never keys: the key combo is looked up on the PC.
What "down" does depends on the button's type. A phone that stops talking
for HEARTBEAT_TIMEOUT seconds is dropped and every key it holds is released.

A toggle button is lit or not. The PC keeps that state, so every phone shows
the same: "down" presses the keys and changes it, "flip" changes it without a
key, for the case the light and the game went apart. Both are told to every
phone with "lit"; "welcome" and "panels" carry the state in "on" of the button.

"active" names the panels bound to the program whose window is active on the
PC, so that a phone opens the game the player switched to. "welcome" carries
the list for a phone that connects, or null when the PC cannot tell at that
moment. After that a phone is sent "active" whenever the list is not the one
it was told last, and nothing while it is the same.

A macro button presses the keys of its steps one after another. "down" starts
the macro; on a macro that runs it changes nothing. "stop" with the button
ends it, from any phone, and is answered with "ack": a phone says which of the
two the player meant, by whether the button was lit when it was touched. A
macro runs only in a panel that is bound to a window and while that window is
active. It ends when the phone that started it goes away, or says "stop"
without a button: a phone does when its page is hidden. While a macro runs the
button is lit on every phone: "lit" says so. When the PC ends a macro before
its last step, the phone that started it is told why with "stopped".
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import itertools
import json
import logging
import time
from collections import deque
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field

from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from game_remote.access import PairingCodes
from game_remote.devices import Device, DeviceStore
from game_remote.input import Combo, InputController, InputError
from game_remote.input.windows import ForegroundInfo, input_blocked_by_elevation
from game_remote.panels import Button, PanelStore

log = logging.getLogger(__name__)

HELLO_TIMEOUT = 5.0
HEARTBEAT_TIMEOUT = 3.0
CLOSE_BAD_KEY = 4401
CLOSE_BAD_CODE = 4403
CLOSE_TIMEOUT = 4408
MAX_MESSAGE_CHARS = 2000
FOCUS_WATCH_SECONDS = 0.25


@dataclass
class Connection:
    id: str
    ws: WebSocket
    address: str
    device: Device
    held: dict[tuple[str, str], Combo] = field(default_factory=dict)
    # The panels of the active window, as this phone was told last. None: it
    # was told nothing yet, because the window was not known when it connected.
    active: list[str] | None = None


@dataclass
class Macro:
    """A macro that runs."""

    conn: Connection
    # The program whose window has to stay active while it runs.
    window: str
    task: asyncio.Task | None = None
    # Why the PC stops it; None: the player did, or it came to its end.
    reason: str | None = None


def _is_window_of(info: ForegroundInfo, window: str) -> bool:
    """True when the active window belongs to the program a panel is bound to."""
    return (info.exe_name or "").lower() == window.lower()


class RemoteHub:
    def __init__(
        self,
        controller: InputController,
        store: PanelStore,
        devices: DeviceStore,
        pairing: PairingCodes,
        foreground: Callable[[], ForegroundInfo | None] = lambda: None,
        heartbeat_timeout: float = HEARTBEAT_TIMEOUT,
    ) -> None:
        self.controller = controller
        self.store = store
        self.devices = devices
        self.pairing = pairing
        # Returns None where the foreground window cannot be inspected (not Windows).
        self.foreground = foreground
        self.heartbeat_timeout = heartbeat_timeout
        self.language: str | None = None
        self.connections: dict[str, Connection] = {}
        self.recent: deque[dict] = deque(maxlen=30)
        # Toggles that were pressed: (panel, button) -> (the state its panel file
        # starts it with, the state now). Lives as long as the program runs.
        # ponytail: entries of deleted buttons stay; a few bytes each.
        self.lit: dict[tuple[str, str], tuple[bool, bool]] = {}
        self._ids = itertools.count(1)
        self._taps: set[asyncio.Task] = set()
        # The macros that run, by (panel, button).
        self.macros: dict[tuple[str, str], Macro] = {}
        # Process that owned the active window when the last key was held down.
        self._held_pid: int | None = None

    # -- connection lifecycle -------------------------------------------------

    async def handle(self, ws: WebSocket) -> None:
        await ws.accept()
        address = ws.client.host if ws.client else "?"
        conn: Connection | None = None
        try:
            first = await self._receive(ws, HELLO_TIMEOUT)
            device, key = self._admit(first)
            if device is None:
                bad_code = first.get("type") == "pair"
                log.info("Refused %s: unknown %s", address, "code" if bad_code else "key")
                await ws.close(code=CLOSE_BAD_CODE if bad_code else CLOSE_BAD_KEY)
                return
            if key is not None:
                await self._send(ws, {"type": "paired", "key": key})
            # From here to "welcome" nothing waits: the watcher of the active
            # window cannot tell this phone anything before its first message.
            name = f"phone-{next(self._ids)}"
            conn = Connection(name, ws, address, device, active=self.active_panels())
            self.connections[conn.id] = conn
            self.devices.touch(device.id)
            log.info("%s connected from %s as %r", conn.id, address, device.name)
            welcome = {
                "type": "welcome",
                "panels": self.panels(),
                "language": self.language,
                "active": conn.active,
            }
            await self._send(ws, welcome)
            while conn.id in self.connections:
                message = await self._receive(ws, self.heartbeat_timeout)
                await self._dispatch(conn, message)
        except TimeoutError:
            log.info("%s stopped responding", conn.id if conn else address)
            await self._close(ws, CLOSE_TIMEOUT)
        except WebSocketDisconnect:
            pass
        except (ValueError, TypeError, KeyError) as exc:  # KeyError: a binary frame
            log.info("%s sent a bad message: %s", conn.id if conn else address, exc)
            await self._close(ws, 1003)
        finally:
            if conn is not None:
                if self.connections.pop(conn.id, None):
                    log.info("%s disconnected", conn.id)
                    self.devices.touch(conn.device.id)
                self._release_connection(conn)

    def _admit(self, first: dict) -> tuple[Device | None, str | None]:
        """Who is connecting. A phone that pairs right now also gets its new key."""
        kind = first.get("type")
        if kind == "hello":
            return self.devices.find(first.get("key")), None
        if kind == "pair" and self.pairing.redeem(first.get("code")):
            device, key = self.devices.add(first.get("name"))
            log.info("Paired a new device: %r", device.name)
            return device, key
        return None, None

    def online_devices(self) -> set[str]:
        return {conn.device.id for conn in self.connections.values()}

    async def drop_device(self, device_id: str) -> None:
        """Releases the keys of a removed device and closes its connections."""
        for conn in [c for c in self.connections.values() if c.device.id == device_id]:
            del self.connections[conn.id]
            self._release_connection(conn)
            await self._close(conn.ws, CLOSE_BAD_KEY)

    def rename_device(self, device: Device) -> None:
        for conn in self.connections.values():
            if conn.device.id == device.id:
                conn.device = device

    def _release_connection(self, conn: Connection) -> None:
        conn.held.clear()
        self._stop_macros_of(conn)
        try:
            self.controller.release_all(conn.id)
        except InputError:
            log.exception("Could not release the keys held by %s", conn.id)

    async def _receive(self, ws: WebSocket, timeout: float) -> dict:
        text = await asyncio.wait_for(ws.receive_text(), timeout)
        if len(text) > MAX_MESSAGE_CHARS:
            raise ValueError("message too long")
        message = json.loads(text)
        if not isinstance(message, dict):
            raise ValueError("message is not an object")
        return message

    @staticmethod
    async def _send(ws: WebSocket, message: dict) -> None:
        await ws.send_text(json.dumps(message, ensure_ascii=False))

    @staticmethod
    async def _close(ws: WebSocket, code: int) -> None:
        if ws.application_state != WebSocketState.DISCONNECTED:
            with contextlib.suppress(RuntimeError):
                await ws.close(code=code)

    async def _broadcast(self, message: dict) -> None:
        for conn in list(self.connections.values()):
            with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                await self._send(conn.ws, message)

    # -- toggles ----------------------------------------------------------------

    def panels(self) -> list[dict]:
        """The panels as the phones get them: a toggle is on or off as it is now."""
        panels = self.store.public()
        for panel in panels:
            for button in panel["buttons"]:
                if button["type"] == "toggle":
                    button["on"] = self._is_lit((panel["id"], button["id"]), button["on"])
                elif button["type"] == "macro":
                    button["on"] = (panel["id"], button["id"]) in self.macros
        return panels

    def _is_lit(self, key: tuple[str, str], start: bool) -> bool:
        known = self.lit.get(key)
        # A state that was counted from another start is forgotten: the button
        # was changed in the editor, and what the editor says shows.
        return known[1] if known and known[0] == start else start

    async def _flip(self, key: tuple[str, str], button: Button) -> None:
        lit = not self._is_lit(key, button.on)
        self.lit[key] = (button.on, lit)
        # Another press may come while the phones are being told, and reach
        # some of them first: the telling ends with the state the PC has.
        while True:
            await self._broadcast({"type": "lit", "panel": key[0], "button": key[1], "on": lit})
            now = self._is_lit(key, button.on)
            if now == lit:
                return
            lit = now

    async def broadcast_panels(self) -> None:
        message = {"type": "panels", "panels": self.panels()}
        for conn in list(self.connections.values()):
            # A removed or changed button must not stay held.
            self._release_connection(conn)
            with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                await self._send(conn.ws, message)

    # -- a held key must not follow the player into another window -------------

    def check_focus(
        self, look: Callable[[], ForegroundInfo | None] | None = None
    ) -> list[Connection]:
        """Releases every held key once the active window belongs to another
        program than at the moment of the press. Returns the phones it concerned.
        ``look`` is asked for the active window instead of ``foreground``."""
        holders = [conn for conn in self.connections.values() if conn.held]
        if not holders or self._held_pid is None:
            return []
        info = (look or self.foreground)()
        if info is None or info.pid is None or info.pid == self._held_pid:
            return []
        log.info("The active window changed: releasing held keys")
        self._held_pid = None
        for conn in holders:
            self._release_connection(conn)
        return holders

    def active_panels(
        self, look: Callable[[], ForegroundInfo | None] | None = None
    ) -> list[str] | None:
        """The panels bound to the program whose window is active now. None
        while that program is not known: between two windows, off Windows."""
        bound = [loaded for loaded in self.store.panels.values() if loaded.panel.window]
        if not bound:
            return []  # no panel has a window: the active one is not even asked about
        info = (look or self.foreground)()
        if info is None or not info.exe_name:
            return None
        return [loaded.id for loaded in bound if _is_window_of(info, loaded.panel.window)]

    async def follow_window(self, look: Callable[[], ForegroundInfo | None] | None = None) -> None:
        """Tells every phone that the active window is that of another game,
        or of none, than the phone was told last: it opens the panel of the
        game by itself. While the window is not known, nothing is said."""
        if not self.connections:
            return  # nobody to tell; a phone that connects reads it in "welcome"
        active = self.active_panels(look)
        if active is None:
            return
        for conn in list(self.connections.values()):
            if conn.active != active:
                conn.active = active
                with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                    await self._send(conn.ws, {"type": "active", "panels": active})

    # -- macros ---------------------------------------------------------------

    def _start_macro(
        self, conn: Connection, key: tuple[str, str], button: Button, window: str
    ) -> None:
        macro = Macro(conn, window)
        self.macros[key] = macro
        macro.task = asyncio.create_task(self._run_macro(key, button, macro))
        # Also when it was stopped before its first line ran.
        macro.task.add_done_callback(lambda task: self._forget_macro(key, macro))

    def _forget_macro(self, key: tuple[str, str], macro: Macro) -> None:
        if self.macros.get(key) is macro:
            del self.macros[key]

    def _stop_macros_of(self, conn: Connection) -> None:
        for macro in list(self.macros.values()):
            if macro.conn is conn:
                self._stop_macro(macro, None)

    def stop_macros(self) -> None:
        """Ends every macro that runs: "release all keys" on the PC means them too."""
        for macro in list(self.macros.values()):
            self._stop_macro(macro, None)

    @staticmethod
    def _stop_macro(macro: Macro, reason: str | None) -> None:
        """Ends a macro that runs: its keys go up, and the phones are told."""
        macro.reason = reason
        if macro.task is not None:
            macro.task.cancel()

    async def _run_macro(self, key: tuple[str, str], button: Button, macro: Macro) -> None:
        lit = {"type": "lit", "panel": key[0], "button": key[1]}
        reason = None
        try:
            await self._broadcast({**lit, "on": True})
            for step in button.steps:
                # Looked at before every step: no key goes to another window.
                reason = self._focus_problem(self.foreground(), macro.window)
                if reason:
                    break
                await self.controller.tap(step.combo, step.hold)
                await asyncio.sleep(step.wait / 1000)
        except Exception:
            # Whatever it is, the macro ends like any other: the button goes
            # dark on the phones, and the one that started it is told.
            log.exception("A macro could not go on")
            reason = "input_error"
        except asyncio.CancelledError:
            reason = macro.reason  # whoever stopped it left the reason there
        self._forget_macro(key, macro)  # before the phones are told: it runs no more
        await self._broadcast({**lit, "on": False})
        if reason:
            log.info("The macro %s of %s was stopped: %s", key[1], key[0], reason)
        if reason and macro.conn.id in self.connections:
            stopped = {"type": "stopped", "panel": key[0], "button": key[1], "reason": reason}
            with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                await self._send(macro.conn.ws, stopped)

    def check_macros(self, look: Callable[[], ForegroundInfo | None] | None = None) -> None:
        """Stops the macros whose window is not the active one any more: a
        key that a step holds must not stay down in another program."""
        if not self.macros:
            return
        info = (look or self.foreground)()
        for macro in list(self.macros.values()):
            reason = self._focus_problem(info, macro.window)
            if reason:
                self._stop_macro(macro, reason)

    async def watch_focus(self, interval: float = FOCUS_WATCH_SECONDS) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                # One look at the active window serves both checks, and none is
                # taken when neither needs it.
                look = functools.cache(self.foreground)
                for conn in self.check_focus(look):
                    with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                        await self._send(conn.ws, {"type": "released"})
                self.check_macros(look)
                await self.follow_window(look)
            except Exception:
                log.exception("Could not check the active window")

    async def set_language(self, language: str | None) -> None:
        self.language = language
        await self._broadcast({"type": "settings", "language": language})

    # -- messages -------------------------------------------------------------

    async def _dispatch(self, conn: Connection, message: dict) -> None:
        kind = message.get("type")
        if kind == "ping":
            await self._send(conn.ws, {"type": "pong", "t": message.get("t")})
        elif kind in ("down", "up", "flip"):
            reason = await self._press(conn, kind, message.get("panel"), message.get("button"))
            ack = {"type": "ack", "id": message.get("id"), "ok": reason is None}
            if reason:
                ack["reason"] = reason
            await self._send(conn.ws, ack)
        elif kind == "stop":
            key = (message.get("panel"), message.get("button"))
            if key == (None, None):
                self._stop_macros_of(conn)  # the page of the phone was left
                return
            if isinstance(key[0], str) and isinstance(key[1], str) and key in self.macros:
                self._stop_macro(self.macros[key], None)
            # A macro that came to its end by itself is as good as stopped.
            await self._send(conn.ws, {"type": "ack", "id": message.get("id"), "ok": True})
        else:
            raise ValueError(f"unknown message type {kind!r}")

    async def _press(
        self, conn: Connection, kind: str, panel_id: object, button_id: object
    ) -> str | None:
        """Carry out one button event. Returns None on success or the reason it was rejected."""
        if not isinstance(panel_id, str) or not isinstance(button_id, str):
            return "unknown_button"
        key = (panel_id, button_id)

        if kind == "up":
            combo = conn.held.pop(key, None)
            if combo is not None:
                try:
                    self.controller.unhold(conn.id, combo)
                except InputError:
                    log.exception("Could not release %s", combo)
                    return "input_error"
            return None

        loaded = self.store.get(panel_id)
        button = loaded.panel.button(button_id) if loaded else None
        if loaded is None or button is None:
            return "unknown_button"
        if kind == "flip":
            # Sets the light right and presses nothing, whatever window is active.
            if button.type != "toggle":
                return "unknown_button"
            await self._flip(key, button)
            return None
        if key in conn.held:
            return None  # already down; a repeated "down" changes nothing
        if key in self.macros:
            return None  # it runs already; the phone that wants it ended says "stop"

        info = self.foreground()
        reason = self._focus_problem(info, loaded.panel.window)
        if button.type == "macro":
            # A macro presses many keys: only in the window of its game.
            if not loaded.panel.window:
                reason = "no_window"
            if reason is None:
                self._start_macro(conn, key, button, loaded.panel.window)
        elif reason is None:
            combo = button.combo
            try:
                if button.type == "hold":
                    self.controller.hold(conn.id, combo)
                    conn.held[key] = combo
                    self._held_pid = info.pid if info else None
                else:
                    # The keys go down now; the release runs in the background.
                    task = asyncio.create_task(self._finish_tap(self.controller.start_tap(combo)))
                    self._taps.add(task)
                    task.add_done_callback(self._taps.discard)
            except InputError:
                log.exception("SendInput failed for %s", combo)
                reason = "input_error"
        if reason is None and button.type == "toggle":
            await self._flip(key, button)
        self.recent.appendleft(
            {
                "time": time.time(),
                "phone": conn.device.name,
                "panel": loaded.panel.name,
                "button": button.label or button.id,
                "keys": button.keys_label(),
                "type": button.type,
                "ok": reason is None,
                "reason": reason,
            }
        )
        return reason

    @staticmethod
    async def _finish_tap(rest: Coroutine[None, None, None]) -> None:
        try:
            await rest
        except InputError:
            log.exception("Could not release a tapped key")

    @staticmethod
    def _focus_problem(info: ForegroundInfo | None, window: str | None) -> str | None:
        if info is None:
            return None
        if window and not _is_window_of(info, window):
            return "not_focused"
        if input_blocked_by_elevation(info):
            return "elevated"
        return None
