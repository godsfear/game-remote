"""The editor's API for games and buttons."""

import io
import json
import os
import random
import re
import struct
import zipfile

import pytest
from conftest import phone_key
from fastapi.testclient import TestClient

from game_remote.panels import PanelStore
from game_remote.server.editor import create_editor_app
from game_remote.server.remote import create_remote_app

EDITOR = "http://127.0.0.1:8730"
ORIGIN = {"origin": EDITOR}

X4 = {
    "name": "X4: Foundations",
    "columns": 2,
    "buttons": [
        {"id": "map", "label": "Карта", "keys": "KeyM"},
        {"id": "radio", "label": "Связь", "keys": "KeyR+ControlLeft", "type": "hold"},
    ],
}


@pytest.fixture
def client(state):
    return TestClient(create_editor_app(state), base_url=EDITOR)


def panel_file(state, panel_id):
    return state.settings.panels_dir / panel_id / "panel.json"


def test_panels_are_listed_with_their_keys(client):
    data = client.get("/api/panels").json()
    assert [p["id"] for p in data["panels"]] == ["demo"]
    assert data["panels"][0]["buttons"][0]["keys"] == "KeyM"
    assert data["errors"] == {}
    assert data["revision"] == client.get("/api/status").json()["revision"]


def test_key_list_for_the_manual_choice(client):
    data = client.get("/api/keys").json()
    by_code = {key["code"]: key for key in data["keys"]}
    assert by_code["KeyM"] == {"code": "KeyM", "label": "M", "modifier": False}
    assert by_code["ControlLeft"]["modifier"] is True
    assert data["modifiers"][0] == "ControlLeft"


def test_create_a_game(client, state):
    created = client.post("/api/panels", json={"name": "X4: Foundations"}, headers=ORIGIN)
    assert created.status_code == 201
    data = created.json()
    assert data["id"] == "x4-foundations"
    assert [p["id"] for p in data["panels"]] == ["demo", "x4-foundations"]
    assert json.loads(panel_file(state, "x4-foundations").read_text(encoding="utf-8"))["name"] == (
        "X4: Foundations"
    )


def test_game_ids_do_not_collide(client):
    ids = [
        client.post("/api/panels", json={"name": name}, headers=ORIGIN).json()["id"]
        for name in ("Новая игра", "Новая игра", "demo", "a" * 60)
    ]
    assert ids == ["game", "game-2", "demo-2", "a" * 30]


@pytest.mark.parametrize("body", [{}, {"name": ""}, {"name": "x" * 61}])
def test_a_game_needs_a_sane_name(client, body):
    assert client.post("/api/panels", json=body, headers=ORIGIN).status_code == 422


def test_save_writes_the_file_and_normalises_keys(client, state):
    before = client.get("/api/panels").json()["revision"]
    saved = client.put("/api/panels/demo", json=X4, headers=ORIGIN)
    assert saved.status_code == 200
    assert saved.json()["revision"] > before
    on_disk = json.loads(panel_file(state, "demo").read_text(encoding="utf-8"))
    assert on_disk["name"] == "X4: Foundations"
    assert on_disk["buttons"][1]["keys"] == "ControlLeft+KeyR"
    assert state.store.get("demo").panel.columns == 2
    assert not (state.settings.panels_dir / "demo" / "panel.json.tmp").exists()


def test_the_page_does_not_reload_after_its_own_save(client, state):
    revision = client.put("/api/panels/demo", json=X4, headers=ORIGIN).json()["revision"]
    assert not state.store.reload_if_changed()  # the watcher sees nothing new
    assert client.get("/api/status").json()["revision"] == revision


def test_bad_panel_is_refused_and_the_file_stays(client, state):
    before = panel_file(state, "demo").read_text(encoding="utf-8")
    bad = dict(X4, buttons=[{"id": "a", "keys": "NoSuchKey"}])
    reply = client.put("/api/panels/demo", json=bad, headers=ORIGIN)
    assert reply.status_code == 422
    assert "buttons.0.keys" in reply.json()["error"]
    assert panel_file(state, "demo").read_text(encoding="utf-8") == before


@pytest.mark.parametrize("panel_id", ["nope", "bad id", "..", "demo.json"])
def test_save_cannot_create_or_escape(client, state, panel_id):
    # ".." never reaches the handler: the URL is normalised to another route.
    reply = client.put(f"/api/panels/{panel_id}", json=X4, headers=ORIGIN)
    assert reply.status_code in (404, 405)
    assert sorted(p.name for p in state.settings.panels_dir.iterdir()) == ["demo"]


