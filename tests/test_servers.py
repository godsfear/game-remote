from xml.etree import ElementTree

from conftest import phone_key
from fastapi.testclient import TestClient

from game_remote.config import Settings
from game_remote.input import InputError
from game_remote.server.editor import create_editor_app, phone_links
from game_remote.server.remote import create_remote_app

EDITOR = "http://127.0.0.1:8730"


def editor_client(state):
    return TestClient(create_editor_app(state), base_url=EDITOR)


def test_editor_health_and_page(state):
    client = editor_client(state)
    assert client.get("/api/health").json()["app"] == "editor"
    page = client.get("/")
    assert page.status_code == 200
    assert "Game Remote" in page.text
    assert client.get("/shared/i18n.js").status_code == 200


def test_editor_rejects_foreign_host(state):
    client = editor_client(state)
    resp = client.get("/api/health", headers={"host": "evil.example:8730"})
    assert resp.status_code == 403


def test_editor_rejects_cross_site_writes(state):
    client = editor_client(state)
    for path in ("/api/release-keys", "/api/open-panels-folder"):
        assert client.post(path, headers={"origin": "http://evil.example"}).status_code == 403
        assert client.post(path).status_code == 403  # no Origin at all
    same = client.post("/api/release-keys", headers={"origin": EDITOR})
    assert same.status_code == 200


def test_editor_status_describes_panels_and_phones(state, tmp_path):
    broken = tmp_path / "panels" / "broken"
    broken.mkdir()
    (broken / "panel.json").write_text("{", encoding="utf-8")
    state.store.load()
    status = editor_client(state).get("/api/status").json()
    assert status["phones"] == 0
    assert status["fake_input"] is True
    assert [p["id"] for p in status["panels"]] == ["demo"]
    assert status["panels"][0]["buttons"] == 6
    assert "broken" in status["panel_errors"]
    assert status["panels_dir"] == str(tmp_path / "panels")


def test_editor_never_shows_device_keys(state):
    key = phone_key(state)
    client = editor_client(state)
    for path in ("/api/status", "/api/links", "/api/health"):
        assert key not in client.get(path).text
    # The pairing code is only in the links, which the QR code needs anyway.
    assert state.pairing.current() not in client.get("/api/status").text


def test_qr_code_holds_the_phone_link(state, monkeypatch):
    monkeypatch.setattr("game_remote.server.editor.lan_addresses", lambda: ["192.168.1.10"])
    monkeypatch.setattr("game_remote.server.editor.local_name", lambda: "gamer-pc.local")
    code = state.pairing.current()
    links = phone_links(state)
    assert links == [
        {"kind": "ip", "host": "192.168.1.10", "url": f"http://192.168.1.10:8731/#pair={code}"},
        {
            "kind": "name",
            "host": "gamer-pc.local",
            "url": f"http://gamer-pc.local:8731/#pair={code}",
        },
    ]
    client = editor_client(state)
    assert client.get("/api/links").json() == {"links": links, "pairing": 1}
    first = client.get("/api/qr/0.svg")
    assert first.status_code == 200
    assert first.headers["content-type"].startswith("image/svg+xml")
    assert first.headers["cache-control"] == "no-store"
    # The page shows it with <img>, which needs a complete SVG document.
    root = ElementTree.fromstring(first.content)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.get("width") and root.get("height")
    assert client.get("/api/qr/1.svg").text != first.text
    assert client.get("/api/qr/2.svg").status_code == 404


def test_release_keys_from_the_editor(state):
    remote = TestClient(create_remote_app(state), client=("192.168.1.50", 50000))
    with remote.websocket_connect("/ws") as ws:
        ws.send_json({"type": "hello", "key": phone_key(state)})
        ws.receive_json()
        ws.send_json({"type": "down", "id": 1, "panel": "demo", "button": "forward"})
        ws.receive_json()
        assert editor_client(state).get("/api/status").json()["held_keys"] == ["KeyW"]
        assert editor_client(state).get("/api/status").json()["phones"] == 1
        resp = editor_client(state).post("/api/release-keys", headers={"origin": EDITOR})
        assert resp.json() == {"ok": True}
        assert state.controller.held_keys == set()
        # The phone still thinks the button is down; its "up" must not break anything.
        ws.send_json({"type": "up", "id": 2, "panel": "demo", "button": "forward"})
        assert ws.receive_json()["ok"]
    assert state.backend.trace() == ["+KeyW", "-KeyW"]


