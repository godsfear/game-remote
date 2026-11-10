"""Windows ``SendInput`` backend. Imported only on Windows."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from game_remote.input.backend import InputError, KeyEvent

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    # MOUSEINPUT is the largest member; it must be present so sizeof(INPUT) is right.
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
_user32.SendInput.restype = wintypes.UINT


def _to_input(event: KeyEvent) -> INPUT:
    flags = KEYEVENTF_SCANCODE
    if event.scan.extended:
        flags |= KEYEVENTF_EXTENDEDKEY
    if not event.down:
        flags |= KEYEVENTF_KEYUP
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(wVk=0, wScan=event.scan.code, dwFlags=flags, time=0, dwExtraInfo=0)
    return inp


class SendInputBackend:
    def send(self, events: list[KeyEvent]) -> None:
        if not events:
            return
        array = (INPUT * len(events))(*(_to_input(e) for e in events))
        sent = _user32.SendInput(len(events), array, ctypes.sizeof(INPUT))
        if sent != len(events):
            # Blocked by UIPI or another input lock. Note: UIPI often blocks
            # silently and still returns the full count; see windows.foreground_info.
            raise InputError(
                f"SendInput injected {sent} of {len(events)} events "
                f"(error {ctypes.get_last_error()})"
            )
