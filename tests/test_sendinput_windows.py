import ctypes
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


def test_input_struct_matches_windows_layout():
    from game_remote.input.backend import KeyEvent
    from game_remote.input.keys import scan_code
    from game_remote.input.sendinput import INPUT, KEYEVENTF_SCANCODE, _to_input

    assert ctypes.sizeof(INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
    inp = _to_input(KeyEvent("ArrowUp", scan_code("ArrowUp"), down=False))
    assert inp.ki.wScan == 0x48
    assert inp.ki.dwFlags & KEYEVENTF_SCANCODE
    assert inp.ki.dwFlags & 0x0001  # extended
    assert inp.ki.dwFlags & 0x0002  # key up


def test_foreground_info_does_not_crash():
    from game_remote.input.windows import foreground_info

    info = foreground_info()
    assert isinstance(info.title, str)
