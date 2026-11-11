"""The channel between phones and the PC.

Protocol (JSON over WebSocket):

    phone -> PC   {"type": "pair", "code": "...", "name": "Pixel 7"}   first visit
    PC -> phone   {"type": "paired", "key": "..."}           the phone keeps the key
    phone -> PC   {"type": "hello", "key": "..."}            every later visit
    PC -> phone   {"type": "welcome", "panels": [...], "language": "ru" | null}
    phone -> PC   {"type": "down", "id": 7, "panel": "x4", "button": "map"}
    phone -> PC   {"type": "up",   "id": 8, "panel": "x4", "button": "map"}
    PC -> phone   {"type": "ack",  "id": 7, "ok": true}
                  {"type": "ack",  "id": 7, "ok": false, "reason": "elevated"}
    phone -> PC   {"type": "ping", "t": 123.4}
    PC -> phone   {"type": "pong", "t": 123.4}
    PC -> phone   {"type": "panels", "panels": [...]}        panels were edited
    PC -> phone   {"type": "settings", "language": "ru" | null}
    PC -> phone   {"type": "released"}                       held keys were let go

"language" is the interface language chosen on the PC; null means that the
phone uses the language of its own browser.

The first message must be "pair" with the one-time code from the QR link or
"hello" with the key that pairing gave this phone. Anything else closes the
connection: CLOSE_BAD_CODE for a used or old code, CLOSE_BAD_KEY for an unknown
key, which is also what a phone gets when it is removed on the PC.

The phone names a button, never keys: the key combo is looked up on the PC.
What "down" does depends on the button's type. A phone that stops talking
for HEARTBEAT_TIMEOUT seconds is dropped and every key it holds is released.
"""

from __future__ import annotations

import asyncio
import contextlib
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
from game_remote.panels import PanelStore

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
        self._ids = itertools.count(1)
        self._taps: set[asyncio.Task] = set()
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
            conn = Connection(f"phone-{next(self._ids)}", ws, address, device)
            self.connections[conn.id] = conn
            self.devices.touch(device.id)
            log.info("%s connected from %s as %r", conn.id, address, device.name)
            if key is not None:
                await self._send(ws, {"type": "paired", "key": key})
            welcome = {"type": "welcome", "panels": self.store.public(), "language": self.language}
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

    async def broadcast_panels(self) -> None:
        message = {"type": "panels", "panels": self.store.public()}
        for conn in list(self.connections.values()):
            # A removed or changed button must not stay held.
            self._release_connection(conn)
            with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                await self._send(conn.ws, message)

    # -- a held key must not follow the player into another window -------------

    def check_focus(self) -> list[Connection]:
        """Releases every held key once the active window belongs to another
        program than at the moment of the press. Returns the phones it concerned."""
        holders = [conn for conn in self.connections.values() if conn.held]
        if not holders or self._held_pid is None:
            return []
        info = self.foreground()
        if info is None or info.pid is None or info.pid == self._held_pid:
            return []
        log.info("The active window changed: releasing held keys")
        self._held_pid = None
        for conn in holders:
            self._release_connection(conn)
        return holders

    async def watch_focus(self, interval: float = FOCUS_WATCH_SECONDS) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                for conn in self.check_focus():
                    with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                        await self._send(conn.ws, {"type": "released"})
            except Exception:
                log.exception("Could not check the active window")

    async def set_language(self, language: str | None) -> None:
        self.language = language
        message = {"type": "settings", "language": language}
        for conn in list(self.connections.values()):
            with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                await self._send(conn.ws, message)

    # -- messages -------------------------------------------------------------

    async def _dispatch(self, conn: Connection, message: dict) -> None:
        kind = message.get("type")
        if kind == "ping":
            await self._send(conn.ws, {"type": "pong", "t": message.get("t")})
        elif kind in ("down", "up"):
            reason = self._press(conn, kind, message.get("panel"), message.get("button"))
            ack = {"type": "ack", "id": message.get("id"), "ok": reason is None}
            if reason:
                ack["reason"] = reason
            await self._send(conn.ws, ack)
        else:
            raise ValueError(f"unknown message type {kind!r}")

    def _press(
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
        if key in conn.held:
            return None  # already down; a repeated "down" changes nothing

        info = self.foreground()
        reason = self._focus_problem(info, loaded.panel.window)
        if reason is None:
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
        self.recent.appendleft(
            {
                "time": time.time(),
                "phone": conn.device.name,
                "panel": loaded.panel.name,
                "button": button.label or button.id,
                "keys": button.combo.label(),
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
        if window and (info.exe_name or "").lower() != window.lower():
            return "not_focused"
        if input_blocked_by_elevation(info):
            return "elevated"
        return None
