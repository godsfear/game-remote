"""Choices the user makes in the editor, kept in ``settings.json``."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from game_remote.files import replace_file

log = logging.getLogger(__name__)

Language = Literal["auto", "en", "ru"]


class UserSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # "auto": every device uses the language of its own browser.
    language: Language = "auto"
    # Ask GitHub now and then whether a newer version of the program is out.
    check_updates: bool = True
    # Ready-made panels that were already put into the panels folder. One the
    # user deleted is not installed again.
    samples: list[str] = Field(default_factory=list)

    @property
    def forced_language(self) -> str | None:
        return None if self.language == "auto" else self.language


def load_user_settings(path: Path) -> UserSettings:
    try:
        return UserSettings.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))
    except FileNotFoundError:
        return UserSettings()
    except (OSError, ValueError, ValidationError) as exc:
        log.warning("Settings were not read, using defaults: %s", exc)
        return UserSettings()


def save_user_settings(path: Path, settings: UserSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(settings.model_dump(), indent=2) + "\n", encoding="utf-8")
    replace_file(temporary, path)
