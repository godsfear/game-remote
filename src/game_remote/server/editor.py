"""The editor app. Listens on 127.0.0.1 only and is used from the PC's browser."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from game_remote import __version__
from game_remote.config import Settings
from game_remote.web import web_dir


def allowed_hosts(port: int) -> set[str]:
    return {f"127.0.0.1:{port}", f"localhost:{port}"}


def create_editor_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Game Remote editor", docs_url=None, redoc_url=None, openapi_url=None)
    hosts = allowed_hosts(settings.editor_port)
    origins = {f"http://{h}" for h in hosts}

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        # Blocks DNS rebinding (foreign Host header) and cross-site writes
        # from other pages open in the same browser (foreign Origin).
        if request.headers.get("host", "") not in hosts:
            return JSONResponse({"error": "forbidden_host"}, status_code=403)
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin not in origins:
            return JSONResponse({"error": "forbidden_origin"}, status_code=403)
        return await call_next(request)

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "app": "editor", "version": __version__}

    app.mount("/", StaticFiles(directory=web_dir("editor"), html=True), name="editor")
    return app
