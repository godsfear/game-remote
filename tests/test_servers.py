from fastapi.testclient import TestClient

from game_remote.config import Settings
from game_remote.input import InputController, RecordingBackend
from game_remote.server.editor import create_editor_app
from game_remote.server.remote import create_remote_app


def settings(tmp_path):
    return Settings(data_dir=tmp_path, editor_port=8730, remote_port=8731, open_browser=False)


def editor_client(tmp_path):
    return TestClient(create_editor_app(settings(tmp_path)), base_url="http://127.0.0.1:8730")


def test_editor_health_and_page(tmp_path):
    client = editor_client(tmp_path)
    assert client.get("/api/health").json()["app"] == "editor"
    page = client.get("/")
    assert page.status_code == 200
    assert "Game Remote" in page.text


def test_editor_rejects_foreign_host(tmp_path):
    client = editor_client(tmp_path)
    resp = client.get("/api/health", headers={"host": "evil.example:8730"})
    assert resp.status_code == 403


def test_editor_rejects_cross_site_writes(tmp_path):
    client = editor_client(tmp_path)
    resp = client.post("/api/health", headers={"origin": "http://evil.example"})
    assert resp.status_code == 403
    same = client.post("/api/health", headers={"origin": "http://127.0.0.1:8730"})
    assert same.status_code == 405  # allowed through, the route only has GET


def test_remote_health(tmp_path):
    app = create_remote_app(settings(tmp_path), InputController(RecordingBackend()))
    client = TestClient(app)
    assert client.get("/api/health").json()["app"] == "remote"
    assert client.get("/").status_code == 200


def test_settings_paths(tmp_path):
    s = settings(tmp_path)
    s.ensure_dirs()
    assert s.log_dir.is_dir() and s.images_dir.is_dir()
    assert s.editor_url == "http://127.0.0.1:8730/"
    assert s.editor_host == "127.0.0.1"
