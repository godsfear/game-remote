"""Starts the program the way a user would and checks that it really works.

    python tools/smoke_test.py dist/GameRemote.exe
    python tools/smoke_test.py python -m game_remote

It uses a temporary data folder and free ports, so it does not disturb a
running Game Remote. By default key presses are only recorded. With
--real-input one harmless key (Shift) goes through Windows SendInput.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from websockets.sync.client import connect

START_TIMEOUT = 60.0  # a single-file exe unpacks itself first, and antivirus scans it
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Program:
    def __init__(self, command: list[str], real_input: bool = False) -> None:
        self.command = [*command, "--no-browser", "--no-tray"]
        if not real_input:
            self.command.append("--fake-input")
        self.real_input = real_input
        self._tmp = tempfile.TemporaryDirectory(prefix="game-remote-smoke-")
        self.data_dir = Path(self._tmp.name)
        self.editor_port, self.remote_port = free_port(), free_port()
        self.env = dict(
            os.environ,
            GAME_REMOTE_DATA_DIR=str(self.data_dir),
            GAME_REMOTE_EDITOR_PORT=str(self.editor_port),
            GAME_REMOTE_REMOTE_PORT=str(self.remote_port),
        )
        self.editor = f"http://127.0.0.1:{self.editor_port}"
        self.remote = f"http://127.0.0.1:{self.remote_port}"
        self.process: subprocess.Popen | None = None

    # -- process ---------------------------------------------------------------

    def start(self) -> None:
        self.process = subprocess.Popen(self.command, env=self.env)
        deadline = time.monotonic() + START_TIMEOUT
        while True:
            if self.process.poll() is not None:
                raise AssertionError(f"the program exited with code {self.process.returncode}")
            try:
                if (
                    self.get(self.editor + "/api/health")["app"] == "editor"
                    and self.get(self.remote + "/api/health")["app"] == "remote"
                ):
                    return
            except (OSError, ValueError):
                pass
            if time.monotonic() > deadline:
                raise AssertionError("the program did not start in time")
            time.sleep(0.2)

    def close(self) -> None:
        if self.process is not None and self.process.poll() is None:
            if sys.platform == "win32":
                # A single-file exe is two processes; take both down.
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                self.process.kill()
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.process.wait(timeout=10)
        with contextlib.suppress(OSError):
            self._tmp.cleanup()

    def log(self) -> str:
        return "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in sorted((self.data_dir / "logs").glob("*"))
            if path.is_file()
        )

    # -- helpers ---------------------------------------------------------------

    def get(self, url: str) -> dict:
        with _opener.open(url, timeout=3) as response:
            return json.load(response)

    def get_text(self, url: str) -> str:
        with _opener.open(url, timeout=3) as response:
            return response.read().decode("utf-8")

    def post(self, path: str, origin: str | None = None) -> tuple[int, dict]:
        headers = {"Origin": origin} if origin else {}
        request = urllib.request.Request(self.editor + path, data=b"", headers=headers)
        try:
            with _opener.open(request, timeout=3) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, {}

    def status(self) -> dict:
        return self.get(self.editor + "/api/status")

    def phone(self):
        return connect(f"ws://127.0.0.1:{self.remote_port}/ws", proxy=None, open_timeout=10)

    def key(self) -> str:
        return (self.data_dir / "access.key").read_text(encoding="ascii").strip()


def wait_for(condition, what: str, timeout: float = 6.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError(f"timed out: {what}")
        time.sleep(0.1)


def exchange(ws, message: dict) -> dict:
    ws.send(json.dumps(message))
    return json.loads(ws.recv(timeout=5))


def check(program: Program, say=print) -> None:
    """The checks themselves. Raises AssertionError with a readable reason."""
    status = program.status()
    assert [p["id"] for p in status["panels"]] == ["demo"], status
    assert status["fake_input"] is (not program.real_input), status
    say(f"started, version {status['version']}, demo panel is there")

    for path in ("/", "/app.js", "/style.css", "/shared/i18n.js"):
        assert program.get_text(program.editor + path), f"editor{path} is empty"
        assert program.get_text(program.remote + path), f"remote{path} is empty"
    links = program.get(program.editor + "/api/links")["links"]
    if links:
        assert "<svg" in program.get_text(program.editor + "/api/qr/0.svg")
    say(f"pages are served, {len(links)} address(es) for the QR code")

    with program.phone() as ws:
        ws.send(json.dumps({"type": "hello", "key": "wrong-key"}))
        try:
            ws.recv(timeout=5)
        except Exception as closed:  # noqa: BLE001 - any close is the expected result
            assert "4401" in str(closed), closed
        else:
            raise AssertionError("a wrong key was accepted")
    say("a wrong key is refused")

    with program.phone() as ws:
        welcome = exchange(ws, {"type": "hello", "key": program.key()})
        assert welcome["type"] == "welcome" and welcome["panels"][0]["id"] == "demo", welcome
        assert exchange(ws, {"type": "ping", "t": 1}) == {"type": "pong", "t": 1}

        if not program.real_input:
            ack = exchange(ws, {"type": "down", "id": 1, "panel": "demo", "button": "map"})
            assert ack == {"type": "ack", "id": 1, "ok": True}, ack
            exchange(ws, {"type": "up", "id": 2, "panel": "demo", "button": "map"})
        # "run" holds Shift, which does nothing on its own.
        ack = exchange(ws, {"type": "down", "id": 3, "panel": "demo", "button": "run"})
        assert ack == {"type": "ack", "id": 3, "ok": True}, ack
        # The tapped key is released after some milliseconds; Shift stays down.
        wait_for(lambda: program.status()["held_keys"] == ["ShiftLeft"], "only Shift is held")
        assert program.status()["phones"] == 1
        say("tap and hold reach the input layer")
    wait_for(lambda: program.status()["held_keys"] == [], "keys released after disconnect")
    say("held key is released when the phone disconnects")

    with program.phone() as ws:
        exchange(ws, {"type": "hello", "key": program.key()})
        panel_file = program.data_dir / "panels" / "demo" / "panel.json"
        panel = json.loads(panel_file.read_text(encoding="utf-8"))
        panel["name"] = "Smoke test"
        panel_file.write_text(json.dumps(panel), encoding="utf-8")
        pushed = json.loads(ws.recv(timeout=10))
        assert pushed["type"] == "panels" and pushed["panels"][0]["name"] == "Smoke test", pushed
    say("an edited panel file reaches the phone")

    second = subprocess.run(program.command, env=program.env, timeout=START_TIMEOUT, check=False)
    assert second.returncode == 0, f"second copy exited with {second.returncode}"
    assert program.get(program.editor + "/api/health")["app"] == "editor"
    say("a second copy exits and leaves the first one running")

    assert program.post("/api/quit")[0] == 403, "quit without Origin must be refused"
    code, body = program.post("/api/quit", origin=program.editor)
    assert (code, body) == (200, {"ok": True}), (code, body)
    assert program.process is not None
    try:
        exit_code = program.process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        raise AssertionError("the program did not exit after Quit") from None
    assert exit_code == 0, f"exit code {exit_code}"
    say("Quit stops the program")


def run(command: list[str], real_input: bool = False, say=print) -> None:
    program = Program(command, real_input=real_input)
    try:
        program.start()
        check(program, say)
    except BaseException:
        log = program.log()
        if log:
            say("--- program log ---\n" + log)
        raise
    finally:
        program.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--real-input", action="store_true", help="send Shift through SendInput")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="how to start Game Remote")
    args = parser.parse_args()
    command = args.command
    if not command:
        parser.error("say how to start Game Remote, for example: dist/GameRemote.exe")
    if Path(command[0]).exists():
        command = [str(Path(command[0]).absolute()), *command[1:]]
    try:
        run(command, real_input=args.real_input)
    except AssertionError as error:
        print(f"FAILED: {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
