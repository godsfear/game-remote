import asyncio

import pytest

from game_remote.input import Combo, InputController, InputError, RecordingBackend

CTRL_R = Combo.parse("ControlLeft+KeyR")
SHIFT = Combo.parse("ShiftLeft")
W = Combo.parse("KeyW")


def make():
    backend = RecordingBackend()
    return backend, InputController(backend, tap_ms=1)


def test_tap_presses_modifiers_first_and_releases_them_last():
    backend, ctl = make()
    asyncio.run(ctl.tap(CTRL_R))
    assert backend.trace() == ["+ControlLeft", "+KeyR", "-KeyR", "-ControlLeft"]
    assert ctl.held_keys == set()


def test_tap_uses_scan_codes():
    backend, ctl = make()
    asyncio.run(ctl.tap(Combo.parse("ArrowUp")))
    assert backend.events[0].scan.code == 0x48
    assert backend.events[0].scan.extended


def test_hold_and_unhold():
    backend, ctl = make()
    ctl.hold("phone-1", W)
    assert backend.trace() == ["+KeyW"]
    assert ctl.is_held("phone-1", W)
    assert ctl.unhold("phone-1", W)
    assert backend.trace() == ["+KeyW", "-KeyW"]
    assert not ctl.unhold("phone-1", W)


def test_shared_key_goes_up_only_after_last_holder():
    backend, ctl = make()
    ctl.hold("phone-1", SHIFT)
    ctl.hold("phone-2", SHIFT)
    ctl.unhold("phone-1", SHIFT)
    assert backend.trace() == ["+ShiftLeft"]
    ctl.unhold("phone-2", SHIFT)
    assert backend.trace() == ["+ShiftLeft", "-ShiftLeft"]


def test_tap_while_modifier_is_held_keeps_it_down():
    backend, ctl = make()
    ctl.hold("phone-1", Combo.parse("ControlLeft"))
    asyncio.run(ctl.tap(CTRL_R))
    assert backend.trace() == ["+ControlLeft", "+KeyR", "-KeyR"]
    assert ctl.held_keys == {"ControlLeft"}


def test_release_all_for_one_source_after_disconnect():
    backend, ctl = make()
    ctl.hold("phone-1", W)
    ctl.hold("phone-1", SHIFT)
    ctl.hold("phone-2", Combo.parse("Space"))
    ctl.release_all("phone-1")
    assert ctl.held_keys == {"Space"}
    assert backend.trace()[-2:] == ["-ShiftLeft", "-KeyW"]
    ctl.release_all()
    assert ctl.held_keys == set()


class FlakyBackend(RecordingBackend):
    """Refuses events while ``refuse`` says so, like Windows does when input is blocked."""

    def __init__(self) -> None:
        super().__init__()
        self.refuse = lambda event: False

    def send(self, events):
        if any(self.refuse(event) for event in events):
            raise InputError("blocked")
        super().send(events)


def make_flaky():
    backend = FlakyBackend()
    return backend, InputController(backend, tap_ms=1)


def test_refused_tap_does_not_leave_the_key_counted_as_held():
    backend, ctl = make_flaky()
    backend.refuse = lambda event: event.down
    with pytest.raises(InputError):
        ctl.start_tap(W)
    assert ctl.held_keys == set()
    backend.refuse = lambda event: False
    backend.clear()
    asyncio.run(ctl.tap(W))
    # The next tap must really reach Windows, not be swallowed as "already down".
    assert backend.trace() == ["+KeyW", "-KeyW"]


def test_refused_hold_does_not_leave_the_key_counted_as_held():
    backend, ctl = make_flaky()
    backend.refuse = lambda event: event.down
    with pytest.raises(InputError):
        ctl.hold("phone-1", W)
    assert ctl.held_keys == set()
    assert not ctl.is_held("phone-1", W)
    backend.refuse = lambda event: False
    backend.clear()
    ctl.hold("phone-1", W)
    ctl.unhold("phone-1", W)
    assert backend.trace() == ["+KeyW", "-KeyW"]


def test_refused_press_lets_go_of_keys_windows_may_have_taken():
    backend, ctl = make_flaky()
    backend.refuse = lambda event: event.down
    with pytest.raises(InputError):
        ctl.hold("phone-1", CTRL_R)
    # Windows can take a part of the events before it refuses, so both keys go up.
    assert backend.trace() == ["-KeyR", "-ControlLeft"]


def test_refused_press_does_not_touch_keys_others_hold():
    backend, ctl = make_flaky()
    ctl.hold("phone-1", Combo.parse("ControlLeft"))
    backend.refuse = lambda event: event.down
    with pytest.raises(InputError):
        ctl.start_tap(CTRL_R)
    assert ctl.held_keys == {"ControlLeft"}
    assert backend.trace() == ["+ControlLeft", "-KeyR"]


def test_refused_release_is_remembered_and_retried_by_release_all():
    backend, ctl = make_flaky()
    ctl.hold("phone-1", W)
    backend.refuse = lambda event: not event.down
    with pytest.raises(InputError):
        ctl.unhold("phone-1", W)
    # The key may still be down in Windows, so the program keeps showing it.
    assert ctl.held_keys == {"KeyW"}
    backend.refuse = lambda event: False
    ctl.release_all()
    assert backend.trace() == ["+KeyW", "-KeyW"]
    assert ctl.held_keys == set()


def test_release_all_goes_on_after_one_refusal():
    backend, ctl = make_flaky()
    ctl.hold("phone-1", W)
    ctl.hold("phone-1", SHIFT)
    backend.refuse = lambda event: event.key == "ShiftLeft"
    with pytest.raises(InputError):
        ctl.release_all("phone-1")
    assert backend.trace() == ["+KeyW", "+ShiftLeft", "-KeyW"]
    assert ctl.held_keys == {"ShiftLeft"}
    backend.refuse = lambda event: False
    ctl.release_all()
    assert ctl.held_keys == set()
