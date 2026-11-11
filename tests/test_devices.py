"""Pairing by one-time code, the list of devices and the window choice."""

import sqlite3

import pytest
from conftest import phone_key, wait_for
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from game_remote.config import Settings
from game_remote.devices import DeviceStore, clean_name
from game_remote.hub import CLOSE_BAD_CODE, CLOSE_BAD_KEY
from game_remote.input.windows import OpenWindow, open_windows
from game_remote.server.editor import create_editor_app
from game_remote.server.remote import create_remote_app
from game_remote.state import build_state

PHONE = ("192.168.1.50", 50000)
EDITOR = "http://127.0.0.1:8730"
ORIGIN = {"origin": EDITOR}


@pytest.fixture
def editor(state):
    return TestClient(create_editor_app(state), base_url=EDITOR)


def phone(state):
    return TestClient(create_remote_app(state), client=PHONE).websocket_connect("/ws")


def pair(ws, state, name="Pixel 7"):
    ws.send_json({"type": "pair", "code": state.pairing.current(), "name": name})
    paired = ws.receive_json()
    assert paired["type"] == "paired"
    assert ws.receive_json()["type"] == "welcome"
    return paired["key"]


# -- the store ------------------------------------------------------------------


def test_store_keeps_devices_between_runs(tmp_path):
    path = tmp_path / "devices.sqlite3"
    store = DeviceStore(path)
    device, key = store.add("Pixel 7")
    assert store.find(key) == device
    assert store.find("other") is None and store.find(None) is None and store.find("") is None
    store.close()

    again = DeviceStore(path)
    assert again.find(key).name == "Pixel 7"
    assert [d.id for d in again.all()] == [device.id]
    again.close()
    assert key.encode() not in path.read_bytes()


def test_names_are_cleaned_and_kept_apart(tmp_path):
    store = DeviceStore(tmp_path / "d.sqlite3")
    names = [store.add(name)[0].name for name in ("Pixel 7", "Pixel 7", " Pixel\n7 ", "", None)]
    assert names == ["Pixel 7", "Pixel 7 (2)", "Pixel 7 (3)", "Phone", "Phone (2)"]
    assert clean_name("x" * 100) == "x" * 40
    assert clean_name("a\x00b\tc") == "a b c"
    store.close()


def test_rename_touch_and_remove(tmp_path):
    store = DeviceStore(tmp_path / "d.sqlite3")
    device, key = store.add("Tablet")
    assert store.rename(device.id, "  Планшет в гостиной ").name == "Планшет в гостиной"
    assert store.rename(device.id, "  ") is None
    assert store.rename("nope", "x") is None
    store.touch(device.id)
    assert store.get(device.id).last_seen >= device.last_seen
    assert store.remove(device.id)
    assert not store.remove(device.id)
    assert store.find(key) is None
    store.close()


def test_unreadable_database_is_put_aside(tmp_path):
    settings = Settings(data_dir=tmp_path, open_browser=False)
    settings.db_path.write_bytes(b"this is not a database, " * 200)
    state = build_state(settings, fake_input=True)
    assert state.devices.all() == []
    assert (tmp_path / "game-remote.sqlite3.broken").is_file()
    state.devices.close()
    with sqlite3.connect(settings.db_path) as db:
        assert db.execute("SELECT count(*) FROM devices").fetchone() == (0,)
    db.close()


def test_old_shared_key_is_dropped_at_start(tmp_path):
    (tmp_path / "access.key").write_text("old-secret-of-the-prototype\n", encoding="ascii")
    state = build_state(Settings(data_dir=tmp_path, open_browser=False), fake_input=True)
    assert not (tmp_path / "access.key").exists()
    with phone(state) as ws:
        ws.send_json({"type": "hello", "key": "old-secret-of-the-prototype"})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == CLOSE_BAD_KEY
    state.devices.close()


# -- pairing --------------------------------------------------------------------


def test_pairing_gives_the_phone_its_own_key(state):
    with phone(state) as ws:
        key = pair(ws, state)
        ws.send_json({"type": "down", "id": 1, "panel": "demo", "button": "forward"})
        assert ws.receive_json()["ok"]
    [device] = state.devices.all()
    assert device.name == "Pixel 7"
    assert state.hub.recent[0]["phone"] == "Pixel 7"

    with phone(state) as ws:  # the next visit needs no code
        ws.send_json({"type": "hello", "key": key})
        assert ws.receive_json()["type"] == "welcome"
    assert len(state.devices.all()) == 1


def test_a_code_pairs_only_one_phone(state):
    code = state.pairing.current()
    with phone(state) as ws:
        pair(ws, state)
    with phone(state) as ws:
        ws.send_json({"type": "pair", "code": code, "name": "Stranger"})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == CLOSE_BAD_CODE
    assert [d.name for d in state.devices.all()] == ["Pixel 7"]
    assert state.pairing.current() != code


