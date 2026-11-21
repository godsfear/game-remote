import importlib
import json
import mimetypes
import re

import game_remote.web
from game_remote.web import web_dir

SIGNS = web_dir("shared") / "signs"
# A sign is one outline and nothing else: no script, no link, no colour of its own.
# The ones of Material Design Icons carry its id, the ones drawn here carry none.
SHAPE = re.compile(
    r'<svg xmlns="http://www\.w3\.org/2000/svg"(?: id="mdi-[a-z0-9-]+")? viewBox="0 0 24 24">'
    r'<path d="[MmLlHhVvCcSsQqTtAaZz0-9,.\- ]+" /></svg>\n'
)


def test_the_list_of_signs_and_their_pictures_agree():
    groups = json.loads((SIGNS / "index.json").read_text(encoding="utf-8"))
    names = [name for group in groups for name in group["signs"]]
    assert len(names) == len(set(names))  # one sign stands in one group
    assert sorted(names) == sorted(path.stem for path in SIGNS.glob("*.svg"))
    for group in groups:
        assert group["ru"] and group["en"] and group["signs"]
        for name, texts in group["signs"].items():
            assert re.fullmatch(r"[a-z0-9-]+", name)
            assert set(texts) == {"ru", "en"} and all(texts.values()), name
            assert SHAPE.fullmatch((SIGNS / f"{name}.svg").read_text(encoding="utf-8")), name
        # The search of the editor finds a sign by its name: two signs of a group
        # with one name would be the same action drawn twice. The signs of a
        # ready-made set stand in a group of their own beside the common ones.
        for language in ("ru", "en"):
            texts = [texts[language] for texts in group["signs"].values()]
            assert len(texts) == len(set(texts)), (group["en"], language)


def test_the_registry_of_windows_does_not_decide_what_a_page_file_is():
    """Another program may have written any type for .svg or .js there, and a
    browser draws a sign and runs a script only when they come as what they are."""
    for suffix in (".svg", ".js", ".css"):
        mimetypes.add_type("text/plain", suffix)
    importlib.reload(game_remote.web)
    assert mimetypes.guess_type("power.svg")[0] == "image/svg+xml"
    assert mimetypes.guess_type("app.js")[0] == "text/javascript"
    assert mimetypes.guess_type("style.css")[0] == "text/css"


def test_the_licence_of_the_signs_ships_with_them():
    for name in ("LICENSE", "LICENSE-APACHE-2.0", "NOTICE"):
        assert (SIGNS / name).read_text(encoding="utf-8").strip()
    # The notice tells whose a sign is by its name, so the names must not lie.
    assert 'names begin with "sc-"' in (SIGNS / "NOTICE").read_text(encoding="utf-8")
    for path in SIGNS.glob("*.svg"):
        ours = ' id="mdi-' not in path.read_text(encoding="utf-8")
        assert ours == path.stem.startswith("sc-"), path.name
