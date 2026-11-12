"""Asks GitHub whether a newer version of the program is out.

This is the one request the program sends outside the home network. It says
nothing about the user or the PC, and the editor has a switch that turns it
off. Nothing is downloaded: the editor shows a link, the user gets the exe.
"""

from __future__ import annotations

import asyncio
import contextlib
import http.client
import json
import logging
import re
import ssl
import threading
import urllib.request
from collections.abc import Callable
from typing import TYPE_CHECKING

import truststore

from game_remote import __version__

if TYPE_CHECKING:
    from game_remote.state import AppState

log = logging.getLogger(__name__)

# The release GitHub marks "Latest". The page of sets never is: see sets.yml.
LATEST_URL = "https://api.github.com/repos/godsfear/game-remote/releases/latest"
# A tag of a release, e.g. "v0.5.0". The answer comes from outside: nothing but
# such a number is taken from it.
TAG = re.compile(r"^v(\d{1,4}(?:\.\d{1,4}){1,3})$")


def latest_version(timeout: float = 5.0) -> str | None:
    """The version of the latest release, e.g. "0.5.0". None when GitHub did
    not say: no network, too many questions, an answer that is not a version."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"GameRemote/{__version__}"}
    try:
        request = urllib.request.Request(LATEST_URL, headers=headers)
        # Windows checks the certificate, and fetches a root it lacks. Python
        # alone knows only the roots that are in the store of the PC already.
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with urllib.request.urlopen(request, timeout=timeout, context=context) as reply:
            tag = json.loads(reply.read(1_000_000))["tag_name"]
    except (OSError, http.client.HTTPException, ValueError, LookupError, TypeError) as error:
        log.info("The latest version is not known: %s", error)
        return None
    match = TAG.match(tag) if isinstance(tag, str) else None
    return match.group(1) if match else None


def newer(latest: str | None, current: str = __version__) -> str | None:
    """``latest`` when it is a later version than ``current``, else None."""

    def numbers(version: str) -> tuple[int, ...]:
        # The numbers a version starts with: "0.5.0rc1" counts as 0.5.0.
        return tuple(int(part) for part in re.match(r"[\d.]*", version)[0].split(".") if part)

    return latest if latest and numbers(latest) > numbers(current) else None


def _in_daemon_thread(function: Callable[[], str | None]) -> asyncio.Future:
    """Runs ``function`` in a thread the program does not wait for when it
    quits. ``asyncio.to_thread`` would keep the process alive until a request
    that hangs runs into its timeout."""
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    def finish(result: str | None, error: Exception | None) -> None:
        if future.done():  # nobody waits any more
            return
        if error is None:
            future.set_result(result)
        else:
            future.set_exception(error)

    def run() -> None:
        try:
            outcome = (function(), None)
        except Exception as error:  # handed to the one who waits
            outcome = (None, error)
        with contextlib.suppress(RuntimeError):  # the loop is closed: the program quits
            loop.call_soon_threadsafe(finish, *outcome)

    threading.Thread(target=run, name="update-check", daemon=True).start()
    return future


async def refresh_update(state: AppState) -> bool:
    """Sets ``state.update``: the newer version the editor tells about, or None.
    With the check turned off nothing is asked. False when GitHub was asked and
    did not answer: the question is worth asking again sooner than in a day."""
    if not state.user.check_updates:
        state.update = None
        return True
    latest = await _in_daemon_thread(state.latest_version)
    # No answer keeps what is known: a day without network does not unsay a
    # version that is out.
    if latest is None:
        return False
    if state.user.check_updates:  # it may have been turned off meanwhile
        log.info("The latest version on GitHub is %s, this one is %s", latest, __version__)
        state.update = newer(latest)
    return True
