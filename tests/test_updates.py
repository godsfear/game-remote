"""The check for a newer version of the program."""

import asyncio
import io
import json
import time
import urllib.error

import pytest
import truststore
from conftest import free_port
from fastapi.testclient import TestClient

from game_remote import main as program
from game_remote import updates
from game_remote.config import Settings
from game_remote.server.editor import create_editor_app
from game_remote.state import build_state
from game_remote.user_settings import load_user_settings

EDITOR = "http://127.0.0.1:8730"
ORIGIN = {"origin": EDITOR}


@pytest.fixture
def client(state):
    return TestClient(create_editor_app(state), base_url=EDITOR)


def answers(monkeypatch, body: bytes | Exception):
    """GitHub answers with ``body``, or the request fails with it."""
    asked = []

    def urlopen(request, timeout, context):
        # Windows itself checks the certificate: it has every root, Python may not.
        assert isinstance(context, truststore.SSLContext)
        asked.append(request)
        if isinstance(body, Exception):
            raise body
        return io.BytesIO(body)

    monkeypatch.setattr(updates.urllib.request, "urlopen", urlopen)
    return asked


def test_the_latest_release_is_asked_and_only_its_number_is_taken(monkeypatch):
    asked = answers(monkeypatch, json.dumps({"tag_name": "v0.5.0", "body": "notes"}).encode())
    assert updates.latest_version() == "0.5.0"
    assert asked[0].full_url == updates.LATEST_URL
    # GitHub refuses a request without this header; it names the program, not the user.
    assert asked[0].get_header("User-agent").startswith("GameRemote/")


@pytest.mark.parametrize(
    "body",
    [
        urllib.error.URLError("no network"),
        TimeoutError("too slow"),
        b"<html>not json</html>",
        b"[]",
        b'{"message": "rate limit"}',
        b'{"tag_name": null}',
        b'{"tag_name": "panel-sets"}',
        b'{"tag_name": "v1.0.0\\"><script>"}',
    ],
)
def test_an_answer_that_is_not_a_version_is_no_version(monkeypatch, body):
    answers(monkeypatch, body)
    assert updates.latest_version() is None


def test_only_a_later_version_is_an_update():
    assert updates.newer("0.5.0", "0.4.0") == "0.5.0"
    assert updates.newer("0.10.0", "0.9.9") == "0.10.0"  # numbers, not text
    assert updates.newer("0.4.0", "0.4.0") is None
    assert updates.newer("0.3.9", "0.4.0") is None
    assert updates.newer(None) is None
    # A trial build has letters in its version: it counts by its numbers.
    assert updates.newer("0.5.0", "0.5.0rc1") is None
    assert updates.newer("0.5.1", "0.5.0.dev0") == "0.5.1"


def test_tests_and_test_mode_never_ask_github(state):
    assert state.latest_version() is None


async def eventually(condition, seconds: float = 5.0) -> None:
    end = time.monotonic() + seconds
    while not condition():
        assert time.monotonic() < end, "condition was not met in time"
        await asyncio.sleep(0.01)


def test_the_editor_is_told_about_a_newer_version_until_the_check_is_turned_off(client, state):
    asked = []
    state.latest_version = lambda: asked.append(1) or "99.0.0"
    assert client.get("/api/status").json()["update"] is None

    asyncio.run(updates.refresh_update(state))
    assert client.get("/api/status").json()["update"] == "99.0.0"

    reply = client.put("/api/settings", json={"check_updates": False}, headers=ORIGIN)
    assert reply.json() == {"language": "auto", "check_updates": False}
    assert client.get("/api/status").json()["update"] is None
    # The page reads the box from the status too: another window may have changed it.
    assert client.get("/api/status").json()["check_updates"] is False
    assert load_user_settings(state.settings.user_settings_path).check_updates is False
    # Turned off, nothing is asked: not when its day comes, not by another setting.
    asyncio.run(updates.refresh_update(state))
    client.put("/api/settings", json={"language": "en"}, headers=ORIGIN)
    assert len(asked) == 1 and not state.check_now.is_set()

    # Turned on again: the program is told to ask now; the page does not wait for GitHub.
    client.put("/api/settings", json={"check_updates": True}, headers=ORIGIN)
    assert state.check_now.is_set() and len(asked) == 1


def test_the_version_that_runs_is_not_an_update(client, state):
    state.latest_version = lambda: updates.__version__
    asyncio.run(updates.refresh_update(state))
    assert client.get("/api/status").json()["update"] is None


def test_a_check_without_an_answer_keeps_the_version_that_is_known(state):
    state.latest_version = lambda: "99.0.0"
    asyncio.run(updates.refresh_update(state))
    state.latest_version = lambda: None  # the next day there is no network
    asyncio.run(updates.refresh_update(state))
    assert state.update == "99.0.0"


