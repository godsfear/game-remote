"""Starts the whole program as a separate process, like a user does."""

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "smoke_test", Path(__file__).resolve().parents[1] / "tools" / "smoke_test.py"
)
smoke_test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke_test)


def test_program_runs_end_to_end():
    lines = []
    smoke_test.run([sys.executable, "-m", "game_remote"], say=lines.append)
    assert lines[-1] == "Quit stops the program"


def test_busy_port_is_reported_not_crashed(tmp_path, monkeypatch):
    import socket

    from game_remote import main as program

    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        monkeypatch.setenv("GAME_REMOTE_DATA_DIR", str(tmp_path))
        port = taken.getsockname()[1]
        monkeypatch.setenv("GAME_REMOTE_EDITOR_PORT", str(port))
        monkeypatch.setenv("GAME_REMOTE_REMOTE_PORT", str(smoke_test.free_port()))
        shown = []
        monkeypatch.setattr(program, "show_error", shown.append)
        monkeypatch.setattr(program, "wait_for_ports", lambda s: program.busy_port(s))
        monkeypatch.setattr(program, "setup_logging", lambda log_dir: None)
        assert program.main(["--no-browser", "--no-tray", "--fake-input"]) == 1
    assert len(shown) == 1 and str(port) in shown[0]
