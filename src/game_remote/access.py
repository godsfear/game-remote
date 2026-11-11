"""How a phone proves that it may press keys.

The QR code on the PC carries a one-time pairing code. The first phone that
presents it gets a key of its own and the code stops working, so a photo of
the screen or a forwarded link lets nobody else in. The PC keeps only a hash
of each key (see devices.py); the key itself lives in the phone's browser.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import secrets
import time
from collections.abc import Callable
from pathlib import Path

PAIRING_TTL = 300.0  # seconds a code stays valid while nobody uses it
LEGACY_KEY_FILE = "access.key"  # the one key for all phones of the first prototype


def new_device_key() -> str:
    return secrets.token_urlsafe(32)


def key_hash(key: str) -> str:
    # The key is 256 random bits, so a plain hash is enough: there is nothing to guess.
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class PairingCodes:
    """The code inside the QR link. One is valid at a time."""

    def __init__(
        self, ttl: float = PAIRING_TTL, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.ttl = ttl
        self._clock = clock
        self._code: str | None = None
        self._expires = 0.0
        # Grows with every new code; the PC page redraws the QR code when it changes.
        self.serial = 0

    def current(self) -> str:
        """The valid code; a new one when the last was used or grew old."""
        if self._code is None or self._clock() >= self._expires:
            self._code = secrets.token_urlsafe(16)
            self._expires = self._clock() + self.ttl
            self.serial += 1
        return self._code

    def redeem(self, given: object) -> bool:
        """True once for the valid code; after that the code is gone."""
        if not isinstance(given, str) or self._code is None or self._clock() >= self._expires:
            return False
        if not hmac.compare_digest(self._code.encode(), given.encode()):
            return False
        self._code = None
        return True


def remove_legacy_key(data_dir: Path) -> bool:
    """Deletes the shared key of the first prototype; phones pair anew with the QR code."""
    path = data_dir / LEGACY_KEY_FILE
    if not path.is_file():
        return False
    with contextlib.suppress(OSError):
        path.unlink()
    return True
