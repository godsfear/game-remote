"""The phone -> PC channel, driven through the remote app."""

import json

import pytest
from conftest import phone_key, wait_for
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from game_remote.hub import CLOSE_BAD_KEY, CLOSE_TIMEOUT
from game_remote.input import InputError
from game_remote.input.windows import ForegroundInfo
from game_remote.server.remote import create_remote_app

PHONE = ("192.168.1.50", 50000)


def client(state, address=PHONE):
    return TestClient(create_remote_app(state), client=address)


def connect(state, address=PHONE):
    return client(state, address).websocket_connect("/ws")


def hello(ws, state):
    ws.send_json({"type": "hello", "key": phone_key(state)})
    welcome = ws.receive_json()
    assert welcome["type"] == "welcome"
    return welcome


def press(ws, kind, button, panel="demo", message_id=1):
    ws.send_json({"type": kind, "id": message_id, "panel": panel, "button": button})
    return ws.receive_json()


def trace(state):
    return state.backend.trace()


def test_welcome_lists_panels_without_keys(state):
    with connect(state) as ws:
        welcome = hello(ws, state)
    assert [p["id"] for p in welcome["panels"]] == ["demo"]
    assert "KeyM" not in json.dumps(welcome)


@pytest.mark.parametrize(
    "first",
    [
        {"type": "hello", "key": "wrong"},
        {"type": "hello"},
        {"type": "down", "id": 1, "panel": "demo", "button": "map"},
    ],
)
def test_nothing_works_without_the_key(state, first):
    with connect(state) as ws:
        ws.send_json(first)
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    assert closed.value.code == CLOSE_BAD_KEY
    assert trace(state) == []
    assert state.hub.connections == {}


def test_connection_from_outside_the_home_network_is_refused(state):
    with pytest.raises(WebSocketDisconnect), connect(state, ("8.8.8.8", 4000)) as ws:
        ws.send_json({"type": "hello", "key": phone_key(state)})
        ws.receive_json()
    assert client(state, ("8.8.8.8", 4000)).get("/").status_code == 403
    assert client(state).get("/").status_code == 200


def test_tap_presses_and_releases(state):
    with connect(state) as ws:
        hello(ws, state)
        assert press(ws, "down", "map") == {"type": "ack", "id": 1, "ok": True}
        assert press(ws, "up", "map", message_id=2)["ok"]
        wait_for(lambda: trace(state) == ["+KeyM", "-KeyM"])
    assert state.hub.recent[0]["button"] and state.hub.recent[0]["ok"]


def test_hold_keeps_the_key_down_until_up(state):
    with connect(state) as ws:
        hello(ws, state)
        assert press(ws, "down", "forward")["ok"]
        assert press(ws, "down", "forward", message_id=2)["ok"]  # repeated down: no effect
        assert trace(state) == ["+KeyW"]
        assert state.controller.held_keys == {"KeyW"}
        assert press(ws, "up", "forward", message_id=3)["ok"]
        assert trace(state) == ["+KeyW", "-KeyW"]
        assert press(ws, "up", "forward", message_id=4)["ok"]  # repeated up: no effect
        assert trace(state) == ["+KeyW", "-KeyW"]


def test_two_fingers_hold_two_buttons(state):
    with connect(state) as ws:
        hello(ws, state)
        press(ws, "down", "forward")
        press(ws, "down", "run")
        assert state.controller.held_keys == {"KeyW", "ShiftLeft"}
        press(ws, "up", "forward")
        assert state.controller.held_keys == {"ShiftLeft"}
        press(ws, "up", "run")
    assert trace(state) == ["+KeyW", "+ShiftLeft", "-KeyW", "-ShiftLeft"]


def test_two_phones_holding_the_same_key(state):
    with connect(state) as first, connect(state, ("192.168.1.51", 50001)) as second:
        hello(first, state)
        hello(second, state)
        assert len(state.hub.connections) == 2
        press(first, "down", "forward")
        press(second, "down", "forward")
        press(first, "up", "forward")
        assert state.controller.held_keys == {"KeyW"}  # the second phone still holds it
        press(second, "up", "forward")
    assert trace(state) == ["+KeyW", "-KeyW"]


def test_keys_are_released_when_the_phone_disconnects(state):
    with connect(state) as ws:
        hello(ws, state)
        press(ws, "down", "forward")
        press(ws, "down", "run")
    wait_for(lambda: state.controller.held_keys == set())
    assert state.hub.connections == {}
    assert sorted(trace(state)[2:]) == ["-KeyW", "-ShiftLeft"]


def test_silent_phone_is_dropped_and_its_keys_released(state):
    state.hub.heartbeat_timeout = 0.2
    with connect(state) as ws:
        hello(ws, state)
        press(ws, "down", "forward")
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()  # no ping is sent, so the PC gives up
    assert closed.value.code == CLOSE_TIMEOUT
    assert trace(state) == ["+KeyW", "-KeyW"]


def test_ping_keeps_the_connection(state):
    with connect(state) as ws:
        hello(ws, state)
        ws.send_json({"type": "ping", "t": 12.5})
        assert ws.receive_json() == {"type": "pong", "t": 12.5}


