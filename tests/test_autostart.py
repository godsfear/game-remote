"""Starting the program together with Windows."""

import contextlib
import json
import secrets
import sys

import pytest
from fastapi.testclient import TestClient

from game_remote.autostart import Autostart, MemoryValue, RegistryValue, own_command
from game_remote.server.editor import create_editor_app

EDITOR = "http://127.0.0.1:8730"
ORIGIN = {"origin": EDITOR}
EXE = r'"C:\Games\GameRemote.exe" --no-browser'


def test_the_box_puts_the_program_into_the_start_of_windows_and_takes_it_out():
    value = MemoryValue()
    autostart = Autostart(value, EXE)
    assert autostart.supported and not autostart.enabled()
    autostart.set(True)
    assert autostart.enabled() and value.get() == EXE
    autostart.set(False)
    assert not autostart.enabled() and value.get() is None


def test_a_moved_exe_is_the_one_windows_starts_from_then_on():
    """A newer GameRemote.exe was downloaded next to the old one, or the file
    was moved: the first run of that copy points Windows at it."""
    value = MemoryValue(r'"C:\Downloads\GameRemote.exe" --no-browser')
    Autostart(value, EXE).refresh()
    assert value.get() == EXE
    # Whoever did not ask for the start with Windows does not get it this way.
    untouched = MemoryValue()
    Autostart(untouched, EXE).refresh()
    assert untouched.get() is None


def test_a_run_from_the_source_does_not_offer_it():
    assert own_command() is None  # the tests are no exe
    autostart = Autostart(MemoryValue("something"), None)
    assert not autostart.supported and not autostart.enabled()
    autostart.set(True)  # changes nothing
    assert autostart.value.get() == "something"


def test_windows_that_does_not_answer_leaves_the_box_empty(caplog):
    class Locked(MemoryValue):
        def get(self):
            raise PermissionError(5, "Access is denied")

    autostart = Autostart(Locked(), EXE)
    assert not autostart.enabled()
    autostart.refresh()  # and the start of the program goes on
    # The editor asks all the time: the log gets the refusal once.
    caplog.clear()
    assert not autostart.enabled() and not autostart.enabled()
    assert caplog.records == []


@pytest.mark.skipif(sys.platform != "win32", reason="the registry is a thing of Windows")
def test_the_value_is_kept_in_the_registry_of_the_user():
    """In a key of its own: the list of what Windows starts is not touched."""
    import winreg

    base = rf"Software\GameRemoteTests\{secrets.token_hex(6)}"
    key, approved = rf"{base}\Run", rf"{base}\Approved"
    value = RegistryValue(key, "GameRemote", approved)

    def mark(first_byte):
        """What the switch of Windows leaves for the program."""
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, approved) as switches:
            data = bytes([first_byte]) + bytes(11)
            winreg.SetValueEx(switches, "GameRemote", 0, winreg.REG_BINARY, data)

    try:
        assert value.get() is None  # no such key yet
        value.set(EXE)
        assert value.get() == EXE
        # Windows has a switch of its own, which leaves the value where it is.
        mark(3)
        assert value.get() is None and not Autostart(value, EXE).enabled()
        Autostart(value, "another.exe").refresh()  # a start does not switch it on again
        assert value.get() is None
        mark(2)
        assert value.get() == EXE  # switched on again in Windows
        # Ticking the box in the editor switches it on in Windows too.
        mark(3)
        Autostart(value, EXE).set(True)
        assert value.get() == EXE
        value.set(None)
        assert value.get() is None
        value.set(None)  # taking away what is not there is no mistake
    finally:
        # A key that was never made must not hide why the test failed.
        for made in (key, approved, base, r"Software\GameRemoteTests"):
            with contextlib.suppress(OSError):
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, made)


def test_the_editor_ticks_and_unticks_it(state, monkeypatch):
    client = TestClient(create_editor_app(state), base_url=EDITOR)
    assert client.get("/api/settings").json()["autostart"] is False
    assert client.get("/api/status").json()["autostart"] is False

    reply = client.put("/api/settings", json={"autostart": True}, headers=ORIGIN)
    assert reply.json() == {"language": "auto", "check_updates": True, "autostart": True}
    assert state.autostart.enabled() and client.get("/api/status").json()["autostart"] is True
    # Windows keeps it, not the file of settings.
    path = state.settings.user_settings_path
    assert not path.exists() or "autostart" not in json.loads(path.read_text(encoding="utf-8"))

    # So the file is not even written, and a file that cannot be written does
    # not turn a change Windows took into an error.
    def refused(*args):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr("game_remote.server.editor.save_user_settings", refused)
    again = client.put("/api/settings", json={"autostart": True}, headers=ORIGIN)
    assert (again.status_code, again.json()["autostart"]) == (200, True)
    monkeypatch.undo()
    # Another setting leaves it alone.
    client.put("/api/settings", json={"check_updates": False}, headers=ORIGIN)
    assert state.autostart.enabled()
    assert (
        client.put("/api/settings", json={"autostart": False}, headers=ORIGIN).json()["autostart"]
        is False
    )


def test_the_editor_does_not_offer_it_where_it_cannot_work(state):
    state.autostart = Autostart(MemoryValue(), None)
    client = TestClient(create_editor_app(state), base_url=EDITOR)
    assert client.get("/api/status").json()["autostart"] is None
    reply = client.put("/api/settings", json={"autostart": True}, headers=ORIGIN)
    assert reply.json()["autostart"] is None


def test_a_refusal_of_windows_is_told_and_changes_nothing(state):
    class Refusing(MemoryValue):
        def set(self, text):
            raise PermissionError(5, "Access is denied")

    state.autostart = Autostart(Refusing(), EXE)
    client = TestClient(create_editor_app(state), base_url=EDITOR)
    reply = client.put("/api/settings", json={"autostart": True, "language": "en"}, headers=ORIGIN)
    assert (reply.status_code, reply.json()) == (
        500,
        {"error": "Windows refused: Access is denied"},
    )
    assert state.user.language == "auto"  # nothing of the request was taken
