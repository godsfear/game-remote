import importlib.util
from pathlib import Path

import pytest

import game_remote

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_notes", ROOT / "tools" / "release_notes.py")
release_notes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_notes)

SAMPLE = "# Changes\n\n## 0.2.0\n\n- new\n\n## 0.1.0\n\n- first\n- second\n\n## 0.0.9\n"


def test_notes_are_the_section_of_that_version():
    assert release_notes.notes_for("0.1.0", SAMPLE) == "- first\n- second\n"
    assert release_notes.notes_for("0.2.0", SAMPLE) == "- new\n"


@pytest.mark.parametrize("version", ["0.3.0", "0.1", "0.0.9"])
def test_missing_or_empty_notes_stop_the_release(version):
    with pytest.raises(ValueError, match="CHANGELOG"):
        release_notes.notes_for(version, SAMPLE)


def test_the_current_version_has_notes_and_one_number_everywhere(tmp_path):
    version = game_remote.__version__
    assert release_notes.program_version() == version
    assert f'version = "{version}"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    target = tmp_path / "notes.md"
    assert release_notes.main([f"v{version}", str(target)]) == 0
    assert "GameRemote.exe" in target.read_text(encoding="utf-8")
    assert release_notes.main(["v9.9.9", str(target)]) == 1
