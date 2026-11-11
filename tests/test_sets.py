"""The catalogue of sets and the tool that checks and packs it."""

import importlib.util
import io
import json
import zipfile
from pathlib import Path

import pytest

from game_remote.panels import PanelStore

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_sets", ROOT / "tools" / "build_sets.py")
build_sets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_sets)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
ELITE = {
    "name": "Elite",
    "language": "en",
    "cover": "cover.png",
    "buttons": [{"id": "gear", "label": "Gear", "keys": "KeyN"}],
}


def write_set(root, name="elite", panel=ELITE, **files):
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "panel.json").write_text(json.dumps(panel), encoding="utf-8")
    for file_name, content in {"cover.png": PNG, **files}.items():
        text = content if isinstance(content, bytes) else json.dumps(content).encode("utf-8")
        (folder / file_name.replace("_", ".")).write_bytes(text)
    return folder


def test_every_set_of_the_catalogue_can_be_imported(capsys):
    assert build_sets.main([]) == 0, capsys.readouterr().out
    # The set inside the program is a part of the catalogue.
    assert "ok   star-citizen" in capsys.readouterr().out


def test_a_set_is_packed_into_a_zip_the_program_imports(tmp_path):
    russian = {"name": "Элита", "labels": {"gear": "Шасси"}}
    notes = b"The cover is my own drawing."
    folder = write_set(tmp_path / "sets", panel_ru_json=russian, README_md=notes)
    assert build_sets.main([str(tmp_path / "out")], sources=(tmp_path / "sets",)) == 0

    data = (tmp_path / "out" / "elite.zip").read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        # The notes of the author stay in the catalogue; a user gets the set alone.
        assert archive.namelist() == ["cover.png", "panel.json", "panel.ru.json"]
    assert build_sets.build(folder) == data  # the same set gives the same zip

    store = PanelStore(tmp_path / "panels")
    store.root.mkdir()
    assert store.import_set(data, "ru") == "elite"
    assert store.panels["elite"].panel.buttons[0].label == "Шасси"


@pytest.mark.parametrize(
    ("name", "panel", "files", "problem"),
    [
        ("Elite", ELITE, {}, "name the folder with small Latin letters"),
        ("elite_2", ELITE, {}, "name the folder with small Latin letters"),
        ("elite", ELITE | {"language": None}, {}, "say the language of the texts"),
        ("elite", ELITE, {"spare.png": PNG}, "spare.png: the set does not use this file"),
        ("elite", ELITE, {"notes.txt": b"hello"}, "notes.txt: the set does not use this file"),
        ("elite", ELITE, {"cover.png": b"MZ not a picture"}, "cover.png: not a PNG"),
        ("elite", ELITE, {"panel_ru_json": {"labels": {"map": "Карта"}}}, "no button 'map'"),
        ("elite", ELITE | {"buttons": [{"id": "a", "keys": "Nope"}]}, {}, "panel.json: buttons"),
    ],
)
def test_a_set_with_a_mistake_fails_the_check(tmp_path, capsys, name, panel, files, problem):
    panel = {key: value for key, value in panel.items() if value is not None}
    write_set(tmp_path / "sets", name, panel, **files)
    write_set(tmp_path / "sets", "good")
    assert build_sets.main([str(tmp_path / "out")], sources=(tmp_path / "sets",)) == 1
    said = capsys.readouterr().out
    assert f"FAIL {name}: " in said and problem in said, said
    # The other sets are still checked and packed; the wrong one is not offered.
    assert [path.name for path in (tmp_path / "out").iterdir()] == ["good.zip"]


def test_two_sets_cannot_share_a_name(tmp_path, capsys):
    write_set(tmp_path / "sets")
    write_set(tmp_path / "samples")
    assert build_sets.main([], sources=(tmp_path / "sets", tmp_path / "samples")) == 1
    assert "FAIL elite: two sets have this name" in capsys.readouterr().out
