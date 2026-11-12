"""The phone -> PC channel, driven through the remote app."""

import asyncio
import json
import time
from types import SimpleNamespace

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


def add_toggles(state, tmp_path, **panel_fields):
    """Two toggles join the demo panel: "lights" starts off, "gear" starts on."""
    panel = tmp_path / "panels" / "demo" / "panel.json"
    data = json.loads(panel.read_text(encoding="utf-8"))
    data["buttons"] = [button for button in data["buttons"] if button.get("type") != "toggle"]
    data["buttons"] += [
        {"id": "lights", "keys": "KeyL", "type": "toggle"},
        {"id": "gear", "keys": "KeyN", "type": "toggle", "on": True},
    ]
    panel.write_text(json.dumps({**data, **panel_fields}), encoding="utf-8")
    state.store.load()


def toggles(panels):
    return {b["id"]: b["on"] for b in panels[0]["buttons"] if b["type"] == "toggle"}


def lit(button, on):
    return {"type": "lit", "panel": "demo", "button": button, "on": on}


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


def test_a_toggle_is_lit_by_a_press_and_every_phone_shows_it(state, tmp_path):
    add_toggles(state, tmp_path)
    with connect(state) as ws, connect(state, ("192.168.1.51", 50001)) as second:
        assert toggles(hello(ws, state)["panels"]) == {"lights": False, "gear": True}
        hello(second, state)
        # The key is tapped like any other, and both phones learn the new state.
        assert press(ws, "down", "lights") == lit("lights", True)
        assert ws.receive_json() == {"type": "ack", "id": 1, "ok": True}
        assert second.receive_json() == lit("lights", True)
        wait_for(lambda: trace(state) == ["+KeyL", "-KeyL"])
        # A toggle that starts on goes off with its first press.
        assert press(second, "down", "gear") == lit("gear", False)
        assert ws.receive_json() == lit("gear", False)
    # The PC keeps the state: a phone that connects later gets it.
    with connect(state) as later:
        assert toggles(hello(later, state)["panels"]) == {"lights": True, "gear": False}
        assert press(later, "down", "lights") == lit("lights", False)


def test_a_long_touch_sets_the_light_right_without_a_key(state, tmp_path):
    add_toggles(state, tmp_path, window="X4.exe")
    state.hub.foreground = foreground("chrome.exe")  # the game is not even in front
    with connect(state) as ws:
        hello(ws, state)
        assert press(ws, "flip", "lights") == lit("lights", True)
        assert ws.receive_json() == {"type": "ack", "id": 1, "ok": True}
        # Only a toggle has a light to set.
        assert press(ws, "flip", "map", message_id=2)["reason"] == "unknown_button"
        assert press(ws, "flip", "nothing", message_id=3)["reason"] == "unknown_button"
    assert trace(state) == [] and len(state.hub.recent) == 0


def test_a_press_that_was_rejected_leaves_the_light_as_it_was(state, tmp_path):
    add_toggles(state, tmp_path, window="X4.exe")
    state.hub.foreground = foreground("chrome.exe")
    with connect(state) as ws:
        hello(ws, state)
        assert press(ws, "down", "lights")["reason"] == "not_focused"
    assert toggles(state.hub.panels()) == {"lights": False, "gear": True}


def test_a_toggle_changed_in_the_editor_shows_what_the_editor_says(state, tmp_path):
    add_toggles(state, tmp_path)
    with connect(state) as ws:
        hello(ws, state)
        press(ws, "down", "lights")
        ws.receive_json()
        press(ws, "down", "lights", message_id=2)  # on and off again
        ws.receive_json()
    assert toggles(state.hub.panels())["lights"] is False
    # The editor now says that it starts on: the count of presses begins anew.
    panel = tmp_path / "panels" / "demo" / "panel.json"
    data = json.loads(panel.read_text(encoding="utf-8"))
    data["buttons"][-2]["on"] = True
    panel.write_text(json.dumps(data), encoding="utf-8")
    state.store.load()
    assert toggles(state.hub.panels()) == {"lights": True, "gear": True}


