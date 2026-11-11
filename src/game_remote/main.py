"""Starts both servers in one process, shows the tray icon and opens the editor."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import socket
import sys
import time
import urllib.request
import webbrowser

import uvicorn

from game_remote.config import Settings
from game_remote.input import InputError
from game_remote.logging_setup import setup_logging
from game_remote.server.editor import create_editor_app
from game_remote.server.remote import create_remote_app
from game_remote.state import AppState, build_state
from game_remote.tray import start_tray

log = logging.getLogger("game_remote")

PANEL_WATCH_SECONDS = 1.0


def _server(app, host: str, port: int) -> uvicorn.Server:
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_config=None,
        access_log=False,
        ws="auto",
        timeout_graceful_shutdown=2,
    )
    return uvicorn.Server(config)


async def watch_panels(state: AppState) -> None:
    """Pick up edits of panel files and push them to the connected phones."""
    while True:
        await asyncio.sleep(PANEL_WATCH_SECONDS)
        try:
            if state.store.reload_if_changed():
                log.info("Panels reloaded: %s", ", ".join(state.store.panels) or "none")
                await state.hub.broadcast_panels()
        except Exception:
            log.exception("Could not reload the panels")


async def serve(state: AppState, tray: bool = False) -> None:
    settings = state.settings
    editor = _server(create_editor_app(state), settings.editor_host, settings.editor_port)
    remote = _server(create_remote_app(state), settings.remote_host, settings.remote_port)
    loop = asyncio.get_running_loop()

    def stop() -> None:
        editor.should_exit = True
        remote.should_exit = True

    state.stop = stop

    def open_editor() -> None:
        webbrowser.open(settings.editor_url)

    async def when_ready() -> None:
        while not (editor.started and remote.started):
            await asyncio.sleep(0.05)
        log.info("Editor: %s", settings.editor_url)
        log.info("Phone panel: port %s", settings.remote_port)
        if settings.open_browser:
            open_editor()

    icon = None
    if tray:
        quit_program = lambda: loop.call_soon_threadsafe(stop)  # noqa: E731
        icon = start_tray(open_editor, quit_program, state.user.forced_language)
    helpers = [
        asyncio.create_task(watch_panels(state)),
        asyncio.create_task(state.hub.watch_focus()),
        asyncio.create_task(when_ready()),
    ]
    try:
        # If one server stops (for example its port vanished), stop the other too.
        tasks = [asyncio.create_task(editor.serve()), asyncio.create_task(remote.serve())]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        stop()
        await asyncio.gather(*tasks)
    finally:
        state.stop = None
        for task in helpers:
            task.cancel()
        try:
            state.controller.release_all()
        except InputError:
            log.exception("Could not release every key on exit")
        if icon is not None:
            with contextlib.suppress(Exception):
                icon.stop()


def already_running(settings: Settings) -> bool:
    """True if another Game Remote already answers on the editor port."""
    # No proxy: the request must reach this PC, not a proxy set in the system.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(settings.editor_url + "api/health", timeout=1) as response:
            return json.load(response).get("app") == "editor"
    except (OSError, ValueError):
        return False


def busy_port(settings: Settings) -> int | None:
    for host, port in (
        (settings.editor_host, settings.editor_port),
        (settings.remote_host, settings.remote_port),
    ):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if sys.platform != "win32":
                # Same option as the server uses; without it a port whose old
                # connections are still closing looks busy. On Windows the
                # option means something else and would hide a real conflict.
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
            except OSError:
                return port
    return None


def wait_for_ports(settings: Settings, seconds: float = 4.0) -> int | None:
    """A copy that was just closed needs a moment to let go of its ports."""
    deadline = time.monotonic() + seconds
    while True:
        port = busy_port(settings)
        if port is None or time.monotonic() >= deadline:
            return port
        time.sleep(0.25)


def show_error(text: str) -> None:
    log.error(text)
    if sys.platform == "win32":  # the exe has no console, so say it in a window
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, "Game Remote", 0x10)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="game-remote")
    parser.add_argument("--no-browser", action="store_true", help="do not open the editor")
    parser.add_argument("--no-tray", action="store_true", help="do not show the tray icon")
    parser.add_argument(
        "--fake-input",
        action="store_true",
        help="record key presses instead of sending them to Windows",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = Settings(open_browser=not args.no_browser)
    settings.ensure_dirs()
    setup_logging(settings.log_dir)

    if already_running(settings):
        log.info("Game Remote is already running; opening its editor")
        if settings.open_browser:
            webbrowser.open(settings.editor_url)
        return 0
    port = wait_for_ports(settings)
    if port is not None and already_running(settings):  # a copy that was still starting
        return 0
    if port is not None:
        show_error(
            f"Port {port} is used by another program, so Game Remote cannot start.\n"
            f"Порт {port} занят другой программой, поэтому Game Remote не может запуститься."
        )
        return 1

    state = build_state(settings, fake_input=args.fake_input)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(serve(state, tray=not args.no_tray))
    return 0


if __name__ == "__main__":
    sys.exit(main())
