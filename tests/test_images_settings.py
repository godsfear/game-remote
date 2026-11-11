"""Pictures for buttons and games, and the language chosen on the PC."""

import json
import os
import time

import pytest
from fastapi.testclient import TestClient

from game_remote.panels import MAX_IMAGE_BYTES, image_extension
from game_remote.server.editor import create_editor_app
from game_remote.server.remote import create_remote_app
from game_remote.user_settings import UserSettings, load_user_settings

EDITOR = "http://127.0.0.1:8730"
ORIGIN = {"origin": EDITOR}
PHONE = ("192.168.1.50", 50000)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32


@pytest.fixture
def client(state):
    return TestClient(create_editor_app(state), base_url=EDITOR)


def upload(client, data, panel="demo", headers=ORIGIN):
    return client.post(f"/api/panels/{panel}/images", content=data, headers=headers)


def demo(client):
    return client.get("/api/panels").json()["panels"][0]


def test_image_kind_is_judged_by_content():
    assert image_extension(PNG) == "png"
    assert image_extension(JPEG) == "jpg"
    assert image_extension(WEBP) == "webp"
    for data in (
        b"",
        b"<svg xmlns='http://www.w3.org/2000/svg'/>",
        b"GIF89a",
        b"MZ\x90\x00",
        b"RIFF",
    ):
        assert image_extension(data) is None


@pytest.mark.parametrize(("data", "extension"), [(PNG, "png"), (JPEG, "jpg"), (WEBP, "webp")])
def test_upload_stores_the_picture_in_the_panel_folder(client, state, data, extension):
    reply = upload(client, data)
    assert reply.status_code == 201
    name = reply.json()["name"]
    assert name.startswith("img-") and name.endswith("." + extension)
    assert (state.settings.panels_dir / "demo" / name).read_bytes() == data
    # The editor can show it at once, before the panel that uses it is saved.
    assert client.get(f"/panel-files/demo/{name}").content == data


def test_upload_refuses_what_is_not_a_picture(client, state):
    for data in (b"<script>alert(1)</script>", b"MZ\x90\x00" + b"\x00" * 64, b""):
        reply = upload(client, data)
        assert reply.status_code == 415
        assert reply.json() == {"error": "not_an_image"}
    assert sorted(p.name for p in (state.settings.panels_dir / "demo").iterdir()) == ["panel.json"]


def test_upload_refuses_a_huge_file(client):
    reply = upload(client, PNG + b"\x00" * MAX_IMAGE_BYTES)
    assert reply.status_code == 413
    assert reply.json() == {"error": "too_large"}


def test_upload_needs_an_existing_panel_and_the_editors_origin(client):
    assert upload(client, PNG, panel="nope").status_code == 404
    assert upload(client, PNG, headers={}).status_code == 403
    assert upload(client, PNG, headers={"origin": "http://evil.example"}).status_code == 403


def test_picture_and_cover_reach_the_phone(client, state):
    image, cover = upload(client, PNG).json()["name"], upload(client, JPEG).json()["name"]
    phone = TestClient(create_remote_app(state), client=PHONE)
    # Uploaded but not used by the panel yet: the phone gets nothing.
    assert phone.get(f"/panel-files/demo/{image}").status_code == 404

    panel = demo(client)
    panel.pop("id")
    panel["cover"] = cover
    panel["buttons"][0]["image"] = image
    assert client.put("/api/panels/demo", json=panel, headers=ORIGIN).status_code == 200

    public = state.store.public()[0]
    assert public["cover"] == f"/panel-files/demo/{cover}"
    assert public["buttons"][0]["image"] == f"/panel-files/demo/{image}"
    assert phone.get(public["cover"]).content == JPEG
    assert phone.get(public["buttons"][0]["image"]).content == PNG
    on_disk = json.loads((state.settings.panels_dir / "demo" / "panel.json").read_text("utf-8"))
    assert on_disk["cover"] == cover


def test_replaced_pictures_are_removed_later_and_own_files_never(client, state):
    folder = state.settings.panels_dir / "demo"
    old, fresh = upload(client, PNG).json()["name"], upload(client, PNG).json()["name"]
    (folder / "my-photo.png").write_bytes(PNG)  # put there by hand
    (folder / "img-notes.txt").write_text("mine")
    long_ago = time.time() - 3600
    for name in (old, "my-photo.png", "img-notes.txt"):
        os.utime(folder / name, (long_ago, long_ago))

    panel = demo(client)
    panel.pop("id")
    client.put("/api/panels/demo", json=panel, headers=ORIGIN)
    left = sorted(p.name for p in folder.iterdir())
    assert old not in left  # unused and old: removed
    assert fresh in left  # unused but just uploaded: the page may still save it
    assert "my-photo.png" in left and "img-notes.txt" in left


def test_editor_serves_only_pictures_from_the_panel_folder(client, state):
    (state.settings.panels_dir / "demo" / "notes.txt").write_text("x")
    for name in ("panel.json", "notes.txt", "..%2F..%2Faccess.key", "%2e%2e%2faccess.key"):
        assert client.get(f"/panel-files/demo/{name}").status_code == 404


def test_language_is_auto_by_default(client, state):
    assert client.get("/api/settings").json() == {"language": "auto"}
    assert state.hub.language is None


def test_language_choice_is_saved_and_sent_to_phones(client, state):
    phone = TestClient(create_remote_app(state), client=PHONE)
    with phone.websocket_connect("/ws") as ws:
        ws.send_json({"type": "hello", "key": state.access_key})
        assert ws.receive_json()["language"] is None

        reply = client.put("/api/settings", json={"language": "en"}, headers=ORIGIN)
        assert reply.json() == {"language": "en"}
        assert ws.receive_json() == {"type": "settings", "language": "en"}

        client.put("/api/settings", json={"language": "auto"}, headers=ORIGIN)
        assert ws.receive_json() == {"type": "settings", "language": None}

    client.put("/api/settings", json={"language": "ru"}, headers=ORIGIN)
    assert load_user_settings(state.settings.user_settings_path).language == "ru"
    with phone.websocket_connect("/ws") as ws:
        ws.send_json({"type": "hello", "key": state.access_key})
        assert ws.receive_json()["language"] == "ru"


def test_bad_language_is_refused(client):
    assert client.put("/api/settings", json={"language": "xx"}, headers=ORIGIN).status_code == 422
    assert client.put("/api/settings", json={"language": "en"}).status_code == 403


def test_settings_file_survives_damage(tmp_path):
    path = tmp_path / "settings.json"
    assert load_user_settings(path) == UserSettings()
    path.write_text("{ broken", encoding="utf-8")
    assert load_user_settings(path) == UserSettings()
    path.write_text('{"language": "klingon"}', encoding="utf-8")
    assert load_user_settings(path) == UserSettings()
    path.write_text('{"language": "ru", "future_option": 1}', encoding="utf-8")
    assert load_user_settings(path).language == "ru"