def test_two_presses_at_once_leave_every_phone_with_the_state_of_the_pc(state, tmp_path):
    add_toggles(state, tmp_path)
    hub = state.hub
    hub.connections = {name: SimpleNamespace(ws=name) for name in ("near", "far")}
    heard = {"near": [], "far": []}

    async def send(ws, message):
        # The first news is slow on its way to the far phone: the second overtakes it.
        await asyncio.sleep(0.05 if ws == "far" and message["on"] and not heard["far"] else 0)
        heard[ws].append(message["on"])

    hub._send = send
    key, button = ("demo", "lights"), state.store.get("demo").panel.button("lights")

    async def scenario():
        await asyncio.gather(hub._flip(key, button), hub._flip(key, button))

    asyncio.run(scenario())
    assert heard["far"][:2] == [False, True]  # the news did arrive in the wrong order
    assert heard["near"][-1] is heard["far"][-1] is toggles(hub.panels())["lights"] is False


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


def test_the_phones_are_told_which_game_has_the_active_window(state, tmp_path):
    panel = tmp_path / "panels" / "demo" / "panel.json"
    data = json.loads(panel.read_text(encoding="utf-8"))
    panel.write_text(json.dumps(data | {"window": "X4.exe"}), encoding="utf-8")
    hub = state.hub

    def unknown():
        return ForegroundInfo(None, None, "", None)

    # No panel is bound to a window yet: the active one is not even asked about.
    hub.foreground = None
    with connect(state) as ws:
        assert hello(ws, state)["active"] == []
    state.store.load()
    # A phone that connects in the middle of the game learns it at once.
    hub.foreground = foreground("x4.EXE")
    with connect(state) as ws:
        assert hello(ws, state)["active"] == ["demo"]
    hub.foreground = foreground("chrome.exe")
    with connect(state) as ws:
        assert hello(ws, state)["active"] == []
    # Between two windows the PC cannot tell, and says so: the phone keeps what it knew.
    hub.foreground = unknown
    with connect(state) as ws:
        assert hello(ws, state)["active"] is None

    heard = []

    async def send(ws, message):
        heard.append((ws, message["type"], message["panels"]))

    def told(*lists):
        return [("phone", "active", panels) for panels in lists]

    hub._send = send
    looks = (
        ("x4.exe", told(["demo"])),  # the player switched to the game
        ("x4.exe", told(["demo"])),  # still there: said once
        ("chrome.exe", told(["demo"], [])),
        ("notepad.exe", told(["demo"], [])),  # another program that is no game: no news
        (None, told(["demo"], [])),  # between two windows: not known, so nothing is said
        ("x4.exe", told(["demo"], [], ["demo"])),
    )
    hub.connections = {"phone": SimpleNamespace(ws="phone", active=[], held={})}
    for exe, said in looks:
        hub.foreground = foreground(exe) if exe else unknown
        asyncio.run(hub.follow_window())
        assert heard == said, exe

    # A phone that connected while the window was not known is told at the
    # next look, and it alone: the other one knows already.
    hub.connections["late"] = SimpleNamespace(ws="late", active=None, held={})
    del heard[:]
    asyncio.run(hub.follow_window())
    assert heard == [("late", "active", ["demo"])]

    # The watcher that runs in the program takes these looks.
    async def watch():
        watcher = asyncio.create_task(hub.watch_focus(0.01))
        await asyncio.sleep(0.2)
        watcher.cancel()

    del heard[:]
    hub.foreground = foreground("chrome.exe")
    asyncio.run(watch())
    assert sorted(heard) == [("late", "active", []), ("phone", "active", [])]

    # Nobody is connected: the window is not even looked at.
    hub.connections = {}
    hub.foreground = None
    asyncio.run(hub.follow_window())


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
        state.backend.clear()
        # A refused press must not be remembered as a key that is down:
        # the next presses really go to Windows.
        assert press(ws, "down", "forward")["ok"]
        assert press(ws, "up", "forward")["ok"]
        assert press(ws, "down", "map")["ok"]
        deadline = time.monotonic() + 2
        while len(state.backend.trace()) < 4 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert state.backend.trace() == ["+KeyW", "-KeyW", "+KeyM", "-KeyM"]
        assert state.controller.held_keys == set()


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
