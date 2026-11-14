"""Starting the program together with Windows.

At sign-in Windows runs what the values of the user's ``Run`` key say. While
the box in the editor is ticked the program keeps one value there: its own exe
with ``--no-browser``, so that only the icon in the tray appears.

Nothing else remembers the choice: Windows does. The value is there or it is
not, and Windows has a switch of its own for every such program, in the Task
Manager and in its settings. That switch does not take the value away: it
leaves a mark "disabled" in the key ``StartupApproved`` next to it. The box in
the editor shows both: it is ticked while the value is there and not switched
off. Ticking it takes the mark away, or the program would not start for all
the ticks in the editor.
"""

from __future__ import annotations

import contextlib
import logging
import sys

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# Where Windows keeps its own switch of every program of the Run key: binary
# data under the name of the program, the first byte odd when it is switched
# off. A program without a mark there is on.
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
VALUE_NAME = "GameRemote"


class RegistryValue:
    """One text value in the registry of the current user. With ``approved``,
    the key of the switches of Windows, a value that is switched off there
    counts as not being there."""

    def __init__(self, key: str, name: str, approved: str | None = None) -> None:
        self.key = key
        self.name = name
        self.approved = approved

    def _read(self, key_path: str) -> object:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                return winreg.QueryValueEx(key, self.name)[0]
        except FileNotFoundError:  # no such key, or no such value in it
            return None

    def get(self) -> str | None:
        text = self._read(self.key)
        if text is None:
            return None
        mark = self._read(self.approved) if self.approved else None
        if isinstance(mark, bytes) and mark and mark[0] & 1:
            return None  # switched off in Windows
        return str(text)

    def set(self, text: str | None) -> None:
        """Writes the value, or takes it away when ``text`` is None. Either way
        the switch of Windows forgets the program: a value that is written is
        on."""
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.key) as key:
            if text is None:
                with contextlib.suppress(FileNotFoundError):
                    winreg.DeleteValue(key, self.name)
            else:
                winreg.SetValueEx(key, self.name, 0, winreg.REG_SZ, text)
        if self.approved:
            with (
                contextlib.suppress(FileNotFoundError),
                winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, self.approved, 0, winreg.KEY_SET_VALUE
                ) as key,
            ):
                winreg.DeleteValue(key, self.name)


class MemoryValue:
    """Stands for the registry in test mode and in the tests: nothing of the
    PC is touched."""

    def __init__(self, text: str | None = None) -> None:
        self.text = text

    def get(self) -> str | None:
        return self.text

    def set(self, text: str | None) -> None:
        self.text = text


class Autostart:
    def __init__(self, value: RegistryValue | MemoryValue, command: str | None) -> None:
        self.value = value
        # What Windows has to run. None: this program cannot be started so.
        self.command = command
        # The editor asks every second or two: a Windows that does not answer
        # is written into the log once, not every time.
        self._told = False

    @property
    def supported(self) -> bool:
        return self.command is not None

    def enabled(self) -> bool:
        if not self.supported:
            return False
        try:
            return self.value.get() is not None
        except OSError:  # Windows does not let the program look: the box stays empty
            if not self._told:
                self._told = True
                log.exception("Could not read whether the program starts with Windows")
            return False

    def set(self, on: bool) -> None:
        """Raises OSError when Windows does not take the change."""
        if self.supported:
            self.value.set(self.command if on else None)

    def refresh(self) -> None:
        """The exe was moved, or a newer one was downloaded next to it: Windows
        goes on starting the one that runs now."""
        try:
            if self.enabled() and self.value.get() != self.command:
                self.value.set(self.command)
                log.info("Windows now starts this copy of the program: %s", self.command)
        except OSError:
            log.exception("Could not point the start with Windows at this copy")


def own_command() -> str | None:
    """How Windows starts this program: the exe, without the page in the
    browser. None off Windows and for a run from the source, which has no
    single file to start."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return None
    return f'"{sys.executable}" --no-browser'


def windows_autostart() -> Autostart:
    return Autostart(RegistryValue(RUN_KEY, VALUE_NAME, APPROVED_KEY), own_command())