def test_an_answer_that_comes_after_the_check_was_turned_off_is_dropped(state):
    def slow():
        time.sleep(0.2)
        return "99.0.0"

    async def scenario():
        state.latest_version = slow
        asking = asyncio.create_task(updates.refresh_update(state))
        await asyncio.sleep(0.05)
        state.user = state.user.model_copy(update={"check_updates": False})
        await updates.refresh_update(state)  # what turning it off does
        await asking

    asyncio.run(scenario())
    assert state.update is None


def test_quitting_does_not_wait_for_a_request_that_hangs(state):
    async def scenario():
        state.latest_version = lambda: time.sleep(3)
        asking = asyncio.create_task(updates.refresh_update(state))
        await asyncio.sleep(0.05)
        asking.cancel()

    started = time.monotonic()
    asyncio.run(scenario())  # closes its loop the way the program does when it quits
    assert time.monotonic() - started < 1.5


def test_a_setting_of_the_pc_alone_is_not_sent_to_the_phones(client, state):
    sent = []

    async def set_language(language):
        sent.append(language)

    state.hub.set_language = set_language
    client.put("/api/settings", json={"check_updates": False}, headers=ORIGIN)
    assert sent == []
    client.put("/api/settings", json={"language": "en"}, headers=ORIGIN)
    assert sent == ["en"]


def test_a_question_without_an_answer_is_asked_again_before_a_day_passes(state, monkeypatch):
    """A PC that had no network a minute after its start still learns of a new version."""
    replies = [None, None, "99.0.0"]
    asked = []
    state.latest_version = lambda: asked.append(1) or replies[len(asked) - 1]
    monkeypatch.setattr(program, "FIRST_CHECK_SECONDS", 0.01)
    monkeypatch.setattr(program, "RETRY_CHECK_SECONDS", 0.01)

    async def scenario():
        watching = asyncio.create_task(program.watch_updates(state))
        await eventually(lambda: state.update == "99.0.0")
        await asyncio.sleep(0.1)
        watching.cancel()

    asyncio.run(scenario())
    assert len(asked) == 3  # answered: the next question waits for its day


def test_a_question_github_keeps_refusing_is_asked_less_and_less_often(state, monkeypatch):
    waits = []

    async def wait_for(waiting, timeout):
        waiting.close()
        waits.append(timeout)
        if len(waits) == 8:
            raise asyncio.CancelledError
        raise TimeoutError

    monkeypatch.setattr(program.asyncio, "wait_for", wait_for)
    state.latest_version = lambda: None
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(program.watch_updates(state))
    hour, day = program.RETRY_CHECK_SECONDS, program.UPDATE_CHECK_SECONDS
    first = program.FIRST_CHECK_SECONDS
    assert waits == [first, hour, 2 * hour, 4 * hour, 8 * hour, 16 * hour, day, day]


def test_the_running_program_asks_after_a_while_and_when_the_check_is_turned_on(
    tmp_path, monkeypatch
):
    """The whole program, as ``main`` runs it: the first question waits, so a
    new user can turn the check off before anything is asked."""
    settings = Settings(
        data_dir=tmp_path, editor_port=free_port(), remote_port=free_port(), open_browser=False
    )
    state = build_state(settings, fake_input=True)
    asked = []
    state.latest_version = lambda: asked.append(1) or "99.0.0"
    monkeypatch.setattr(program, "FIRST_CHECK_SECONDS", 0.3)

    async def scenario():
        running = asyncio.create_task(program.serve(state))
        await eventually(lambda: state.stop is not None)
        assert asked == []  # nothing is asked right at the start
        await eventually(lambda: state.update == "99.0.0")
        assert len(asked) == 1
        state.check_now.set()  # what turning the check on does
        await eventually(lambda: len(asked) == 2)
        await asyncio.sleep(0.1)
        assert len(asked) == 2  # then not again until its day has passed
        state.stop()
        await running

    try:
        asyncio.run(scenario())
    finally:
        state.devices.close()


def test_settings_are_saved_while_another_program_reads_the_file(client, state, monkeypatch):
    """On Windows a file somebody reads cannot be replaced at that moment: an
    antivirus does that to a file that was just written. The write waits."""
    from game_remote import files

    real, refused = files.os.replace, []

    def replace(source, target):
        if not refused:
            refused.append(target)
            raise PermissionError(5, "Access is denied")
        real(source, target)

    monkeypatch.setattr(files.os, "replace", replace)
    reply = client.put("/api/settings", json={"check_updates": False}, headers=ORIGIN)
    assert reply.status_code == 200 and refused
    assert load_user_settings(state.settings.user_settings_path).check_updates is False


def test_a_setting_that_could_not_be_saved_is_not_acted_upon(state, monkeypatch):
    """The box must not show "off" while the file, and the next start, say "on"."""

    def refused(source, target):
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr("game_remote.files.os.replace", refused)
    client = TestClient(create_editor_app(state), base_url=EDITOR, raise_server_exceptions=False)
    reply = client.put("/api/settings", json={"check_updates": False}, headers=ORIGIN)
    assert reply.status_code == 500
    assert client.get("/api/status").json()["check_updates"] is True
    assert load_user_settings(state.settings.user_settings_path).check_updates is True
