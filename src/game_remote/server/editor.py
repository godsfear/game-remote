"""The editor app. Listens on 127.0.0.1 only and is used from the PC's browser."""

from __future__ import annotations

import io
import os
import sys

import segno
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from game_remote import __version__
from game_remote.input.keys import MODIFIERS, SCAN_CODES, is_modifier, key_label
from game_remote.netinfo import lan_addresses, local_name
from game_remote.panels import Panel, short_error
from game_remote.state import AppState
from game_remote.web import web_dir

BODY = Body(...)


class NewPanel(BaseModel):
    name: str = Field(min_length=1, max_length=60)


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
            "revision": store.revision,
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

    # -- panels ------------------------------------------------------------------

    def panels_reply() -> dict:
        store = state.store
        return {
            "panels": [p.full() for p in store.panels.values()],
            "errors": store.errors,
            "revision": store.revision,
        }

    @app.get("/api/panels")
    async def list_panels() -> dict:
        return panels_reply()

    @app.get("/api/keys")
    async def keys() -> dict:
        """Every key a button can press, in keyboard order, with its short label."""
        return {
            "keys": [
                {"code": code, "label": key_label(code), "modifier": is_modifier(code)}
                for code in SCAN_CODES
            ],
            "modifiers": list(MODIFIERS),
        }

    @app.post("/api/panels", status_code=201)
    async def create_panel(body: NewPanel) -> dict:
        panel_id = state.store.create(body.name.strip() or "Panel")
        await state.hub.broadcast_panels()
        return {"id": panel_id, **panels_reply()}

    @app.put("/api/panels/{panel_id}")
    async def save_panel(panel_id: str, body: dict = BODY) -> Response:
        if not state.store.exists(panel_id):
            raise HTTPException(status_code=404)
        try:
            panel = Panel.model_validate(body)
        except ValidationError as exc:
            return JSONResponse({"error": short_error(exc)}, status_code=422)
        state.store.save(panel_id, panel)
        await state.hub.broadcast_panels()
        return JSONResponse({"ok": True, "revision": state.store.revision})

    @app.delete("/api/panels/{panel_id}")
    async def delete_panel(panel_id: str) -> dict:
        if not state.store.delete(panel_id):
            raise HTTPException(status_code=404)
        await state.hub.broadcast_panels()
        return {"ok": True, "revision": state.store.revision}

    @app.get("/panel-files/{panel_id}/{name}")
    async def panel_file(panel_id: str, name: str) -> FileResponse:
        loaded = state.store.get(panel_id)
        path = loaded.image_path(name) if loaded else None
        if path is None:
            raise HTTPException(status_code=404)
        return FileResponse(path, headers={"Cache-Control": "no-cache"})

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
