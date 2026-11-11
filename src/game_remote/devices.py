"""The phones and tablets that were paired with this PC, kept in SQLite."""

from __future__ import annotations

import secrets
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from game_remote.access import key_hash, new_device_key

MAX_NAME_CHARS = 40
DEFAULT_NAME = "Phone"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id        TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    key_hash  TEXT NOT NULL UNIQUE,
    created   REAL NOT NULL,
    last_seen REAL
);
"""


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    created: float
    last_seen: float | None

    def as_dict(self) -> dict:
        return asdict(self)


def clean_name(value: object) -> str:
    """A device name as it is stored: one line, no control characters, not too long."""
    if not isinstance(value, str):
        return ""
    text = " ".join("".join(ch if ch.isprintable() else " " for ch in value).split())
    return text[:MAX_NAME_CHARS].strip()


class DeviceStore:
    def __init__(self, path: Path | str) -> None:
        # The servers and the tests touch the store from different threads.
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        try:
            with self._db:
                self._db.executescript(_SCHEMA)
        except sqlite3.DatabaseError:
            self._db.close()  # or Windows keeps the broken file locked
            raise

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def _rows(self, sql: str, args: tuple = ()) -> list[Device]:
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
        return [Device(*row) for row in rows]

    def _write(self, sql: str, args: tuple) -> int:
        with self._lock, self._db:
            return self._db.execute(sql, args).rowcount

    def all(self) -> list[Device]:
        return self._rows("SELECT id, name, created, last_seen FROM devices ORDER BY created, id")

    def get(self, device_id: str) -> Device | None:
        found = self._rows(
            "SELECT id, name, created, last_seen FROM devices WHERE id = ?", (device_id,)
        )
        return found[0] if found else None

    def find(self, key: object) -> Device | None:
        """The device that owns this key, or None."""
        if not isinstance(key, str) or not key:
            return None
        found = self._rows(
            "SELECT id, name, created, last_seen FROM devices WHERE key_hash = ?",
            (key_hash(key),),
        )
        return found[0] if found else None

    def add(self, name: object = "") -> tuple[Device, str]:
        """Registers a device. Returns it with its key, which is not stored anywhere."""
        key = new_device_key()
        now = time.time()
        device = Device(
            id=secrets.token_hex(6),
            name=self._free_name(clean_name(name) or DEFAULT_NAME),
            created=now,
            last_seen=now,
        )
        self._write(
            "INSERT INTO devices (id, name, key_hash, created, last_seen) VALUES (?, ?, ?, ?, ?)",
            (device.id, device.name, key_hash(key), device.created, device.last_seen),
        )
        return device, key

    def _free_name(self, name: str) -> str:
        """Two phones of one model get "Pixel 7" and "Pixel 7 (2)"."""
        taken = {device.name for device in self.all()}
        if name not in taken:
            return name
        number = 2
        while f"{name} ({number})" in taken:
            number += 1
        return f"{name} ({number})"

    def rename(self, device_id: str, name: object) -> Device | None:
        cleaned = clean_name(name)
        if not cleaned:
            return None
        self._write("UPDATE devices SET name = ? WHERE id = ?", (cleaned, device_id))
        return self.get(device_id)

    def touch(self, device_id: str) -> None:
        self._write("UPDATE devices SET last_seen = ? WHERE id = ?", (time.time(), device_id))

    def remove(self, device_id: str) -> bool:
        return self._write("DELETE FROM devices WHERE id = ?", (device_id,)) > 0
