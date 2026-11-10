"""Starts both servers in one process and opens the editor."""

from __future__ import annotations

import argparse
import asyncio
import logging
import webbrowser

import uvicorn

from game_remote.config import Settings
from game_remote.input import InputController
from game_remote.input.backend import default_backend
from game_remote.logging_setup import setup_logging
from game_remote.server.editor import create_editor_app
from game_remote.server.remote import create_remote_app

log = logging.getLogger("game_remote")


def _server(app, host: str, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host=host, port=port, log_config=None, access_log=False)
    return uvicorn.Server(config)


async def serve(settings: Settings) -> None:
    controller = InputController(default_backend())
    editor = _server(create_editor_app(settings), settings.editor_host, settings.editor_port)
    remote = _server(
        create_remote_app(settings, controller), settings.remote_host, settings.remote_port
    )

    async def open_editor_when_ready() -> None:
        while not editor.started:
            if editor.should_exit:
                return
            await asyncio.sleep(0.05)
        log.info("Editor: %s", settings.editor_url)
        if settings.open_browser:
            webbrowser.open(settings.editor_url)

    try:
        await asyncio.gather(editor.serve(), remote.serve(), open_editor_when_ready())
    finally:
        controller.release_all()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="game-remote")
    parser.add_argument("--no-browser", action="store_true", help="do not open the editor")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    settings = Settings(open_browser=not args.no_browser)
    settings.ensure_dirs()
    setup_logging(settings.log_dir)
    asyncio.run(serve(settings))


if __name__ == "__main__":
    main()
