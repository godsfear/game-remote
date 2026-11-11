import json
import time

import pytest

from game_remote.config import Settings
from game_remote.panels import PANEL_FILE, SAMPLE_ID, demo_panel
from game_remote.state import build_state


def seed_demo(data_dir) -> None:
    """Puts a plain panel with tap and hold buttons into the data folder and
    marks the ready-made panel as installed, so tests work with this one only."""
    folder = data_dir / "panels" / "demo"
    folder.mkdir(parents=True)
    panel = demo_panel(russian=False).model_dump(exclude_none=True)
    (folder / PANEL_FILE).write_text(json.dumps(panel), encoding="utf-8")
    (data_dir / "settings.json").write_text(json.dumps({"samples": [SAMPLE_ID]}), encoding="utf-8")


@pytest.fixture
def state(tmp_path):
    """A complete app state with fake input and a demo panel in a temp folder."""
    seed_demo(tmp_path)
    settings = Settings(data_dir=tmp_path, editor_port=8730, remote_port=8731, open_browser=False)
    state = build_state(settings, fake_input=True, tap_ms=1)
    yield state
    state.devices.close()


def phone_key(state, name="Test phone") -> str:
    """Registers a device without the QR code and returns its key."""
    return state.devices.add(name)[1]


def wait_for(condition, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condition was not met in time"
        time.sleep(0.02)
