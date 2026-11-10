"""Facts about the foreground window: which program it is and whether it runs elevated.

Windows (UIPI) silently drops input sent from a normal process to an elevated
one, so the app checks this before sending and tells the phone why a press did
nothing. Every function returns None-ish values off Windows.
"""

from __future__ import annotations

import ntpath
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ForegroundInfo:
    pid: int | None
    exe_path: str | None
    title: str
    # True/False when known; None when Windows did not let us check.
    elevated: bool | None

    @property
    def exe_name(self) -> str | None:
        return ntpath.basename(self.exe_path) if self.exe_path else None


def self_is_elevated() -> bool:
    if sys.platform != "win32":
        return False
    import ctypes

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def foreground_info() -> ForegroundInfo:
    if sys.platform != "win32":
        return ForegroundInfo(pid=None, exe_path=None, title="", elevated=None)
    return _foreground_info_win32()


def input_blocked_by_elevation(info: ForegroundInfo) -> bool:
    """True when the foreground program is elevated and this app is not."""
    return info.elevated is True and not self_is_elevated()


def _foreground_info_win32() -> ForegroundInfo:  # pragma: no cover - Windows only
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
    user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    advapi32.OpenProcessToken.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    )
    advapi32.GetTokenInformation.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )

    process_query_limited_information = 0x1000
    token_query = 0x0008
    token_elevation = 20

    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ForegroundInfo(pid=None, exe_path=None, title="", elevated=None)

    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    exe_path: str | None = None
    elevated: bool | None = None
    process = kernel32.OpenProcess(process_query_limited_information, False, pid.value)
    if process:
        try:
            size = wintypes.DWORD(1024)
            path_buf = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(process, 0, path_buf, ctypes.byref(size)):
                exe_path = path_buf.value

            token = wintypes.HANDLE()
            if advapi32.OpenProcessToken(process, token_query, ctypes.byref(token)):
                try:
                    value = wintypes.DWORD()
                    returned = wintypes.DWORD()
                    if advapi32.GetTokenInformation(
                        token,
                        token_elevation,
                        ctypes.byref(value),
                        ctypes.sizeof(value),
                        ctypes.byref(returned),
                    ):
                        elevated = bool(value.value)
                finally:
                    kernel32.CloseHandle(token)
            elif ctypes.get_last_error() == 5:  # ERROR_ACCESS_DENIED: likely elevated
                elevated = None if self_is_elevated() else True
        finally:
            kernel32.CloseHandle(process)

    return ForegroundInfo(pid=pid.value or None, exe_path=exe_path, title=title, elevated=elevated)
