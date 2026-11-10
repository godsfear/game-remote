"""Runs the real uvicorn server: the in-process test client cannot tell
whether uvicorn itself is able to speak WebSocket."""

import importlib.util
import json
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from websockets.exceptions import InvalidStatus
from websockets.sync.client import connect

from game_remote.input import InputController, RecordingBackend

spec = importlib.util.spec_from_file_location(
    "input_check_real", Path(__file__).resolve().parents[1] / "tools" / "input_check.py"
)
input_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(input_check)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_server():
    backend = RecordingBackend()
    app = input_check.build_app(InputController(backend, tap_ms=1), "s3cret")
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "server did not start"
        time.sleep(0.02)
    yield port, backend
    server.should_exit = True
    thread.join(timeout=10)


def test_phone_page_socket_works_over_a_real_connection(live_server):
    port, backend = live_server
    with connect(f"ws://127.0.0.1:{port}/ws?k=s3cret") as ws:
        ws.send(json.dumps({"type": "down", "id": 1, "combo": "KeyW"}))
        assert json.loads(ws.recv(timeout=5))["ok"]
    deadline = time.monotonic() + 5
    while backend.trace() != ["+KeyW", "-KeyW"]:
        assert time.monotonic() < deadline, backend.trace()
        time.sleep(0.02)


def test_real_socket_refuses_a_wrong_secret(live_server):
    port, backend = live_server
    with pytest.raises(InvalidStatus):
        connect(f"ws://127.0.0.1:{port}/ws?k=wrong")
    assert backend.trace() == []