@pytest.mark.parametrize(
    ("panel", "button"),
    [("demo", "nope"), ("nope", "map"), ("demo", None), (5, "map"), ("../demo", "map")],
)
def test_unknown_button_is_rejected(state, panel, button):
    with connect(state) as ws:
        hello(ws, state)
        ack = press(ws, "down", button, panel=panel)
    assert ack == {"type": "ack", "id": 1, "ok": False, "reason": "unknown_button"}
    assert trace(state) == []


def test_phone_cannot_send_its_own_keys(state):
    with connect(state) as ws:
        hello(ws, state)
        ws.send_json({"type": "down", "id": 1, "panel": "demo", "button": "map", "keys": "KeyQ"})
        assert ws.receive_json()["ok"]
        wait_for(lambda: len(trace(state)) == 2)
    assert trace(state) == ["+KeyM", "-KeyM"]


@pytest.mark.parametrize(
    "message", ["not json", "[1, 2]", '{"type": "format-disk"}', "x" * 5000, b"\x00\x01"]
)
def test_bad_messages_close_the_connection(state, message):
    with connect(state) as ws:
        hello(ws, state)
        press(ws, "down", "forward")
        if isinstance(message, bytes):
            ws.send_bytes(message)
        else:
            ws.send_text(message)
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
    assert trace(state) == ["+KeyW", "-KeyW"]


def foreground(exe, elevated=False):
    path = rf"C:\Games\{exe}"
    return lambda: ForegroundInfo(pid=1, exe_path=path, title="", elevated=elevated)


def test_press_is_rejected_when_another_window_has_focus(state, tmp_path):
    panel = tmp_path / "panels" / "demo" / "panel.json"
    data = json.loads(panel.read_text(encoding="utf-8"))
    data["window"] = "X4.exe"
    panel.write_text(json.dumps(data), encoding="utf-8")
    state.store.load()

    state.hub.foreground = foreground("chrome.exe")
    with connect(state) as ws:
        hello(ws, state)
        assert press(ws, "down", "map")["reason"] == "not_focused"
        assert press(ws, "down", "forward")["reason"] == "not_focused"
        assert trace(state) == []
        state.hub.foreground = foreground("x4.EXE")
        assert press(ws, "down", "forward")["ok"]
    assert state.hub.recent[-1]["reason"] == "not_focused"


def test_held_keys_are_released_when_another_window_becomes_active(state):
    def window(pid):
        return lambda: ForegroundInfo(pid=pid, exe_path=r"C:\x.exe", title="", elevated=False)

    state.hub.foreground = window(10)
    with connect(state) as ws:
        hello(ws, state)
        press(ws, "down", "forward")
        press(ws, "down", "run")
        assert state.hub.check_focus() == []  # still the same window
        state.hub.foreground = lambda: ForegroundInfo(None, None, "", None)
        assert state.hub.check_focus() == []  # between two windows: not known yet
        assert state.controller.held_keys == {"KeyW", "ShiftLeft"}

        state.hub.foreground = window(20)
        assert len(state.hub.check_focus()) == 1
        assert state.controller.held_keys == set()
        assert state.hub.check_focus() == []
        assert press(ws, "up", "forward")["ok"]  # the finger lifts later: nothing breaks
        assert press(ws, "down", "forward")["ok"]  # and a new hold works in the new window
        assert state.controller.held_keys == {"KeyW"}
        assert state.hub.check_focus() == []


def test_press_is_rejected_when_the_game_runs_as_administrator(state, monkeypatch):
    monkeypatch.setattr("game_remote.hub.input_blocked_by_elevation", lambda info: info.elevated)
    state.hub.foreground = foreground("Undecember.exe", elevated=True)
    with connect(state) as ws:
        hello(ws, state)
        assert press(ws, "down", "map")["reason"] == "elevated"
    assert trace(state) == []


def test_input_failure_is_reported(state, monkeypatch):
    def fail(events):
        raise InputError("blocked")

    monkeypatch.setattr(state.backend, "send", fail)
    with connect(state) as ws:
        hello(ws, state)
        assert press(ws, "down", "map")["reason"] == "input_error"
        assert press(ws, "down", "forward")["reason"] == "input_error"
        monkeypatch.undo()
        assert press(ws, "down", "forward")["ok"]


def test_panel_images_are_served_only_from_the_panel(state, tmp_path):
    folder = tmp_path / "panels" / "demo"
    data = json.loads((folder / "panel.json").read_text(encoding="utf-8"))
    data["buttons"][0]["image"] = "map.png"
    (folder / "panel.json").write_text(json.dumps(data), encoding="utf-8")
    (folder / "map.png").write_bytes(b"\x89PNG")
    state.store.load()
    http = client(state)
    assert http.get("/panel-files/demo/map.png").content == b"\x89PNG"
    assert http.get("/panel-files/demo/panel.json").status_code == 404
    assert http.get("/panel-files/demo/..%2F..%2Fgame-remote.sqlite3").status_code == 404
    assert http.get("/panel-files/nope/map.png").status_code == 404
