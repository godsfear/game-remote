import json
import sys

import pytest
from pydantic import ValidationError

from game_remote.config import Settings
from game_remote.panels import SAMPLE_ID, Button, Panel, PanelStore, demo_panel, sample_panel
from game_remote.state import build_state
from game_remote.web import sample_dir


def write_panel(root, panel_id, data):
    folder = root / panel_id
    folder.mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else json.dumps(data)
    (folder / "panel.json").write_text(text, encoding="utf-8")
    return folder


MINIMAL = {"name": "X4", "buttons": [{"id": "map", "label": "Map", "keys": "KeyM"}]}


def started(data_dir):
    """What the program has in its data folder after a start."""
    settings = Settings(data_dir=data_dir, editor_port=8730, remote_port=8731, open_browser=False)
    state = build_state(settings, fake_input=True)
    state.devices.close()
    return state


def test_first_start_installs_the_ready_made_panel_with_its_pictures(tmp_path):
    state = started(tmp_path)
    assert list(state.store.panels) == [SAMPLE_ID]
    assert state.store.errors == {}
    loaded = state.store.panels[SAMPLE_ID]
    assert loaded.panel.name == "Star Citizen"
    assert [(b.id, b.keys, b.type) for b in loaded.panel.buttons] == [
        ("flight-ready", "AltRight+KeyR", "tap"),
        ("atc", "AltLeft+KeyN", "tap"),
        ("landing-gear", "KeyN", "tap"),
        ("headlights", "KeyL", "tap"),
        ("vtol", "KeyK", "tap"),
        ("starmap", "F2", "tap"),
    ]
    # Not tied to the game's window, so the first check in Notepad works.
    assert loaded.panel.window is None
    pictures = [b.image for b in loaded.panel.buttons] + [loaded.panel.background]
    assert len(set(pictures)) == 7
    for name in pictures:
        assert loaded.image_path(name).read_bytes()[:2] == b"\xff\xd8", name
    public = loaded.public()
    assert public["shape"] == "square"
    assert public["background"] == f"/panel-files/{SAMPLE_ID}/background.jpg"
    assert public["buttons"][0]["image"] == f"/panel-files/{SAMPLE_ID}/flight-ready.jpg"
    assert sorted(p.name for p in (tmp_path / "panels").iterdir()) == [SAMPLE_ID]


def test_every_packaged_picture_belongs_to_the_ready_made_panel():
    panel = sample_panel(russian=False)
    used = {b.image for b in panel.buttons} | {panel.background}
    assert {p.name for p in sample_dir(SAMPLE_ID).iterdir()} == used


def test_a_deleted_ready_made_panel_does_not_come_back(tmp_path):
    state = started(tmp_path)
    assert state.store.delete(SAMPLE_ID)
    assert list(started(tmp_path).store.panels) == []


def test_the_ready_made_panel_appears_next_to_the_users_panels_once(tmp_path):
    write_panel(tmp_path / "panels", "x4", MINIMAL)
    assert list(started(tmp_path).store.panels) == [SAMPLE_ID, "x4"]


def test_an_edited_ready_made_panel_is_left_alone(tmp_path):
    started(tmp_path)
    folder = write_panel(tmp_path / "panels", SAMPLE_ID, MINIMAL)
    (tmp_path / "settings.json").unlink()  # as if the mark that it was installed got lost
    assert started(tmp_path).store.panels[SAMPLE_ID].panel.name == "X4"
    assert json.loads((folder / "panel.json").read_text(encoding="utf-8")) == MINIMAL


@pytest.mark.parametrize("russian", [True, False])
def test_untouched_demo_of_the_earlier_version_gives_way(tmp_path, russian):
    old = demo_panel(russian).model_dump(exclude_none=True)
    write_panel(tmp_path / "panels", "demo", old)
    assert list(started(tmp_path).store.panels) == [SAMPLE_ID]
    # Nothing is deleted for good: the folder lies in the trash.
    (kept,) = (tmp_path / "trash").iterdir()
    assert json.loads((kept / "panel.json").read_text(encoding="utf-8")) == old


def test_demo_as_the_earlier_version_wrote_it_is_recognised(tmp_path):
    # Version 0.1.0 before this change wrote the file exactly like this.
    text = json.dumps(demo_panel(True).model_dump(exclude_none=True), ensure_ascii=False, indent=2)
    write_panel(tmp_path / "panels", "demo", text + "\n")
    assert list(started(tmp_path).store.panels) == [SAMPLE_ID]


@pytest.mark.parametrize("change", ["renamed", "picture"])
def test_an_edited_demo_stays(tmp_path, change):
    old = demo_panel(russian=False).model_dump(exclude_none=True)
    if change == "renamed":
        old["name"] = "My game"
    folder = write_panel(tmp_path / "panels", "demo", old)
    if change == "picture":
        (folder / "img-1.png").write_bytes(b"\x89PNG")
    assert list(started(tmp_path).store.panels) == ["demo", SAMPLE_ID]
    assert not (tmp_path / "trash").exists() or not list((tmp_path / "trash").iterdir())


@pytest.mark.parametrize("russian", [True, False])
def test_packaged_panels_are_valid_in_both_languages(russian):
    for panel in (demo_panel(russian), sample_panel(russian)):
        assert Panel.model_validate(panel.model_dump()) == panel


def test_background_and_shape_are_checked():
    assert Panel.model_validate(MINIMAL).shape == "fill"
    assert Panel.model_validate(MINIMAL | {"shape": "square", "background": "img-1.webp"})
    for bad in ({"shape": "round"}, {"background": "../secret.png"}, {"background": "panel.json"}):
        with pytest.raises(ValidationError):
            Panel.model_validate(MINIMAL | bad)


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
@pytest.mark.parametrize(
    ("lang", "label"), [("ru_RU.UTF-8", "Шасси"), ("de_DE.UTF-8", "Landing gear")]
)
def test_ready_made_panel_follows_the_system_language(tmp_path, monkeypatch, lang, label):
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.setenv("LANG", lang)
    store = PanelStore(tmp_path)
    assert store.install_sample()
    assert not store.install_sample()
    store.load()
    assert store.panels[SAMPLE_ID].panel.buttons[2].label == label


def test_a_game_named_like_a_windows_device_gets_a_usable_folder(tmp_path):
    store = PanelStore(tmp_path / "panels")
    assert store.create("CON") == "game-con"
    assert store.create("Com1") == "game-com1"
    assert store.create("Console") == "console"
