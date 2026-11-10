"""Tray icon on Windows: the only visible part of the program besides the browser."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable

from game_remote.config import system_language

log = logging.getLogger(__name__)

TEXTS = {
    "en": {"open": "Open Game Remote", "quit": "Quit"},
    "ru": {"open": "Открыть Game Remote", "quit": "Выход"},
}


def tray_texts() -> dict[str, str]:
    return TEXTS[system_language()]


def make_icon_image(size: int = 64):
    """A rounded square with a 2x2 grid of buttons, drawn at run time (no image file)."""
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=size // 5, fill=(29, 33, 43, 255))
    pad, gap = size // 6, size // 12
    cell = (size - 2 * pad - gap) // 2
    colors = ((76, 125, 240), (62, 207, 122), (226, 179, 64), (196, 79, 106))
    for index, color in enumerate(colors):
        x = pad + (index % 2) * (cell + gap)
        y = pad + (index // 2) * (cell + gap)
        draw.rounded_rectangle((x, y, x + cell, y + cell), radius=cell // 4, fill=(*color, 255))
    return image


def create_tray(on_open: Callable[[], None], on_quit: Callable[[], None]):
    """Build the icon. Call ``.run_detached()`` to show it and ``.stop()`` to remove it."""
    import pystray

    texts = tray_texts()

    def quit_clicked(icon, _item) -> None:
        on_quit()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(texts["open"], lambda _icon, _item: on_open(), default=True),
        pystray.MenuItem(texts["quit"], quit_clicked),
    )
    return pystray.Icon("GameRemote", make_icon_image(), "Game Remote", menu)


def start_tray(on_open: Callable[[], None], on_quit: Callable[[], None]):
    """Show the tray icon if this platform has one. Returns the icon or None."""
    if sys.platform != "win32":
        return None
    try:
        icon = create_tray(on_open, on_quit)
        icon.run_detached()
        return icon
    except Exception:  # the program is still usable from the browser without a tray icon
        log.exception("Could not create the tray icon")
        return None
