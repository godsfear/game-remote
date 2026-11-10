import asyncio

from game_remote.input import Combo, InputController, RecordingBackend

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
