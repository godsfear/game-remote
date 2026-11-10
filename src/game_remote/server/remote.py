"""The phone panel app. Listens on the home network."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from game_remote import __version__
from game_remote.config import Settings
from game_remote.input import InputController
from game_remote.web import web_dir


def create_remote_app(settings: Settings, controller: InputController) -> FastAPI:
    app = FastAPI(title="Game Remote panel", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.controller = controller

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "app": "remote", "version": __version__}

    # The panel and its WebSocket channel arrive in milestone 1, pairing in milestone 3.
    app.mount("/", StaticFiles(directory=web_dir("remote"), html=True), name="remote")
    return app
