import io
import json
import sys
import zipfile

import pytest
from pydantic import ValidationError

from game_remote.config import Settings
from game_remote.panels import (
    SAMPLE_ID,
    Button,
    Panel,
    PanelStore,
    demo_panel,
    read_set,
    unpack_set,
)
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
    assert [(b.id, b.keys, b.type) for b in loaded.panel.buttons if b.screen == 0] == [
        ("flight-ready", "AltRight+KeyR", "tap"),
        ("atc", "AltLeft+KeyN", "tap"),
        ("landing-gear", "KeyN", "tap"),
        ("headlights", "KeyL", "tap"),
        ("vtol", "KeyK", "tap"),
        ("starmap", "F2", "tap"),
    ]
    # Not tied to the game's window, so the first check in Notepad works.
    assert loaded.panel.window is None
    # Three screens show how buttons are grouped: six on each.
    assert [[b.screen for b in loaded.panel.buttons].count(n) for n in range(3)] == [6, 6, 6]
    assert len(loaded.panel.screens) == 3
    # The keys the game wants held down are held for as long as the finger is.
    assert [b.id for b in loaded.panel.buttons if b.type == "hold"] == ["master-mode", "radar-ping"]
    assert loaded.image_path(loaded.panel.cover).read_bytes()[:2] == b"\xff\xd8"
    pictures = [b.image for b in loaded.panel.buttons] + [loaded.panel.background]
    assert len(set(pictures)) == 19
    for name in pictures:
        assert loaded.image_path(name).read_bytes()[:2] == b"\xff\xd8", name
    public = loaded.public()
    assert public["shape"] == "square"
    assert public["background"].split("?")[0] == f"/panel-files/{SAMPLE_ID}/background.jpg"
    image = public["buttons"][0]["image"]
    assert image.split("?")[0] == f"/panel-files/{SAMPLE_ID}/flight-ready.jpg"
    assert sorted(p.name for p in (tmp_path / "panels").iterdir()) == [SAMPLE_ID]


def test_every_packaged_picture_belongs_to_the_ready_made_panel():
    used = read_set(sample_dir(SAMPLE_ID)).panel.images()
    texts = {"panel.json", "panel.ru.json"}
    assert {p.name for p in sample_dir(SAMPLE_ID).iterdir()} == used | texts


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
    sample = read_set(sample_dir(SAMPLE_ID)).in_language("ru" if russian else "en")
    assert sample.language is None
    for panel in (demo_panel(russian), sample):
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
        {"id": "map", "label": "Map", "type": "tap", "color": None, "image": None, "screen": 0}
    ]
    assert "KeyM" not in json.dumps(public)


def test_buttons_are_grouped_into_screens(tmp_path):
    # A panel without screens is one screen: files of earlier versions stay valid.
    plain = Panel.model_validate(MINIMAL)
    assert plain.screens == [] and plain.buttons[0].screen == 0

    data = {
        "name": "SC",
        "screens": ["Flight", "Combat"],
        "buttons": [
            {"id": "gear", "keys": "KeyN"},
            {"id": "missile", "keys": "KeyG", "screen": 1},
        ],
    }
    write_panel(tmp_path, "sc", data)
    store = PanelStore(tmp_path)
    store.load()
    public = store.public()[0]
    assert public["screens"] == ["Flight", "Combat"]
    assert [button["screen"] for button in public["buttons"]] == [0, 1]

    # Only a panel that has screens carries their fields in its file, so the
    # version before screens still reads what this one writes.
    store.save("sc", store.get("sc").panel)
    store.save("x4", plain)
    assert '"screen": 1' in (tmp_path / "sc" / "panel.json").read_text(encoding="utf-8")
    assert "screen" not in (tmp_path / "x4" / "panel.json").read_text(encoding="utf-8")

    for bad in (
        {"screens": ["Flight"]},  # the second button is on a screen that is not there
        {"screens": []},
        {"screens": ["Flight", ""]},
        {"screens": [f"s{n}" for n in range(9)]},
    ):
        with pytest.raises(ValidationError):
            Panel.model_validate(data | bad)


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
    assert loaded.public()["buttons"][0]["image"].split("?")[0] == "/panel-files/x4/map.png"


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


SET = {
    "name": "Elite",
    "language": "de",
    "cover": "cover.png",
    "screens": ["Flug", "Kampf"],
    "buttons": [
        {"id": "gear", "label": "Fahrwerk", "keys": "KeyN"},
        {"id": "fire", "label": "Feuer", "keys": "KeyG", "screen": 1},
    ],
}
RUSSIAN = {"name": "Элита", "screens": ["Полёт", "Бой"], "labels": {"gear": "Шасси"}}


