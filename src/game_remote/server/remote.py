"""The phone panel app. Listens on the home network."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from game_remote import __version__
from game_remote.netinfo import is_local_client
from game_remote.state import AppState
from game_remote.web import web_dir

NO_CACHE = {"Cache-Control": "no-cache"}


def create_remote_app(state: AppState) -> FastAPI:
    app = FastAPI(title="Game Remote panel", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.game_remote = state

    @app.middleware("http")
    async def home_network_only(request: Request, call_next):
        if not is_local_client(request.client.host if request.client else None):
            return JSONResponse({"error": "not_local"}, status_code=403)
        response = await call_next(request)
        # The page is tiny and changes with every build; never serve a stale copy.
        response.headers.setdefault("Cache-Control", "no-cache")
        return response

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "app": "remote", "version": __version__}

    @app.get("/panel-files/{panel_id}/{name}")
    async def panel_file(panel_id: str, name: str) -> FileResponse:
        loaded = state.store.get(panel_id)
        path = loaded.image_path(name) if loaded else None
        if path is None:
            raise HTTPException(status_code=404)
        return FileResponse(path, headers=NO_CACHE)

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        if not is_local_client(ws.client.host if ws.client else None):
            await ws.close(code=1008)
            return
        await state.hub.handle(ws)

    app.mount("/shared", StaticFiles(directory=web_dir("shared")), name="shared")
    app.mount("/", StaticFiles(directory=web_dir("remote"), html=True), name="remote")
    return app
