"""The secret a phone must present before it can press anything.

Milestone 1 uses one secret for all phones; it is part of the link in the QR
code. Milestone 3 replaces it with a one-time code and a key per device.
"""

from __future__ import annotations

import hmac
import secrets
from pathlib import Path

KEY_FILE = "access.key"


def load_or_create_key(data_dir: Path) -> str:
    path = data_dir / KEY_FILE
    if path.is_file():
        key = path.read_text(encoding="ascii").strip()
        if len(key) >= 20:
            return key
    key = secrets.token_urlsafe(24)
    data_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(key + "\n", encoding="ascii")
    return key


def key_matches(expected: str, given: object) -> bool:
    return isinstance(given, str) and hmac.compare_digest(expected.encode(), given.encode())