def write_set(root, panel=SET, **translations):
    folder = write_panel(root, "elite", panel)
    (folder / "cover.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    for language, texts in translations.items():
        (folder / f"panel.{language}.json").write_text(json.dumps(texts), encoding="utf-8")
    return folder


def test_a_set_becomes_a_panel_in_one_language(tmp_path):
    shared = read_set(write_set(tmp_path / "shared", ru=RUSSIAN, en={"labels": {"gear": "Gear"}}))

    def labels(panel):
        return [button.label for button in panel.buttons]

    # The user's language if the set has it. A button without a translation
    # keeps the label of the author.
    russian = shared.in_language("ru")
    assert (russian.name, russian.screens, labels(russian)) == (
        "Элита",
        ["Полёт", "Бой"],
        ["Шасси", "Feuer"],
    )
    # The language of panel.json itself counts as one the set has.
    assert labels(shared.in_language("de")) == ["Fahrwerk", "Feuer"]
    # Else English, and without English what the author wrote.
    assert labels(shared.in_language("fr")) == ["Gear", "Feuer"]
    only_russian = read_set(write_set(tmp_path / "other", ru=RUSSIAN))
    assert labels(only_russian.in_language("fr")) == ["Fahrwerk", "Feuer"]
    # Several languages are tried in the order the user reads them.
    assert labels(shared.in_language("fr", "ru", "en")) == ["Шасси", "Feuer"]
    assert labels(shared.in_language("fr", "de", "ru")) == ["Fahrwerk", "Feuer"]
    assert labels(shared.in_language()) == ["Gear", "Feuer"]

    # In the user's folder it is a plain panel: its pictures, one language.
    store = PanelStore(tmp_path / "panels")
    store.install_set(shared, "elite", "ru")
    store.load()
    assert store.panels["elite"].panel == russian and russian.language is None
    assert sorted(p.name for p in (tmp_path / "panels" / "elite").iterdir()) == [
        "cover.png",
        "panel.json",
    ]


@pytest.mark.parametrize(
    ("panel", "translations", "problem"),
    [
        (SET, {"ru": RUSSIAN | {"screens": ["Полёт"]}}, "panel.ru.json: the panel has 2 screens"),
        (SET, {"ru": {"labels": {"map": "Карта"}}}, "panel.ru.json: the panel has no button 'map'"),
        (SET, {"ru": {"keys": "KeyM"}}, "panel.ru.json: keys"),
        (SET, {"de": {"name": "Elite"}}, "panel.de.json: panel.json is in this language"),
        (SET, {"rus": RUSSIAN}, "panel.rus.json: a translation is called like"),
        (SET | {"background": "space.png"}, {}, "panel.json: the picture space.png"),
        (SET | {"language": "german"}, {}, "panel.json: language"),
    ],
)
def test_a_set_with_a_mistake_names_the_file(tmp_path, panel, translations, problem):
    with pytest.raises(ValueError, match=problem):
        read_set(write_set(tmp_path, panel, **translations))


def test_a_set_that_cannot_be_moved_in_leaves_no_draft(tmp_path, monkeypatch):
    def refused(source, target):
        raise PermissionError(13, "Access is denied")

    shared = read_set(write_set(tmp_path / "shared"))
    store = PanelStore(tmp_path / "panels")
    store.root.mkdir()
    monkeypatch.setattr("game_remote.files.os.replace", refused)
    with pytest.raises(PermissionError):
        store.install_set(shared, "elite", "en")
    assert list(store.root.iterdir()) == []

    # A draft that a crash left behind is not taken for a game.
    write_panel(store.root, ".elite.tmp", MINIMAL)
    store.load()
    assert store.panels == {} and store.errors == {}


def test_a_zip_cannot_write_to_a_device_of_windows(tmp_path):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("panel.json", json.dumps(MINIMAL))
        for name in ("con.png", "CON .png", "aux.jpg", "Com1.webp", "lpt9  .png", "nul.json"):
            archive.writestr(name, b"\x89PNG\r\n\x1a\n")
        archive.writestr("console.png", b"\x89PNG\r\n\x1a\n")  # only looks like one
    unpack_set(out.getvalue(), tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["console.png", "panel.json"]


def test_the_watcher_leaves_an_import_alone(tmp_path, monkeypatch):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("panel.json", json.dumps(MINIMAL))
    store = PanelStore(tmp_path / "panels")
    store.root.mkdir()
    store.load()
    seen = []
    install = store.install_set

    def install_and_look(*args, **options):
        install(*args, **options)
        # The folder is there and the import has not read it yet: the watcher
        # must not announce the panel a second time.
        seen.append(store.reload_if_changed())

    monkeypatch.setattr(store, "install_set", install_and_look)
    assert store.import_set(out.getvalue(), "en") == "x4"
    assert seen == [False] and list(store.panels) == ["x4"]
    assert not store.reload_if_changed()
    # A refused file does not leave the watcher switched off.
    with pytest.raises(ValueError, match="not a zip"):
        store.import_set(b"nothing", "en")
    write_panel(store.root, "second", MINIMAL)
    assert store.reload_if_changed()


def test_the_program_starts_without_a_ready_made_panel_it_cannot_read(tmp_path, monkeypatch):
    def unreadable(folder):
        raise ValueError("panel.json: Permission denied")

    monkeypatch.setattr("game_remote.panels.read_set", unreadable)
    state = started(tmp_path)
    assert state.store.panels == {}
    # Not marked as installed: the next start tries again.
    assert not (tmp_path / "settings.json").exists()


def test_a_game_named_like_a_windows_device_gets_a_usable_folder(tmp_path):
    store = PanelStore(tmp_path / "panels")
    assert store.create("CON") == "game-con"
    assert store.create("Com1") == "game-com1"
    assert store.create("Console") == "console"
