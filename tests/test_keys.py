import pytest

from game_remote.input.keys import SCAN_CODES, Combo, ScanCode, UnknownKeyError, scan_code


def test_letters_digits_and_function_keys_are_mapped():
    assert scan_code("KeyM") == ScanCode(0x32)
    assert scan_code("KeyR") == ScanCode(0x13)
    assert scan_code("Digit1") == ScanCode(0x02)
    assert scan_code("F12") == ScanCode(0x58)


def test_navigation_keys_are_extended():
    for key in ("ArrowUp", "ArrowDown", "Insert", "Delete", "Home", "End", "ControlRight"):
        assert scan_code(key).extended, key
    assert not scan_code("Numpad8").extended


def test_scan_codes_are_unique_per_extended_flag():
    seen = {}
    for key, sc in SCAN_CODES.items():
        assert sc not in seen, f"{key} and {seen.get(sc)} share {sc}"
        seen[sc] = key


def test_unknown_key_is_rejected():
    with pytest.raises(UnknownKeyError):
        scan_code("KeyЖ")
    with pytest.raises(UnknownKeyError):
        Combo.parse("ControlLeft+Nope")


def test_combo_puts_modifiers_first_and_round_trips():
    combo = Combo(("KeyR", "ControlLeft"))
    assert combo.keys == ("ControlLeft", "KeyR")
    assert Combo.parse(combo.serialize()) == combo
    assert combo.label() == "Ctrl+R"


def test_combo_rejects_empty_and_repeated_keys():
    with pytest.raises(ValueError):
        Combo.parse("")
    with pytest.raises(ValueError):
        Combo(("KeyM", "KeyM"))


def test_labels():
    assert Combo.parse("ShiftLeft+ArrowUp").label() == "Shift+Up"
    assert Combo.parse("Digit5").label() == "5"
