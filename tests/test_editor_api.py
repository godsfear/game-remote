"""The editor's API for games and buttons."""

import json

import pytest
from fastapi.testclient import TestClient

from game_remote.panels import PanelStore
from game_remote.server.editor import create_editor_app
from game_remote.server.remote import create_remote_app

EDITOR = "http://127.0.0.1:8730"
ORIGIN = {"origin": EDITOR}

X4 = {
    "name": "X4: Foundations",
    "columns": 2,
    "buttons": [
        {"id": "map", "label": "Карта", "keys": "KeyM"},
        {"id": "radio", "label": "Связь", "keys": "KeyR+ControlLeft", "type": "hold"},
    ],
}


@pytest.fixture
def client(state):
    return TestClient(create_editor_app(state), base_url=EDITOR)


def panel_file(state, panel_id):
    return state.settings.panels_dir / panel_id / "panel.json"


def test_panels_are_listed_with_their_keys(client):
    data = client.get("/api/panels").json()
    assert [p["id"] for p in data["panels"]] == ["demo"]
    assert data["panels"][0]["buttons"][0]["keys"] == "KeyM"
    assert data["errors"] == {}
    assert data["revision"] == client.get("/api/status").json()["revision"]


def test_key_list_for_the_manual_choice(client):
    data = client.get("/api/keys").json()
    by_code = {key["code"]: key for key in data["keys"]}
    assert by_code["KeyM"] == {"code": "KeyM", "label": "M", "modifier": False}
    assert by_code["ControlLeft"]["modifier"] is True
    assert data["modifiers"][0] == "ControlLeft"


def test_create_a_game(client, state):
    created = client.post("/api/panels", json={"name": "X4: Foundations"}, headers=ORIGIN)
    assert created.status_code == 201
    data = created.json()
    assert data["id"] == "x4-foundations"
    assert [p["id"] for p in data["panels"]] == ["demo", "x4-foundations"]
    assert json.loads(panel_file(state, "x4-foundations").read_text(encoding="utf-8"))["name"] == (
        "X4: Foundations"
    )


def test_game_ids_do_not_collide(client):
    ids = [
        client.post("/api/panels", json={"name": name}, headers=ORIGIN).json()["id"]
        for name in ("Новая игра", "Новая игра", "demo", "a" * 60)
    ]
    assert ids == ["game", "game-2", "demo-2", "a" * 30]


@pytest.mark.parametrize("body", [{}, {"name": ""}, {"name": "x" * 61}])
def test_a_game_needs_a_sane_name(client, body):
    assert client.post("/api/panels", json=body, headers=ORIGIN).status_code == 422


def test_save_writes_the_file_and_normalises_keys(client, state):
    before = client.get("/api/panels").json()["revision"]
    saved = client.put("/api/panels/demo", json=X4, headers=ORIGIN)
    assert saved.status_code == 200
    assert saved.json()["revision"] > before
    on_disk = json.loads(panel_file(state, "demo").read_text(encoding="utf-8"))
    assert on_disk["name"] == "X4: Foundations"
    assert on_disk["buttons"][1]["keys"] == "ControlLeft+KeyR"
    assert state.store.get("demo").panel.columns == 2
    assert not (state.settings.panels_dir / "demo" / "panel.json.tmp").exists()


def test_the_page_does_not_reload_after_its_own_save(client, state):
    revision = client.put("/api/panels/demo", json=X4, headers=ORIGIN).json()["revision"]
    assert not state.store.reload_if_changed()  # the watcher sees nothing new
    assert client.get("/api/status").json()["revision"] == revision


def test_bad_panel_is_refused_and_the_file_stays(client, state):
    before = panel_file(state, "demo").read_text(encoding="utf-8")
    bad = dict(X4, buttons=[{"id": "a", "keys": "NoSuchKey"}])
    reply = client.put("/api/panels/demo", json=bad, headers=ORIGIN)
    assert reply.status_code == 422
    assert "buttons.0.keys" in reply.json()["error"]
    assert panel_file(state, "demo").read_text(encoding="utf-8") == before


