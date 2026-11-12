"""Writing files of the program on Windows."""

from __future__ import annotations

import os
import time
from pathlib import Path


def replace_file(source: Path, target: Path) -> None:
    """``os.replace`` that waits a moment for a file somebody holds: on Windows
    an antivirus or an editor does that to a file that was just written."""
    for attempt in range(5):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05)
