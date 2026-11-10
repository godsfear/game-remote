import json
import sys

import pytest
from pydantic import ValidationError

from game_remote.panels import Button, Panel, PanelStore, demo_panel


def write_panel(root, panel_id, data):
    folder = root / panel_id
    folder.mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else json.dumps(data)
    (folder / "panel.json").write_text(text, encoding="utf-8")
    return folder


MINIMAL = {"name": "X4", "buttons": [{"id": "map", "label": "Map", "keys": "KeyM"}]}


def test_demo_panel_is_created_once(tmp_path):
    store = PanelStore(tmp_path / "panels")
    assert store.ensure_demo()
    assert not store.ensure_demo()
    store.load()
    assert list(store.panels) == ["demo"]
    assert store.errors == {}
    types = {b.type for b in store.panels["demo"].panel.buttons}
    assert types == {"tap", "hold"}


def test_demo_is_not_created_next_to_the_users_panels(tmp_path):
    write_panel(tmp_path, "x4", MINIMAL)
    assert not PanelStore(tmp_path).ensure_demo()


@pytest.mark.parametrize("russian", [True, False])
def test_demo_panel_is_valid_in_both_languages(russian):
    panel = demo_panel(russian)
    assert Panel.model_validate(panel.model_dump()) == panel


def test_phone_never_receives_key_combos(tmp_path):
    write_panel(tmp_path, "x4", MINIMAL)
    store = PanelStore(tmp_path)
    store.load()
    public = store.public()
    assert public[0]["id"] == "x4" and public[0]["columns"] == 3
    assert public[0]["buttons"] == [
        {"id": "map", "label": "Map", "type": "tap", "color": None, "image": None}
    ]
    assert "KeyM" not in json.dumps(public)


def test_keys_are_normalised_modifiers_first():
    button = Button(id="radio", keys="KeyR+ControlLeft")
    assert button.keys == "ControlLeft+KeyR"
    assert button.combo.keys == ("ControlLeft", "KeyR")


@pytest.mark.parametrize(
    "data",
    [
        {"name": "x", "buttons": [{"id": "a", "keys": "NoSuchKey"}]},
        {"name": "x", "buttons": [{"id": "a", "keys": ""}]},
        {"name": "x", "buttons": [{"id": "a", "keys": "KeyA"}, {"id": "a", "keys": "KeyB"}]},
        {"name": "x", "buttons": [{"id": "a b", "keys": "KeyA"}]},
        {"name": "x", "buttons": [{"id": "a", "keys": "KeyA", "type": "toggle"}]},
        {"name": "x", "buttons": [{"id": "a", "keys": "KeyA", "image": "../secret.png"}]},
        {"name": "x", "buttons": [{"id": "a", "keys": "KeyA", "color": "red"}]},
        {"name": "x", "buttons": [], "columns": 0},
        {"name": "x", "buttons": [], "macro": "anything"},
        {"name": "x", "buttons": [], "format": 2},
        {"buttons": []},
    ],
)
def test_invalid_panels_are_rejected(data):
    with pytest.raises(ValidationError):
        Panel.model_validate(data)


def test_a_broken_file_does_not_hide_the_other_panels(tmp_path):
    write_panel(tmp_path, "good", MINIMAL)
    write_panel(tmp_path, "broken", "{ not json")
    write_panel(tmp_path, "wrong", {"name": "x", "buttons": [{"id": "a", "keys": "Nope"}]})
    write_panel(tmp_path, "bad name", MINIMAL)
    store = PanelStore(tmp_path)
    store.load()
    assert list(store.panels) == ["good"]
    assert set(store.errors) == {"broken", "wrong", "bad name"}
    assert "buttons.0.keys" in store.errors["wrong"]


def test_file_with_a_byte_order_mark_loads(tmp_path):
    # Notepad on Windows may save UTF-8 with a BOM.
    folder = tmp_path / "x4"
    folder.mkdir()
    (folder / "panel.json").write_bytes(b"\xef\xbb\xbf" + json.dumps(MINIMAL).encode())
    store = PanelStore(tmp_path)
    store.load()
    assert "x4" in store.panels


def test_reload_only_when_files_change(tmp_path):
    folder = write_panel(tmp_path, "x4", MINIMAL)
    store = PanelStore(tmp_path)
    store.load()
    assert not store.reload_if_changed()

    changed = dict(MINIMAL, name="X4: Foundations")
    (folder / "panel.json").write_text(json.dumps(changed), encoding="utf-8")
    assert store.reload_if_changed()
    assert store.panels["x4"].panel.name == "X4: Foundations"

    write_panel(tmp_path, "second", MINIMAL)
    assert store.reload_if_changed()
    assert set(store.panels) == {"x4", "second"}

    (folder / "panel.json").unlink()
    assert store.reload_if_changed()
    assert set(store.panels) == {"second"}


def test_only_images_used_by_a_button_are_served(tmp_path):
    data = {"name": "x", "buttons": [{"id": "a", "keys": "KeyA", "image": "map.png"}]}
    folder = write_panel(tmp_path, "x4", data)
    (folder / "map.png").write_bytes(b"png")
    (folder / "other.png").write_bytes(b"png")
    store = PanelStore(tmp_path)
    store.load()
    loaded = store.panels["x4"]
    assert loaded.image_path("map.png") == folder / "map.png"
    assert loaded.image_path("other.png") is None
    assert loaded.image_path("panel.json") is None
    assert loaded.public()["buttons"][0]["image"] == "/panel-files/x4/map.png"


@pytest.mark.skipif(sys.platform == "win32", reason="Windows asks the system, not the environment")
@pytest.mark.parametrize(("lang", "name"), [("ru_RU.UTF-8", "Демо"), ("de_DE.UTF-8", "Demo")])
def test_demo_panel_follows_the_system_language(tmp_path, monkeypatch, lang, name):
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.setenv("LANG", lang)
    store = PanelStore(tmp_path)
    store.ensure_demo()
    store.load()
    assert store.panels["demo"].panel.name == name
