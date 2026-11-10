"""Addresses of this PC on the home network."""

from __future__ import annotations

import ipaddress
import socket


def lan_addresses() -> list[str]:
    """IPv4 addresses a phone could use, the default route's address first."""
    found: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # no packet is sent; this picks the default route
            found.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addr = info[4][0]
            if addr not in found:
                found.append(addr)
    except OSError:
        pass
    return [a for a in found if not a.startswith("127.")]


def local_name() -> str | None:
    """mDNS name of this PC; it stays the same when the router hands out a new IP."""
    host = socket.gethostname().split(".")[0]
    return f"{host}.local" if host else None


def is_local_client(host: str | None) -> bool:
    """True for addresses of a home network (private, link-local or this PC)."""
    if not host:
        return False
    try:
        addr = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_loopback or addr.is_private or addr.is_link_local
