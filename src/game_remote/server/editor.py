"""The editor app. Listens on 127.0.0.1 only and is used from the PC's browser."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import sys

import segno
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from game_remote import __version__
from game_remote.input import InputError
from game_remote.input.keys import MODIFIERS, SCAN_CODES, is_modifier, key_label
from game_remote.netinfo import lan_addresses, local_name
from game_remote.panels import (
    MAX_IMAGE_BYTES,
    MAX_SET_BYTES,
    ImageError,
    Panel,
    pack_set,
    short_error,
)
from game_remote.state import AppState
from game_remote.user_settings import Language, save_user_settings
from game_remote.web import web_dir

log = logging.getLogger(__name__)

BODY = Body(...)
# The language the texts of an exported game are in, e.g. "ru".
LANGUAGE = Query(default=None, pattern="^[a-z]{2}$")
# The languages the user reads, best first, e.g. "de,en". A browser may name none.
LANGUAGES = Query(default=None, pattern="^([a-z]{2}(,[a-z]{2}){0,9})?$")


class NewPanel(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class LanguageChoice(BaseModel):
    language: Language = "auto"


class DeviceName(BaseModel):
    name: str = Field(min_length=1, max_length=200)


async def body_within(request: Request, limit: int) -> bytes | None:
    """The body of the request, or None once it is larger than ``limit``. It is
    counted while it arrives: the size a request declares can be absent or wrong."""
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def allowed_hosts(port: int) -> set[str]:
    return {f"127.0.0.1:{port}", f"localhost:{port}"}


def phone_links(state: AppState) -> list[dict]:
    """Links for the QR code: one per network address, then the computer name.
    All of them carry the pairing code that is valid right now."""
    code = state.pairing.current()
    links = [
        {"kind": "ip", "host": addr, "url": state.settings.remote_url(addr, code)}
        for addr in lan_addresses()
    ]
    name = local_name()
    if name:
        links.append({"kind": "name", "host": name, "url": state.settings.remote_url(name, code)})
    return links


def device_list(state: AppState) -> list[dict]:
    online = state.hub.online_devices()
    return [{**d.as_dict(), "online": d.id in online} for d in state.devices.all()]


def _pairing_serial(state: AppState) -> int:
    state.pairing.current()
    return state.pairing.serial


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
            "devices": device_list(state),
            # Changes when the code inside the QR link does: the page redraws the QR code.
            "pairing": _pairing_serial(state),
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
        # Only pages of this editor can read the reply (see local_only above),
        # so it may carry the links with the pairing code.
        return {"links": phone_links(state), "pairing": state.pairing.serial}

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

    # -- paired devices ----------------------------------------------------------

    @app.put("/api/devices/{device_id}")
    async def rename_device(device_id: str, body: DeviceName) -> dict:
        if state.devices.get(device_id) is None:
            raise HTTPException(status_code=404)
        device = state.devices.rename(device_id, body.name)
        if device is None:
            raise HTTPException(status_code=422)
        state.hub.rename_device(device)
        return {"devices": device_list(state)}

    @app.delete("/api/devices/{device_id}")
    async def remove_device(device_id: str) -> dict:
        """Forgets the device: its key stops working and its connection closes."""
        if not state.devices.remove(device_id):
            raise HTTPException(status_code=404)
        await state.hub.drop_device(device_id)
        return {"devices": device_list(state)}

    @app.get("/api/windows")
    async def windows() -> dict:
        """Programs with an open window, to bind a panel to a game."""
        found = state.windows()
        return {
            "supported": state.fake_input or sys.platform == "win32",
            "windows": [
                {"exe": w.exe_name, "title": w.title, "elevated": w.elevated is True} for w in found
            ],
        }

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

    @app.post("/api/panels/{panel_id}/images", status_code=201)
    async def upload_image(panel_id: str, request: Request) -> Response:
        """The body is the picture itself. The page shrinks it before sending."""
        data = await body_within(request, MAX_IMAGE_BYTES)
        if data is None:
            return JSONResponse({"error": "too_large"}, status_code=413)
        try:
            name = state.store.add_image(panel_id, data)
        except KeyError:
            raise HTTPException(status_code=404) from None
        except ImageError as exc:
            status = 413 if str(exc) == "too_large" else 415
            return JSONResponse({"error": str(exc)}, status_code=status)
        return JSONResponse({"name": name}, status_code=201)

    # -- sets: a game as a file to share ------------------------------------------

    @app.get("/api/panels/{panel_id}/export")
    async def export_set(panel_id: str, language: str | None = LANGUAGE) -> Response:
        """The game as a zip. ``language`` is what its texts are written in."""
        loaded = state.store.get(panel_id)
        if loaded is None:
            raise HTTPException(status_code=404)
        # In a thread, like the import below: the phones are served by the same loop.
        return Response(
            await asyncio.to_thread(pack_set, loaded, language),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{panel_id}.zip"'},
        )

    @app.post("/api/sets", status_code=201)
    async def import_set(request: Request, languages: str | None = LANGUAGES) -> Response:
        """The body is the zip of a set. It becomes a new game in the first of
        ``languages`` the set has."""
        data = await body_within(request, MAX_SET_BYTES)
        if data is None:
            return JSONResponse({"error": "the file is too large"}, status_code=413)
        wanted = languages.split(",") if languages else []
        try:
            # Unpacking takes a while for a large set; a thread keeps the phones served.
            panel_id = await asyncio.to_thread(state.store.import_set, data, *wanted)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)
        except OSError as exc:
            log.exception("Could not write the imported set")
            reason = exc.strerror or str(exc)
            return JSONResponse({"error": f"the game was not written: {reason}"}, status_code=500)
        await state.hub.broadcast_panels()
        return JSONResponse({"id": panel_id, **panels_reply()}, status_code=201)

    @app.get("/api/settings")
    async def get_settings() -> dict:
        return {"language": state.user.language}

    @app.put("/api/settings")
    async def put_settings(body: LanguageChoice) -> dict:
        # Only the language is the page's to change; the rest of the file stays.
        state.user = state.user.model_copy(update={"language": body.language})
        save_user_settings(settings.user_settings_path, state.user)
        await state.hub.set_language(state.user.forced_language)
        return {"language": state.user.language}

    @app.get("/panel-files/{panel_id}/{name}")
    async def panel_file(panel_id: str, name: str) -> FileResponse:
        loaded = state.store.get(panel_id)
        path = loaded.image_path(name, used_only=False) if loaded else None
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
        try:
            state.controller.release_all()
        except InputError:
            log.exception("Could not release every key")
            return {"ok": False}
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
