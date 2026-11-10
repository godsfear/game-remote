"""Keyboard keys and combos.

Keys are identified by the browser's ``KeyboardEvent.code`` values (``KeyM``,
``ControlLeft``, ``ArrowUp``...). ``code`` names a physical key, so a combo
recorded with a Russian layout is the same as one recorded with an English
layout. Each code maps to a set-1 scan code, which is what games that read
DirectInput or Raw Input actually see.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScanCode:
    code: int
    extended: bool = False


_BASIC: dict[str, int] = {
    "Escape": 0x01,
    "Digit1": 0x02,
    "Digit2": 0x03,
    "Digit3": 0x04,
    "Digit4": 0x05,
    "Digit5": 0x06,
    "Digit6": 0x07,
    "Digit7": 0x08,
    "Digit8": 0x09,
    "Digit9": 0x0A,
    "Digit0": 0x0B,
    "Minus": 0x0C,
    "Equal": 0x0D,
    "Backspace": 0x0E,
    "Tab": 0x0F,
    "KeyQ": 0x10,
    "KeyW": 0x11,
    "KeyE": 0x12,
    "KeyR": 0x13,
    "KeyT": 0x14,
    "KeyY": 0x15,
    "KeyU": 0x16,
    "KeyI": 0x17,
    "KeyO": 0x18,
    "KeyP": 0x19,
    "BracketLeft": 0x1A,
    "BracketRight": 0x1B,
    "Enter": 0x1C,
    "ControlLeft": 0x1D,
    "KeyA": 0x1E,
    "KeyS": 0x1F,
    "KeyD": 0x20,
    "KeyF": 0x21,
    "KeyG": 0x22,
    "KeyH": 0x23,
    "KeyJ": 0x24,
    "KeyK": 0x25,
    "KeyL": 0x26,
    "Semicolon": 0x27,
    "Quote": 0x28,
    "Backquote": 0x29,
    "ShiftLeft": 0x2A,
    "Backslash": 0x2B,
    "KeyZ": 0x2C,
    "KeyX": 0x2D,
    "KeyC": 0x2E,
    "KeyV": 0x2F,
    "KeyB": 0x30,
    "KeyN": 0x31,
    "KeyM": 0x32,
    "Comma": 0x33,
    "Period": 0x34,
    "Slash": 0x35,
    "ShiftRight": 0x36,
    "NumpadMultiply": 0x37,
    "AltLeft": 0x38,
    "Space": 0x39,
    "CapsLock": 0x3A,
    "F1": 0x3B,
    "F2": 0x3C,
    "F3": 0x3D,
    "F4": 0x3E,
    "F5": 0x3F,
    "F6": 0x40,
    "F7": 0x41,
    "F8": 0x42,
    "F9": 0x43,
    "F10": 0x44,
    "NumLock": 0x45,
    "ScrollLock": 0x46,
    "Numpad7": 0x47,
    "Numpad8": 0x48,
    "Numpad9": 0x49,
    "NumpadSubtract": 0x4A,
    "Numpad4": 0x4B,
    "Numpad5": 0x4C,
    "Numpad6": 0x4D,
    "NumpadAdd": 0x4E,
    "Numpad1": 0x4F,
    "Numpad2": 0x50,
    "Numpad3": 0x51,
    "Numpad0": 0x52,
    "NumpadDecimal": 0x53,
    "IntlBackslash": 0x56,
    "F11": 0x57,
    "F12": 0x58,
    "F13": 0x64,
    "F14": 0x65,
    "F15": 0x66,
    "F16": 0x67,
    "F17": 0x68,
    "F18": 0x69,
    "F19": 0x6A,
    "F20": 0x6B,
    "F21": 0x6C,
    "F22": 0x6D,
    "F23": 0x6E,
    "F24": 0x76,
}

# Keys sent with the E0 prefix (KEYEVENTF_EXTENDEDKEY on Windows).
_EXTENDED: dict[str, int] = {
    "NumpadEnter": 0x1C,
    "ControlRight": 0x1D,
    "NumpadDivide": 0x35,
    "AltRight": 0x38,
    "Home": 0x47,
    "ArrowUp": 0x48,
    "PageUp": 0x49,
    "ArrowLeft": 0x4B,
    "ArrowRight": 0x4D,
    "End": 0x4F,
    "ArrowDown": 0x50,
    "PageDown": 0x51,
    "Insert": 0x52,
    "Delete": 0x53,
    "MetaLeft": 0x5B,
    "MetaRight": 0x5C,
    "ContextMenu": 0x5D,
}

SCAN_CODES: dict[str, ScanCode] = {
    **{name: ScanCode(code) for name, code in _BASIC.items()},
    **{name: ScanCode(code, extended=True) for name, code in _EXTENDED.items()},
}

MODIFIERS: tuple[str, ...] = (
    "ControlLeft",
    "ControlRight",
    "ShiftLeft",
    "ShiftRight",
    "AltLeft",
    "AltRight",
    "MetaLeft",
    "MetaRight",
)

_MODIFIER_LABELS = {
    "ControlLeft": "Ctrl",
    "ControlRight": "Right Ctrl",
    "ShiftLeft": "Shift",
    "ShiftRight": "Right Shift",
    "AltLeft": "Alt",
    "AltRight": "Right Alt",
    "MetaLeft": "Win",
    "MetaRight": "Right Win",
}


class UnknownKeyError(ValueError):
    pass


def scan_code(key: str) -> ScanCode:
    try:
        return SCAN_CODES[key]
    except KeyError:
        raise UnknownKeyError(f"Unknown key code: {key!r}") from None


def is_modifier(key: str) -> bool:
    return key in MODIFIERS


def key_label(key: str) -> str:
    """Short layout-independent label, e.g. ``KeyM`` -> ``M``."""
    if key in _MODIFIER_LABELS:
        return _MODIFIER_LABELS[key]
    for prefix in ("Key", "Digit"):
        if key.startswith(prefix) and len(key) == len(prefix) + 1:
            return key[len(prefix) :]
    if key.startswith("Arrow"):
        return key[len("Arrow") :]
    return key


@dataclass(frozen=True)
class Combo:
    """One keyboard shortcut: modifiers first, then the main keys, in press order."""

    keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.keys:
            raise ValueError("A combo needs at least one key")
        if len(set(self.keys)) != len(self.keys):
            raise ValueError("A combo cannot repeat a key")
        for key in self.keys:
            scan_code(key)
        # Normalise order: modifiers (in MODIFIERS order) before other keys.
        mods = tuple(k for k in MODIFIERS if k in self.keys)
        rest = tuple(k for k in self.keys if not is_modifier(k))
        object.__setattr__(self, "keys", mods + rest)

    @classmethod
    def parse(cls, text: str) -> Combo:
        """Parse ``"ControlLeft+KeyR"`` (the stored form)."""
        parts = [p.strip() for p in text.split("+") if p.strip()]
        return cls(tuple(parts))

    def serialize(self) -> str:
        return "+".join(self.keys)

    def label(self) -> str:
        return "+".join(key_label(k) for k in self.keys)

    def __str__(self) -> str:
        return self.label()