def test_a_broken_file_can_be_fixed_from_the_editor(client, state):
    panel_file(state, "demo").write_text("{ broken", encoding="utf-8")
    state.store.load()
    assert "demo" in client.get("/api/panels").json()["errors"]
    assert client.put("/api/panels/demo", json=X4, headers=ORIGIN).status_code == 200
    assert client.get("/api/panels").json()["errors"] == {}


def test_delete_moves_the_game_to_the_trash(client, state):
    client.post("/api/panels", json={"name": "X4"}, headers=ORIGIN)
    assert client.delete("/api/panels/x4", headers=ORIGIN).json()["ok"]
    assert [p["id"] for p in client.get("/api/panels").json()["panels"]] == ["demo"]
    kept = list(state.settings.trash_dir.iterdir())
    assert len(kept) == 1 and kept[0].name.startswith("x4-")
    assert (kept[0] / "panel.json").is_file()
    assert client.delete("/api/panels/x4", headers=ORIGIN).status_code == 404


def test_deleting_the_same_name_twice_keeps_both_copies(tmp_path):
    store = PanelStore(tmp_path / "panels", tmp_path / "trash")
    for _ in range(2):
        store.create("X4")
        assert store.delete("x4")
    assert len(list((tmp_path / "trash").iterdir())) == 2
    assert not store.delete("x4")


def test_changes_need_the_editors_origin(client):
    for method, path in (("post", "/api/panels"), ("put", "/api/panels/demo")):
        call = getattr(client, method)
        assert call(path, json=X4).status_code == 403
        assert call(path, json=X4, headers={"origin": "http://evil.example"}).status_code == 403
    assert client.delete("/api/panels/demo").status_code == 403


def test_the_phone_has_no_editor_api(state):
    phone = TestClient(create_remote_app(state), client=("192.168.1.50", 50000))
    assert phone.get("/api/panels").status_code == 404
    assert phone.get("/api/keys").status_code == 404
    assert phone.put("/api/panels/demo", json=X4).status_code in (404, 405)
    assert phone.delete("/api/panels/demo").status_code in (404, 405)


def test_an_edit_reaches_the_phone_and_releases_its_keys(client, state):
    phone = TestClient(create_remote_app(state), client=("192.168.1.50", 50000))
    with phone.websocket_connect("/ws") as ws:
        ws.send_json({"type": "hello", "key": phone_key(state)})
        ws.receive_json()
        ws.send_json({"type": "down", "id": 1, "panel": "demo", "button": "forward"})
        assert ws.receive_json()["ok"]
        assert state.controller.held_keys == {"KeyW"}

        client.put("/api/panels/demo", json=X4, headers=ORIGIN)
        pushed = ws.receive_json()
        assert pushed["type"] == "panels"
        assert pushed["panels"][0]["name"] == "X4: Foundations"
        assert "KeyM" not in json.dumps(pushed)
        assert state.controller.held_keys == set()

        client.post("/api/panels", json={"name": "Second"}, headers=ORIGIN)
        assert len(ws.receive_json()["panels"]) == 2
        client.delete("/api/panels/second", headers=ORIGIN)
        assert len(ws.receive_json()["panels"]) == 1


def test_editor_serves_panel_images_for_the_preview(client, state):
    folder = state.settings.panels_dir / "demo"
    data = json.loads((folder / "panel.json").read_text(encoding="utf-8"))
    data["buttons"][0]["image"] = "map.png"
    (folder / "map.png").write_bytes(b"\x89PNG")
    assert client.put("/api/panels/demo", json=data, headers=ORIGIN).status_code == 200
    assert client.get("/panel-files/demo/map.png").content == b"\x89PNG"
    assert client.get("/panel-files/demo/panel.json").status_code == 404


# -- sets: a game as a file to share ------------------------------------------------

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
ZIP = {"origin": EDITOR, "content-type": "application/zip"}
ELITE = {
    "name": "Elite",
    "language": "de",
    "cover": "cover.png",
    "buttons": [{"id": "gear", "label": "Fahrwerk", "keys": "KeyN", "image": "gear.png"}],
}


def zipped(files: dict) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content if isinstance(content, bytes) else json.dumps(content))
    return out.getvalue()


