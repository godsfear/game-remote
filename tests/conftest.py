import time

import pytest

from game_remote.config import Settings
from game_remote.state import build_state


@pytest.fixture
def state(tmp_path):
    """A complete app state with fake input and a demo panel in a temp folder."""
    settings = Settings(data_dir=tmp_path, editor_port=8730, remote_port=8731, open_browser=False)
    return build_state(settings, fake_input=True, tap_ms=1)


def wait_for(condition, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condition was not met in time"
        time.sleep(0.02)
