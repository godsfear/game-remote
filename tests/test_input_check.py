import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from game_remote.input import InputController, RecordingBackend

spec = importlib.util.spec_from_file_location(
    "input_check", Path(__file__).resolve().parents[1] / "tools" / "input_check.py"
)
input_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(input_check)


def test_spike_page_holds_and_releases_on_disconnect():
    backend = RecordingBackend()
    client = TestClient(input_check.build_app(InputController(backend, tap_ms=1)))
    assert "Input check" in client.get("/").text
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "ping", "t": 1})
        assert ws.receive_json() == {"type": "pong", "t": 1}
        ws.send_json({"type": "down", "id": 1, "combo": "KeyW"})
        assert ws.receive_json()["ok"]
        ws.send_json({"type": "tap", "id": 2, "combo": "Nope"})
        assert not ws.receive_json()["ok"]
    assert backend.trace() == ["+KeyW", "-KeyW"]
