from game_remote.access import PairingCodes, key_hash, new_device_key, remove_legacy_key


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_code_works_once():
    codes = PairingCodes()
    code = codes.current()
    assert len(code) >= 20
    assert codes.current() == code  # asking again does not change it
    assert codes.redeem(code)
    assert not codes.redeem(code)
    assert codes.current() != code
    assert codes.serial == 2


def test_wrong_codes_are_refused_and_do_not_spend_the_code():
    codes = PairingCodes()
    assert not codes.redeem("anything")  # nothing was issued yet
    code = codes.current()
    for wrong in ("", code[:-1], code + "x", None, 5, [code], "код"):
        assert not codes.redeem(wrong)
    assert codes.redeem(code)


def test_code_grows_old():
    clock = Clock()
    codes = PairingCodes(ttl=600, clock=clock)
    code = codes.current()
    clock.now += 599
    assert codes.current() == code
    clock.now += 2
    assert not codes.redeem(code)
    fresh = codes.current()
    assert fresh != code
    assert codes.redeem(fresh)


def test_device_keys_are_long_and_stored_as_hashes():
    first, second = new_device_key(), new_device_key()
    assert first != second and len(first) >= 40
    assert key_hash(first) != key_hash(second)
    assert first not in key_hash(first)


def test_shared_key_of_the_first_prototype_is_removed(tmp_path):
    assert not remove_legacy_key(tmp_path)
    (tmp_path / "access.key").write_text("old-secret\n", encoding="ascii")
    assert remove_legacy_key(tmp_path)
    assert not (tmp_path / "access.key").exists()
