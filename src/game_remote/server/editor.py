"""The editor app. Listens on 127.0.0.1 only and is used from the PC's browser."""

from __future__ import annotations

import io
import os
import sys

import segno
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from game_remote import __version__
from game_remote.netinfo import lan_addresses, local_name
from game_remote.state import AppState
from game_remote.web import web_dir


def allowed_hosts(port: int) -> set[str]:
    return {f"127.0.0.1:{port}", f"localhost:{port}"}


def phone_links(state: AppState) -> list[dict]:
    """Links for the QR code: one per network address, then the computer name."""
    links = [
        {"kind": "ip", "host": addr, "url": state.settings.remote_url(addr, state.access_key)}
        for addr in lan_addresses()
    ]
    name = local_name()
    if name:
        url = state.settings.remote_url(name, state.access_key)
        links.append({"kind": "name", "host": name, "url": url})
    return links


def create_editor_app(state: AppState) -> FastAPI:
    app = FastAPI(title="Game Remote editor", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.game_remote = state
    settings = state.settings
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
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-cache")
        return response

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "app": "editor", "version": __version__}

    @app.get("/api/status")
    async def status() -> dict:
        store, hub = state.store, state.hub
        return {
            "version": __version__,
            "phones": len(hub.connections),
            "recent": list(hub.recent),
            "panels": [
                {"id": p.id, "name": p.panel.name, "buttons": len(p.panel.buttons)}
                for p in store.panels.values()
            ],
            "panel_errors": store.errors,
            "panels_dir": str(store.root),
            "fake_input": state.fake_input,
            "held_keys": sorted(state.controller.held_keys),
        }

    @app.get("/api/links")
    async def links() -> dict:
        return {"links": [{"kind": x["kind"], "host": x["host"]} for x in phone_links(state)]}

    @app.get("/api/qr/{index}.svg")
    async def qr(index: int) -> Response:
        available = phone_links(state)
        if not 0 <= index < len(available):
            raise HTTPException(status_code=404)
        code = segno.make(available[index]["url"], error="m")
        out = io.BytesIO()
        code.save(out, kind="svg", scale=8, border=3, dark="#000", light="#fff")
        return Response(
            out.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"}
        )

    @app.post("/api/open-panels-folder")
    async def open_panels_folder() -> dict:
        if sys.platform != "win32":
            return {"ok": False, "path": str(state.store.root)}
        os.startfile(state.store.root)  # noqa: S606 - opens Explorer on the user's own folder
        return {"ok": True, "path": str(state.store.root)}

    @app.post("/api/release-keys")
    async def release_keys() -> dict:
        for conn in list(state.hub.connections.values()):
            conn.held.clear()
        state.controller.release_all()
        return {"ok": True}

    @app.post("/api/quit")
    async def quit_program() -> dict:
        if state.stop is None:
            return {"ok": False}
        state.stop()
        return {"ok": True}

    app.mount("/shared", StaticFiles(directory=web_dir("shared")), name="shared")
    app.mount("/", StaticFiles(directory=web_dir("editor"), html=True), name="editor")
    return app
