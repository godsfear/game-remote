"""The channel between phones and the PC.

Protocol (JSON over WebSocket):

    phone -> PC   {"type": "hello", "key": "..."}            must come first
    PC -> phone   {"type": "welcome", "panels": [...], "language": "ru" | null}
    phone -> PC   {"type": "down", "id": 7, "panel": "x4", "button": "map"}
    phone -> PC   {"type": "up",   "id": 8, "panel": "x4", "button": "map"}
    PC -> phone   {"type": "ack",  "id": 7, "ok": true}
                  {"type": "ack",  "id": 7, "ok": false, "reason": "elevated"}
    phone -> PC   {"type": "ping", "t": 123.4}
    PC -> phone   {"type": "pong", "t": 123.4}
    PC -> phone   {"type": "panels", "panels": [...]}        panels were edited
    PC -> phone   {"type": "settings", "language": "ru" | null}

"language" is the interface language chosen on the PC; null means that the
phone uses the language of its own browser.

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

from game_remote.access import key_matches
from game_remote.input import Combo, InputController, InputError
from game_remote.input.windows import ForegroundInfo, input_blocked_by_elevation
from game_remote.panels import PanelStore

log = logging.getLogger(__name__)

HELLO_TIMEOUT = 5.0
HEARTBEAT_TIMEOUT = 3.0
CLOSE_BAD_KEY = 4401
CLOSE_TIMEOUT = 4408
MAX_MESSAGE_CHARS = 2000


@dataclass
class Connection:
    id: str
    ws: WebSocket
    address: str
    held: dict[tuple[str, str], Combo] = field(default_factory=dict)


class RemoteHub:
    def __init__(
        self,
        controller: InputController,
        store: PanelStore,
        access_key: str,
        foreground: Callable[[], ForegroundInfo | None] = lambda: None,
        heartbeat_timeout: float = HEARTBEAT_TIMEOUT,
    ) -> None:
        self.controller = controller
        self.store = store
        self.access_key = access_key
        # Returns None where the foreground window cannot be inspected (not Windows).
        self.foreground = foreground
        self.heartbeat_timeout = heartbeat_timeout
        self.language: str | None = None
        self.connections: dict[str, Connection] = {}
        self.recent: deque[dict] = deque(maxlen=30)
        self._ids = itertools.count(1)
        self._taps: set[asyncio.Task] = set()

    # -- connection lifecycle -------------------------------------------------

    async def handle(self, ws: WebSocket) -> None:
        await ws.accept()
        conn = Connection(f"phone-{next(self._ids)}", ws, ws.client.host if ws.client else "?")
        try:
            hello = await self._receive(ws, HELLO_TIMEOUT)
            if hello.get("type") != "hello" or not key_matches(self.access_key, hello.get("key")):
                await ws.close(code=CLOSE_BAD_KEY)
                return
            self.connections[conn.id] = conn
            log.info("%s connected from %s", conn.id, conn.address)
            welcome = {"type": "welcome", "panels": self.store.public(), "language": self.language}
            await self._send(ws, welcome)
            while True:
                message = await self._receive(ws, self.heartbeat_timeout)
                await self._dispatch(conn, message)
        except TimeoutError:
            log.info("%s stopped responding", conn.id)
            await self._close(ws, CLOSE_TIMEOUT)
        except WebSocketDisconnect:
            pass
        except (ValueError, TypeError, KeyError) as exc:  # KeyError: a binary frame
            log.info("%s sent a bad message: %s", conn.id, exc)
            await self._close(ws, 1003)
        finally:
            if self.connections.pop(conn.id, None):
                log.info("%s disconnected", conn.id)
            self._release_connection(conn)

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

        reason = self._focus_problem(loaded.panel.window)
        if reason is None:
            combo = button.combo
            try:
                if button.type == "hold":
                    self.controller.hold(conn.id, combo)
                    conn.held[key] = combo
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
                "phone": conn.id,
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

    def _focus_problem(self, window: str | None) -> str | None:
        info = self.foreground()
        if info is None:
            return None
        if window and (info.exe_name or "").lower() != window.lower():
            return "not_focused"
        if input_blocked_by_elevation(info):
            return "elevated"
        return None