def test_a_game_is_exported_and_imported_as_a_set(client, state):
    name = client.post("/api/panels/demo/images", content=PNG, headers=ORIGIN).json()["name"]
    demo = client.get("/api/panels").json()["panels"][0]
    demo = {key: value for key, value in demo.items() if key not in ("id", "language")}
    client.put("/api/panels/demo", json=demo | {"cover": name}, headers=ORIGIN)

    exported = client.get("/api/panels/demo/export?language=en")
    assert exported.headers["content-disposition"] == 'attachment; filename="demo.zip"'
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert sorted(archive.namelist()) == sorted(["panel.json", name])
        assert json.loads(archive.read("panel.json"))["language"] == "en"

    again = "/api/sets?languages=ru&same_name=add"  # the game it came from is still here
    imported = client.post(again, content=exported.content, headers=ZIP)
    assert imported.status_code == 201 and imported.json()["id"] == "demo-2"
    first, second = imported.json()["panels"]
    assert {**second, "id": "demo"} == first
    # The game on this PC is a plain panel: the mark of the language stays in the set.
    assert "language" not in json.loads(panel_file(state, "demo-2").read_text(encoding="utf-8"))
    assert client.get(f"/panel-files/demo-2/{name}").content == PNG
    assert client.get("/api/panels/nope/export").status_code == 404


def test_an_imported_set_takes_the_language_of_the_page(client, state):
    # Zipped as a folder, the way Windows does it, with files a set does not need.
    files = {
        "elite/panel.json": ELITE,
        "elite/panel.ru.json": {"name": "Элита", "labels": {"gear": "Шасси"}},
        "elite/cover.png": PNG,
        "elite/gear.png": PNG,
        "elite/readme.txt": b"hello",
        "__MACOSX/elite/._cover.png": b"junk",
    }
    # The first language the set has wins; German is what panel.json is in.
    # A browser may name no language at all: that is not a mistake of the request.
    cases = (
        ("&languages=ru", "Элита", "Шасси"),
        ("&languages=fr,ru,en", "Элита", "Шасси"),
        ("&languages=fr", "Elite", "Fahrwerk"),
        ("&languages=", "Elite", "Fahrwerk"),
        ("", "Elite", "Fahrwerk"),
    )
    for query, name, label in cases:
        address = f"/api/sets?same_name=add{query}"
        reply = client.post(address, content=zipped(files), headers=ZIP)
        panel = reply.json()["panels"][-1]
        assert (panel["name"], panel["buttons"][0]["label"]) == (name, label)
    folder = state.settings.panels_dir / "elite"
    assert sorted(p.name for p in folder.iterdir()) == ["cover.png", "gear.png", "panel.json"]


@pytest.mark.parametrize(
    ("files", "problem"),
    [
        (None, "not a zip"),
        ({"readme.txt": b"no panel here"}, "there is no panel.json in the set"),
        ({"panel.json": ELITE, "cover.png": PNG}, "the picture gear.png is not in the set"),
        (
            {"panel.json": ELITE, "cover.png": PNG, "gear.png": b"MZ not a picture"},
            "gear.png: not a",
        ),
        ({"panel.json": ELITE, "cover.png": PNG, "a/gear.png": PNG, "b/gear.png": PNG}, "twice"),
        ({"panel.json": ELITE | {"buttons": [{"id": "x", "keys": "Nope"}]}}, "panel.json: buttons"),
        ({"panel.json": ELITE, "cover.png": PNG, "gear.png": PNG + b"0" * 2_000_000}, "too large"),
    ],
)
def test_a_bad_set_is_refused_and_leaves_nothing(client, state, files, problem):
    body = b"just some bytes" if files is None else zipped(files)
    reply = client.post("/api/sets", content=body, headers=ZIP)
    assert reply.status_code == 422 and problem in reply.json()["error"], reply.json()
    assert "\\" not in reply.json()["error"] and "/" not in reply.json()["error"]  # no paths
    assert [p.name for p in state.settings.panels_dir.iterdir()] == ["demo"]


def test_a_set_cannot_write_outside_its_folder(client, state):
    files = {
        "panel.json": ELITE,
        "cover.png": PNG,
        "../../gear.png": PNG,
        "..\\..\\escape.png": PNG,
        "/abs/evil.png": PNG,
    }
    assert client.post("/api/sets", content=zipped(files), headers=ZIP).status_code == 201
    panels = state.settings.panels_dir
    assert sorted(p.name for p in (panels / "elite").iterdir()) == [
        "cover.png",
        "gear.png",
        "panel.json",
    ]
    strays = [p for p in panels.parent.rglob("*.png") if panels / "elite" not in p.parents]
    assert strays == []


def test_import_needs_the_editors_origin(client):
    assert client.post("/api/sets", content=zipped({"panel.json": ELITE})).status_code == 403


OWN_WORDS = r"[\w .-]+\.(json|png): |not a zip file this program can read$|there is no panel\.json"