def test_release_keys_when_windows_refuses(state, monkeypatch):
    remote = TestClient(create_remote_app(state), client=("192.168.1.50", 50000))
    editor = editor_client(state)
    with remote.websocket_connect("/ws") as ws:
        ws.send_json({"type": "hello", "key": phone_key(state)})
        ws.receive_json()
        ws.send_json({"type": "down", "id": 1, "panel": "demo", "button": "forward"})
        ws.receive_json()

        def fail(events):
            raise InputError("blocked")

        monkeypatch.setattr(state.backend, "send", fail)
        assert editor.post("/api/release-keys", headers={"origin": EDITOR}).json() == {"ok": False}
        # The key may still be down, and the page keeps saying so.
        assert editor.get("/api/status").json()["held_keys"] == ["KeyW"]
        monkeypatch.undo()
        assert editor.post("/api/release-keys", headers={"origin": EDITOR}).json() == {"ok": True}
        assert editor.get("/api/status").json()["held_keys"] == []
    assert state.backend.trace() == ["+KeyW", "-KeyW"]


def test_remote_health_and_page(state):
    client = TestClient(create_remote_app(state), client=("192.168.1.50", 50000))
    assert client.get("/api/health").json()["app"] == "remote"
    page = client.get("/")
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-cache"
    assert client.get("/shared/i18n.js").status_code == 200
    assert client.get("/app.js").status_code == 200


def test_remote_page_can_be_put_on_the_home_screen(state):
    client = TestClient(create_remote_app(state), client=("192.168.1.50", 50000))
    manifest = client.get("/manifest.json").json()
    assert manifest["display"] == "fullscreen" and manifest["start_url"] == "/"
    for icon in manifest["icons"]:
        reply = client.get("/" + icon["src"])
        assert reply.headers["content-type"] == "image/png"
        assert reply.content.startswith(b"\x89PNG")
    assert "<svg" in client.get("/shared/icon.svg").text
    assert 'rel="manifest"' in client.get("/").text


def test_remote_app_has_no_editor_routes(state):
    client = TestClient(create_remote_app(state), client=("192.168.1.50", 50000))
    for path in ("/api/status", "/api/links", "/api/qr/0.svg"):
        assert client.get(path).status_code == 404
    assert client.post("/api/release-keys").status_code in (404, 405)


def test_settings_paths(tmp_path):
    s = Settings(data_dir=tmp_path, editor_port=8730, remote_port=8731, open_browser=False)
    s.ensure_dirs()
    assert s.log_dir.is_dir() and s.panels_dir.is_dir()
    assert s.editor_url == "http://127.0.0.1:8730/"
    assert s.editor_host == "127.0.0.1"
    assert s.remote_url("192.168.1.10", "abc") == "http://192.168.1.10:8731/#pair=abc"


def test_i18n_dictionaries_have_the_same_keys():
    import re

    from game_remote.web import web_dir

    text = (web_dir("shared") / "i18n.js").read_text(encoding="utf-8")
    body = text[text.index("const TEXTS = {") : text.index("\n};")]
    languages = re.split(r"^  (\w+): \{$", body, flags=re.MULTILINE)[1:]
    keys = {
        name: re.findall(r"^    '([\w.]+)': ", block, flags=re.MULTILINE)
        for name, block in zip(languages[::2], languages[1::2], strict=True)
    }
    assert set(keys) == {"en", "ru"}
    assert len(keys["en"]) > 20
    assert sorted(keys["en"]) == sorted(keys["ru"])
    assert len(set(keys["en"])) == len(keys["en"])  # no key is written twice
