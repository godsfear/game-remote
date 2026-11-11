"""Facts about windows: which program owns the foreground one, whether it runs
elevated, and which programs have a window open right now.

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


@dataclass(frozen=True)
class OpenWindow:
    exe_name: str
    title: str
    elevated: bool | None


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


def open_windows() -> list[OpenWindow]:
    """Programs with a visible window, one entry per program, for binding a
    panel to a game. Empty off Windows."""
    if sys.platform != "win32":
        return []
    return _open_windows_win32()


def input_blocked_by_elevation(info: ForegroundInfo) -> bool:
    """True when the foreground program is elevated and this app is not."""
    return info.elevated is True and not self_is_elevated()


class _Win32:  # pragma: no cover - Windows only
    """The few Windows calls this module needs, with their argument types set once."""

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        user32 = self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        advapi32 = self.advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        try:
            self.dwmapi = ctypes.WinDLL("dwmapi")
        except OSError:
            self.dwmapi = None

        self.enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
        user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        user32.EnumWindows.argtypes = (self.enum_proc, wintypes.LPARAM)
        user32.IsWindowVisible.argtypes = (wintypes.HWND,)
        user32.GetWindow.argtypes = (wintypes.HWND, wintypes.UINT)
        user32.GetWindow.restype = wintypes.HWND
        user32.GetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int)
        user32.GetWindowLongW.restype = wintypes.LONG
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = (
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        )
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.GetCurrentProcessId.restype = wintypes.DWORD
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

    def title(self, hwnd) -> str:
        length = self.user32.GetWindowTextLengthW(hwnd)
        buf = self.ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value

    def cloaked(self, hwnd) -> bool:
        """True for windows that exist but are not shown, such as suspended Store apps."""
        if self.dwmapi is None:
            return False
        dwmwa_cloaked = 14
        value = self.wintypes.DWORD()
        failed = self.dwmapi.DwmGetWindowAttribute(
            self.wintypes.HWND(hwnd),
            self.wintypes.DWORD(dwmwa_cloaked),
            self.ctypes.byref(value),
            self.wintypes.DWORD(self.ctypes.sizeof(value)),
        )
        return not failed and bool(value.value)

    def pid(self, hwnd) -> int:
        pid = self.wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, self.ctypes.byref(pid))
        return pid.value

    def process_facts(self, pid: int) -> tuple[str | None, bool | None]:
        """Path of the program and whether it runs elevated (None: could not check)."""
        ctypes, wintypes = self.ctypes, self.wintypes
        process_query_limited_information = 0x1000
        token_query = 0x0008
        token_elevation = 20

        exe_path: str | None = None
        elevated: bool | None = None
        process = self.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not process:
            return None, None
        try:
            size = wintypes.DWORD(1024)
            path_buf = ctypes.create_unicode_buffer(size.value)
            if self.kernel32.QueryFullProcessImageNameW(process, 0, path_buf, ctypes.byref(size)):
                exe_path = path_buf.value

            token = wintypes.HANDLE()
            if self.advapi32.OpenProcessToken(process, token_query, ctypes.byref(token)):
                try:
                    value = wintypes.DWORD()
                    returned = wintypes.DWORD()
                    if self.advapi32.GetTokenInformation(
                        token,
                        token_elevation,
                        ctypes.byref(value),
                        ctypes.sizeof(value),
                        ctypes.byref(returned),
                    ):
                        elevated = bool(value.value)
                finally:
                    self.kernel32.CloseHandle(token)
            elif ctypes.get_last_error() == 5:  # ERROR_ACCESS_DENIED: likely elevated
                elevated = None if self_is_elevated() else True
        finally:
            self.kernel32.CloseHandle(process)
        return exe_path, elevated


_win32: _Win32 | None = None


def _api() -> _Win32:  # pragma: no cover - Windows only
    global _win32
    if _win32 is None:
        _win32 = _Win32()
    return _win32


def _foreground_info_win32() -> ForegroundInfo:  # pragma: no cover - Windows only
    api = _api()
    hwnd = api.user32.GetForegroundWindow()
    if not hwnd:
        return ForegroundInfo(pid=None, exe_path=None, title="", elevated=None)
    pid = api.pid(hwnd)
    exe_path, elevated = api.process_facts(pid) if pid else (None, None)
    return ForegroundInfo(
        pid=pid or None, exe_path=exe_path, title=api.title(hwnd), elevated=elevated
    )


def _open_windows_win32() -> list[OpenWindow]:  # pragma: no cover - Windows only
    api = _api()
    gw_owner = 4
    gwl_exstyle = -20
    ws_ex_toolwindow = 0x00000080
    own_pid = api.kernel32.GetCurrentProcessId()
    handles: list[int] = []

    def visit(hwnd, _lparam) -> bool:
        handles.append(hwnd)
        return True

    api.user32.EnumWindows(api.enum_proc(visit), 0)

    found: dict[str, OpenWindow] = {}
    for hwnd in handles:
        # Top-level application windows only: visible, with a title, not a
        # dialog owned by another window and not a floating tool window.
        if not api.user32.IsWindowVisible(hwnd) or api.user32.GetWindow(hwnd, gw_owner):
            continue
        if api.user32.GetWindowLongW(hwnd, gwl_exstyle) & ws_ex_toolwindow or api.cloaked(hwnd):
            continue
        title = api.title(hwnd).strip()
        pid = api.pid(hwnd)
        if not title or not pid or pid == own_pid:
            continue
        exe_path, elevated = api.process_facts(pid)
        if not exe_path:
            continue
        name = ntpath.basename(exe_path)
        # Windows lists the frontmost window first, so the first title of a program wins.
        found.setdefault(name.lower(), OpenWindow(exe_name=name, title=title, elevated=elevated))
    return sorted(found.values(), key=lambda window: window.exe_name.lower())
