"""Writes the notes of one release, taken from CHANGELOG.md.

    python tools/release_notes.py v0.1.0 notes.md

Fails when the tag does not match the version of the program or when the
changelog has no section for it, so a release cannot go out half-described.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def program_version() -> str:
    text = (ROOT / "src" / "game_remote" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__ = "([^"]+)"', text).group(1)


def notes_for(version: str, changelog: str) -> str:
    """The text between the heading of this version and the next heading of the same level."""
    lines = changelog.splitlines()
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if re.match(rf"## \[?{re.escape(version)}\]?(\s|$)", line)
        ),
        None,
    )
    if start is None:
        raise ValueError(f"CHANGELOG.md has no section for {version}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    notes = "\n".join(lines[start + 1 : end]).strip()
    if not notes:
        raise ValueError(f"The section for {version} in CHANGELOG.md is empty")
    return notes + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    tag, target = argv
    version = program_version()
    if tag != f"v{version}":
        print(f"Tag {tag} does not match the program version {version}")
        return 1
    try:
        notes = notes_for(version, (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    except ValueError as error:
        print(error)
        return 1
    Path(target).write_text(notes, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