@pytest.mark.parametrize("panel_id", ["nope", "bad id", "..", "demo.json"])
def test_save_cannot_create_or_escape(client, state, panel_id):
    # ".." never reaches the handler: the URL is normalised to another route.
    reply = client.put(f"/api/panels/{panel_id}", json=X4, headers=ORIGIN)
    assert reply.status_code in (404, 405)
    assert sorted(p.name for p in state.settings.panels_dir.iterdir()) == ["demo"]


def test_a_broken_file_can_be_fixed_from_the_editor(client, state):
    panel_file(state, "demo").write_text("{ broken", encoding="utf-8")
    state.store.load()
    assert "demo" in client.get("/api/panels").json()["errors"]
    assert client.put("/api/panels/demo", json=X4, headers=ORIGIN).status_code == 200
    assert client.get("/api/panels").json()["errors"] == {}


def test_delete_moves_the_game_to_the_trash(client, state):
    client.post("/api/panels", json={"name": "X4"}, headers=ORIGIN)
    assert client.delete("/api/panels/x4", headers=ORIGIN).json()["ok"]
    assert [p["id"] for p in client.get("/api/panels").json()["panels"]] == ["demo"]
    kept = list(state.settings.trash_dir.iterdir())
    assert len(kept) == 1 and kept[0].name.startswith("x4-")
    assert (kept[0] / "panel.json").is_file()
    assert client.delete("/api/panels/x4", headers=ORIGIN).status_code == 404


def test_deleting_the_same_name_twice_keeps_both_copies(tmp_path):
    store = PanelStore(tmp_path / "panels", tmp_path / "trash")
    for _ in range(2):
        store.create("X4")
        assert store.delete("x4")
    assert len(list((tmp_path / "trash").iterdir())) == 2
    assert not store.delete("x4")


def test_changes_need_the_editors_origin(client):
    for method, path in (("post", "/api/panels"), ("put", "/api/panels/demo")):
        call = getattr(client, method)
        assert call(path, json=X4).status_code == 403
        assert call(path, json=X4, headers={"origin": "http://evil.example"}).status_code == 403
    assert client.delete("/api/panels/demo").status_code == 403


def test_the_phone_has_no_editor_api(state):
    phone = TestClient(create_remote_app(state), client=("192.168.1.50", 50000))
    assert phone.get("/api/panels").status_code == 404
    assert phone.get("/api/keys").status_code == 404
    assert phone.put("/api/panels/demo", json=X4).status_code in (404, 405)
    assert phone.delete("/api/panels/demo").status_code in (404, 405)


def test_an_edit_reaches_the_phone_and_releases_its_keys(client, state):
    phone = TestClient(create_remote_app(state), client=("192.168.1.50", 50000))
    with phone.websocket_connect("/ws") as ws:
        ws.send_json({"type": "hello", "key": state.access_key})
        ws.receive_json()
        ws.send_json({"type": "down", "id": 1, "panel": "demo", "button": "forward"})
        assert ws.receive_json()["ok"]
        assert state.controller.held_keys == {"KeyW"}

        client.put("/api/panels/demo", json=X4, headers=ORIGIN)
        pushed = ws.receive_json()
        assert pushed["type"] == "panels"
        assert pushed["panels"][0]["name"] == "X4: Foundations"
        assert "KeyM" not in json.dumps(pushed)
        assert state.controller.held_keys == set()

        client.post("/api/panels", json={"name": "Second"}, headers=ORIGIN)
        assert len(ws.receive_json()["panels"]) == 2
        client.delete("/api/panels/second", headers=ORIGIN)
        assert len(ws.receive_json()["panels"]) == 1


def test_editor_serves_panel_images_for_the_preview(client, state):
    folder = state.settings.panels_dir / "demo"
    data = json.loads((folder / "panel.json").read_text(encoding="utf-8"))
    data["buttons"][0]["image"] = "map.png"
    (folder / "map.png").write_bytes(b"\x89PNG")
    assert client.put("/api/panels/demo", json=data, headers=ORIGIN).status_code == 200
    assert client.get("/panel-files/demo/map.png").content == b"\x89PNG"
    assert client.get("/panel-files/demo/panel.json").status_code == 404
