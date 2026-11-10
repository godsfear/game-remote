from game_remote.access import key_matches, load_or_create_key
from game_remote.netinfo import is_local_client, lan_addresses, local_name


def test_key_is_created_once_and_kept(tmp_path):
    key = load_or_create_key(tmp_path)
    assert len(key) >= 20
    assert load_or_create_key(tmp_path) == key


def test_a_damaged_key_file_is_replaced(tmp_path):
    (tmp_path / "access.key").write_text("short\n", encoding="ascii")
    key = load_or_create_key(tmp_path)
    assert len(key) >= 20


def test_key_matches_only_the_exact_string():
    assert key_matches("abc", "abc")
    assert not key_matches("abc", "abd")
    assert not key_matches("abc", "")
    assert not key_matches("abc", None)
    assert not key_matches("abc", ["abc"])
    assert not key_matches("abc", "ключ")


def test_only_home_network_addresses_are_local():
    for host in ("127.0.0.1", "192.168.1.20", "10.0.0.5", "172.16.3.4", "::1", "169.254.1.1"):
        assert is_local_client(host), host
    assert is_local_client("::ffff:192.168.1.20")
    assert is_local_client("fe80::1%eth0")
    for host in ("8.8.8.8", "::ffff:8.8.8.8", "2001:4860:4860::8888", "", None, "testclient"):
        assert not is_local_client(host), host


def test_lan_addresses_are_usable():
    for addr in lan_addresses():
        assert not addr.startswith("127.")
    assert local_name() is None or local_name().endswith(".local")