def test_a_damaged_zip_is_refused_not_a_crash(client):
    out = io.BytesIO()
    noise = bytes(random.Random(1).randrange(256) for _ in range(20_000)) + b"abc" * 5_000
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("panel.json", json.dumps(ELITE))
        archive.writestr("cover.png", PNG + noise)
        archive.writestr("gear.png", PNG + noise)
    good = out.getvalue()
    flip = random.Random(7)
    seen = set()
    for _ in range(300):
        damaged = bytearray(good)
        for _ in range(flip.randint(1, 4)):
            damaged[flip.randrange(len(damaged))] ^= 1 << flip.randrange(8)
        reply = client.post("/api/sets?same_name=add", content=bytes(damaged), headers=ZIP)
        seen.add(reply.status_code)
        assert reply.status_code in (201, 422), reply.text
        # The reason is in this program's words: it names a file of the set or the zip.
        said = reply.json().get("error", "")
        assert reply.status_code == 201 or re.match(OWN_WORDS, said), said
    assert seen == {201, 422}  # the damage did reach the data, and some of it is harmless
    assert client.post("/api/sets", content=good[: len(good) // 2], headers=ZIP).status_code == 422


def test_an_import_that_cannot_be_written_says_so_and_leaves_nothing(client, state, monkeypatch):
    def refused(source, target):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr("game_remote.panels.os.replace", refused)
    files = {"panel.json": ELITE, "cover.png": PNG, "gear.png": PNG}
    reply = client.post("/api/sets", content=zipped(files), headers=ZIP)
    assert reply.status_code == 500
    assert reply.json() == {"error": "the game was not written: Access is denied"}
    assert [p.name for p in state.settings.panels_dir.iterdir()] == ["demo"]
    assert client.get("/api/panels").json()["errors"] == {}


def test_a_game_with_a_lost_picture_is_exported_as_a_whole_set(client, state):
    files = {"panel.json": ELITE, "cover.png": PNG, "gear.png": PNG}
    client.post("/api/sets", content=zipped(files), headers=ZIP)
    (state.settings.panels_dir / "elite" / "gear.png").unlink()

    exported = client.get("/api/panels/elite/export").content
    with zipfile.ZipFile(io.BytesIO(exported)) as archive:
        assert sorted(archive.namelist()) == ["cover.png", "panel.json"]
    again = client.post("/api/sets?same_name=add", content=exported, headers=ZIP)
    assert again.status_code == 201
    copy = again.json()["panels"][-1]
    assert (copy["cover"], copy["buttons"][0]["image"]) == ("cover.png", None)


def test_the_size_of_an_upload_is_counted_not_believed(client, state, monkeypatch):
    # A body sent in pieces declares no size at all.
    monkeypatch.setattr("game_remote.server.editor.MAX_SET_BYTES", 1000)
    pieces = (b"x" * 300 for _ in range(5))
    reply = client.post("/api/sets", content=pieces, headers=ZIP)
    assert (reply.status_code, reply.json()) == (413, {"error": "the file is too large"})
    monkeypatch.setattr("game_remote.server.editor.MAX_IMAGE_BYTES", 1000)
    pieces = (b"x" * 300 for _ in range(5))
    reply = client.post("/api/panels/demo/images", content=pieces, headers=ORIGIN)
    assert (reply.status_code, reply.json()) == (413, {"error": "too_large"})


def test_a_zip_this_program_cannot_open_is_not_called_damaged(client):
    good = zipped({"panel.json": ELITE, "cover.png": PNG, "gear.png": PNG})

    def with_headers(local_offset, central_offset, value):
        """The zip with one field changed in the header of every file."""
        data = bytearray(good)
        for magic, offset in ((b"PK\x03\x04", local_offset), (b"PK\x01\x02", central_offset)):
            at = data.find(magic)
            while at != -1:
                struct.pack_into("<H", data, at + offset, value)
                at = data.find(magic, at + 4)
        return bytes(data)

    for body, reason in (
        (with_headers(6, 8, 1), "has a password"),  # the flag "encrypted"
        (with_headers(8, 10, 98), "packed in a way this program cannot read"),  # PPMd of 7-Zip
    ):
        reply = client.post("/api/sets", content=body, headers=ZIP)
        assert reply.status_code == 422 and reason in reply.json()["error"], reply.json()


def test_an_import_asks_before_it_touches_a_game_of_the_same_name(client, state):
    files = {"panel.json": ELITE, "cover.png": PNG, "gear.png": PNG}
    russian = {"panel.ru.json": {"name": "Элита"}}
    panels = state.settings.panels_dir
    assert client.post("/api/sets", content=zipped(files), headers=ZIP).json()["id"] == "elite"

    # The same set again: the PC changes nothing and names the game that is in the way.
    asked = client.post("/api/sets", content=zipped(files), headers=ZIP)
    assert (asked.status_code, asked.json()) == (
        409,
        {"error": "same_name", "id": "elite", "name": "Elite"},
    )
    assert sorted(p.name for p in panels.iterdir()) == ["demo", "elite"]
    # It is the name the game would get that counts, whatever the letters' case.
    lower = {**files, "panel.json": ELITE | {"name": "  elite "}}
    assert client.post("/api/sets", content=zipped(lower), headers=ZIP).status_code == 409
    other = client.post("/api/sets?languages=ru", content=zipped(files | russian), headers=ZIP)
    assert (other.status_code, other.json()["panels"][-1]["name"]) == (201, "Элита")

    # "Add": the set stands next to the game.
    added = client.post("/api/sets?same_name=add", content=zipped(files), headers=ZIP)
    assert (added.status_code, added.json()["id"]) == (201, "elite-3")

    # "Replace": the set takes the place and the id of the game, which goes to the trash.
    changed = {**files, "panel.json": ELITE | {"columns": 5}}
    replaced = client.post("/api/sets?same_name=replace", content=zipped(changed), headers=ZIP)
    assert (replaced.status_code, replaced.json()["id"]) == (201, "elite")
    assert json.loads(panel_file(state, "elite").read_text(encoding="utf-8"))["columns"] == 5
    assert sorted(p.name for p in panels.iterdir()) == ["demo", "elite", "elite-2", "elite-3"]
    (trashed,) = state.settings.trash_dir.iterdir()
    assert trashed.name.startswith("elite-") and (trashed / "gear.png").read_bytes() == PNG

    # Without a game of that name there is nothing to ask or to replace.
    fresh = {**files, "panel.json": ELITE | {"name": "Frontier"}}
    for answer in ("ask", "replace"):
        reply = client.post(f"/api/sets?same_name={answer}", content=zipped(fresh), headers=ZIP)
        assert reply.status_code == 201
        client.delete(f"/api/panels/{reply.json()['id']}", headers=ORIGIN)
    wrong = client.post("/api/sets?same_name=maybe", content=zipped(files), headers=ZIP)
    assert wrong.status_code == 422


def test_a_replaced_picture_of_the_same_name_gets_a_new_address(client, state):
    """A page that is open keeps a picture it has for an address. So the address
    changes with the file: here the set that replaces a game brings another
    gear.png."""
    files = {"panel.json": ELITE, "cover.png": PNG, "gear.png": PNG}
    client.post("/api/sets", content=zipped(files), headers=ZIP)
    phone = TestClient(create_remote_app(state), client=("192.168.1.50", 50000))

    def addresses():
        public = next(p for p in state.store.public() if p["id"] == "elite")
        editor = client.get("/api/panels").json()["versions"]["elite"]
        return public["buttons"][0]["image"], editor["gear.png"]

    before = addresses()
    assert before[0].startswith("/panel-files/elite/gear.png?v=")
    # Nothing changed: the address stays, and the picture is not fetched again.
    client.put("/api/panels/elite", json=ELITE | {"columns": 4, "language": None}, headers=ORIGIN)
    assert addresses() == before

    folder = state.settings.panels_dir / "elite"
    old = (folder / "gear.png").stat().st_mtime
    os.utime(folder / "gear.png", (old - 60, old - 60))  # the old file is a minute older
    before = addresses()
    newer = {**files, "gear.png": PNG + b"\x01"}
    client.post("/api/sets?same_name=replace", content=zipped(newer), headers=ZIP)
    after = addresses()
    assert after[0] != before[0] and after[1] != before[1]
    assert phone.get(after[0]).content == PNG + b"\x01"


def test_a_replacement_that_fails_leaves_the_game_where_it_was(client, state, monkeypatch):
    files = {"panel.json": ELITE, "cover.png": PNG, "gear.png": PNG}
    client.post("/api/sets", content=zipped(files), headers=ZIP)
    before = panel_file(state, "elite").read_text(encoding="utf-8")

    def refused(source, target):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr("game_remote.panels.os.replace", refused)
    changed = {**files, "panel.json": ELITE | {"columns": 5}}
    reply = client.post("/api/sets?same_name=replace", content=zipped(changed), headers=ZIP)
    assert reply.status_code == 500
    monkeypatch.undo()
    assert panel_file(state, "elite").read_text(encoding="utf-8") == before
    assert sorted(p.name for p in state.settings.panels_dir.iterdir()) == ["demo", "elite"]
    assert not list(state.settings.trash_dir.iterdir())
    panels = client.get("/api/panels").json()
    assert [p["id"] for p in panels["panels"]] == ["demo", "elite"] and panels["errors"] == {}