@pytest.mark.parametrize("code", ["wrong", "", None, 12345])
def test_a_wrong_code_pairs_nobody(state, code):
    state.pairing.current()
    with phone(state) as ws:
        ws.send_json({"type": "pair", "code": code})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == CLOSE_BAD_CODE
    assert state.devices.all() == []
    assert state.hub.connections == {}


def test_the_pairing_code_is_not_a_key(state):
    with phone(state) as ws:
        ws.send_json({"type": "hello", "key": state.pairing.current()})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == CLOSE_BAD_KEY


# -- the list on the PC ---------------------------------------------------------


def test_status_lists_devices_and_who_is_online(state, editor):
    with phone(state) as ws:
        pair(ws, state, "Pixel 7")
        offline_key = phone_key(state, "Old tablet")
        status = editor.get("/api/status").json()
        assert [(d["name"], d["online"]) for d in status["devices"]] == [
            ("Pixel 7", True),
            ("Old tablet", False),
        ]
        assert status["phones"] == 1
        assert offline_key not in editor.get("/api/status").text
    wait_for(lambda: not editor.get("/api/status").json()["devices"][0]["online"])


def test_pairing_changes_the_qr_code(state, editor):
    before = editor.get("/api/status").json()["pairing"]
    picture = editor.get("/api/links").json()
    assert picture["pairing"] == before
    with phone(state) as ws:
        pair(ws, state)
    assert editor.get("/api/status").json()["pairing"] == before + 1
    assert editor.get("/api/links").json()["links"] != picture["links"] or not picture["links"]


def test_rename_a_device(state, editor):
    with phone(state) as ws:
        pair(ws, state)
        [device] = state.devices.all()
        reply = editor.put(
            f"/api/devices/{device.id}", json={"name": " Мой телефон "}, headers=ORIGIN
        )
        assert reply.json()["devices"][0]["name"] == "Мой телефон"
        ws.send_json({"type": "down", "id": 1, "panel": "demo", "button": "map"})
        ws.receive_json()
        assert state.hub.recent[0]["phone"] == "Мой телефон"
    assert editor.put("/api/devices/nope", json={"name": "x"}, headers=ORIGIN).status_code == 404
    assert (
        editor.put(f"/api/devices/{device.id}", json={"name": "  "}, headers=ORIGIN).status_code
        == 422
    )
    assert editor.put(f"/api/devices/{device.id}", json={"name": "x"}).status_code == 403


def test_removing_a_device_disconnects_it_for_good(state, editor):
    with phone(state) as ws:
        key = pair(ws, state)
        ws.send_json({"type": "down", "id": 1, "panel": "demo", "button": "forward"})
        ws.receive_json()
        assert state.controller.held_keys == {"KeyW"}
        [device] = state.devices.all()

        assert editor.delete(f"/api/devices/{device.id}").status_code == 403  # no Origin
        reply = editor.delete(f"/api/devices/{device.id}", headers=ORIGIN)
        assert reply.json() == {"devices": []}
        assert state.controller.held_keys == set()
        assert state.hub.connections == {}
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert closed.value.code == CLOSE_BAD_KEY

    with phone(state) as ws:
        ws.send_json({"type": "hello", "key": key})
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == CLOSE_BAD_KEY
    assert editor.delete(f"/api/devices/{device.id}", headers=ORIGIN).status_code == 404


def test_the_phone_side_has_no_device_api(state):
    client = TestClient(create_remote_app(state), client=PHONE)
    device, _ = state.devices.add("Pixel")
    assert client.get("/api/windows").status_code == 404
    assert client.delete(f"/api/devices/{device.id}").status_code in (404, 405)
    assert len(state.devices.all()) == 1


# -- windows --------------------------------------------------------------------


def test_window_list_for_binding_a_panel(state, editor):
    state.windows = lambda: [
        OpenWindow(exe_name="X4.exe", title="X4", elevated=False),
        OpenWindow(exe_name="Undecember.exe", title="Undecember", elevated=True),
        OpenWindow(exe_name="mystery.exe", title="?", elevated=None),
    ]
    assert editor.get("/api/windows").json() == {
        "supported": True,
        "windows": [
            {"exe": "X4.exe", "title": "X4", "elevated": False},
            {"exe": "Undecember.exe", "title": "Undecember", "elevated": True},
            {"exe": "mystery.exe", "title": "?", "elevated": False},
        ],
    }


def test_open_windows_does_not_crash():
    found = open_windows()
    assert isinstance(found, list)
    for window in found:
        assert window.exe_name and window.title
    assert len({w.exe_name.lower() for w in found}) == len(found)
