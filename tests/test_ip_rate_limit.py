"""Tests for trusted-proxy handling in the IP rate limiter (F-19)."""

from types import SimpleNamespace

from api.middleware import ip_rate_limit
from api.middleware.ip_rate_limit import _get_client_ip


def _request(peer: str | None, xff: str | None):
    headers = {}
    if xff is not None:
        headers["x-forwarded-for"] = xff
    client = SimpleNamespace(host=peer) if peer is not None else None
    return SimpleNamespace(headers=headers, client=client)


def test_xff_honored_from_trusted_proxy():
    # AWS ALB appends the real client IP as the rightmost entry. A client may
    # forge a leftmost value ("1.2.3.4"); the trusted proxy's appended entry
    # (203.0.113.9) is the one we use.
    req = _request(peer="10.0.1.5", xff="1.2.3.4, 203.0.113.9")
    assert _get_client_ip(req) == "203.0.113.9"


def test_xff_single_entry_from_trusted_proxy():
    req = _request(peer="10.0.1.5", xff="203.0.113.9")
    assert _get_client_ip(req) == "203.0.113.9"


def test_xff_ignored_from_untrusted_peer():
    # Direct attacker connecting from a public IP forges XFF -> must be ignored.
    req = _request(peer="198.51.100.7", xff="1.2.3.4")
    assert _get_client_ip(req) == "198.51.100.7"


def test_no_xff_uses_peer():
    req = _request(peer="198.51.100.7", xff=None)
    assert _get_client_ip(req) == "198.51.100.7"


def test_missing_client_is_unknown():
    req = _request(peer=None, xff="1.2.3.4")
    assert _get_client_ip(req) == "unknown"


def test_trusted_cidrs_default_to_private_ranges():
    assert ip_rate_limit._is_trusted_proxy("10.0.0.1")
    assert ip_rate_limit._is_trusted_proxy("172.16.5.5")
    assert ip_rate_limit._is_trusted_proxy("192.168.1.1")
    assert ip_rate_limit._is_trusted_proxy("127.0.0.1")
    assert not ip_rate_limit._is_trusted_proxy("8.8.8.8")
    assert not ip_rate_limit._is_trusted_proxy("not-an-ip")
