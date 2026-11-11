"""Checks the sets of the catalogue and packs each one into a zip.

    python tools/build_sets.py              # check only
    python tools/build_sets.py dist/sets    # check, then write <name>.zip of every set

The catalogue is the folder ``sets`` and the set that ships inside the
program. A set passes when the program itself imports its zip in every
language the set has: the check is the same code a user's import runs, so
what the catalogue offers can be imported. On top of that a set of the
catalogue says its language and holds no file it does not use.
"""

from __future__ import annotations

import io
import re
import sys
import tempfile
import zipfile
from pathlib import Path

from game_remote.panels import MAX_SET_BYTES, PANEL_FILE, PanelStore, read_set

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (ROOT / "sets", ROOT / "src" / "game_remote" / "samples")
# The name of the folder is the name of the zip and of the game's folder on a PC.
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Notes of the author: where the pictures come from, what the keys assume.
NOTES = "README.md"


def build(folder: Path) -> bytes:
    """The zip of the set in ``folder``. A ValueError says what is wrong with it."""
    if not NAME.match(folder.name) or len(folder.name) > 40:
        raise ValueError("name the folder with small Latin letters, digits and -")
    panel_set = read_set(folder)
    if panel_set.panel.language is None:
        raise ValueError(f'{PANEL_FILE}: say the language of the texts, e.g. "language": "en"')
    files = {PANEL_FILE, *panel_set.panel.images()}
    files.update(f"panel.{language}.json" for language in panel_set.translations)
    unused = sorted(path.name for path in folder.iterdir() if path.name not in files | {NOTES})
    if unused:
        raise ValueError(f"{unused[0]}: the set does not use this file")

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            # A fixed date: the same set gives the same zip, whenever it is built.
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, (folder / name).read_bytes())
    data = out.getvalue()
    if len(data) > MAX_SET_BYTES:
        raise ValueError("the set is larger than the program imports")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        store = PanelStore(Path(temporary))
        for language in (panel_set.panel.language, *panel_set.translations):
            store.import_set(data, language)
    return data


def catalogue(sources: tuple[Path, ...] = SOURCES) -> list[Path]:
    """The folders of the sets, by name."""
    folders = [path for source in sources if source.is_dir() for path in source.iterdir()]
    return sorted((path for path in folders if path.is_dir()), key=lambda path: path.name)


def main(argv: list[str], sources: tuple[Path, ...] = SOURCES) -> int:
    if len(argv) > 1:
        print(__doc__)
        return 2
    target = Path(argv[0]) if argv else None
    failed = False
    seen: set[str] = set()
    for folder in catalogue(sources):
        try:
            if folder.name in seen:
                raise ValueError("two sets have this name")
            seen.add(folder.name)
            data = build(folder)
        except (OSError, ValueError) as error:
            failed = True
            print(f"FAIL {folder.name}: {error}")
            continue
        print(f"ok   {folder.name}: {len(data)} bytes")
        if target is not None:
            target.mkdir(parents=True, exist_ok=True)
            (target / f"{folder.name}.zip").write_bytes(data)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
