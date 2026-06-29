"""Tests for plan quota enforcement."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import api.middleware.auth as auth
import api.middleware.ip_rate_limit as ip_rate_limit
import api.middleware.rate_limit as rate_limit


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    rate_limit._burst_requests.clear()
    rate_limit._daily_counts.clear()
    rate_limit._rolling_7d_counts.clear()
    rate_limit._monthly_counts.clear()
    yield
    rate_limit._burst_requests.clear()
    rate_limit._daily_counts.clear()
    rate_limit._rolling_7d_counts.clear()
    rate_limit._monthly_counts.clear()


def make_request(*, client_host: str, forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "client": (client_host, 12345),
        }
    )


def test_guest_identifier_ignores_spoofed_forwarded_for_from_untrusted_peer():
    request = make_request(client_host="203.0.113.10", forwarded_for="198.51.100.1")

    assert auth._client_identifier(request) == "203.0.113.10"


def test_trusted_proxy_parser_uses_edge_appended_client_ip():
    request = make_request(
        client_host="127.0.0.1",
        forwarded_for="1.2.3.4, 198.51.100.1",
    )

    assert ip_rate_limit._get_client_ip(request) == "198.51.100.1"
    assert auth._client_identifier(request) == "198.51.100.1"


@pytest.mark.asyncio
async def test_free_plan_allows_two_requests_per_second():
    key = "cg_free_test"
    first = await rate_limit.check_rate_limit(key, "free")
    second = await rate_limit.check_rate_limit(key, "free")

    assert first["burst_remaining"] == 1
    assert second["burst_remaining"] == 0

    with pytest.raises(HTTPException) as exc:
        await rate_limit.check_rate_limit(key, "free")

    assert exc.value.status_code == 429
    assert "2 requests/sec" in exc.value.detail


@pytest.mark.asyncio
async def test_free_plan_blocks_when_rolling_seven_day_cap_is_reached():
    key = "cg_free_weekly"
    today = rate_limit._today()
    rate_limit._rolling_7d_counts[key][today] = 60

    with pytest.raises(HTTPException) as exc:
        await rate_limit.check_rate_limit(key, "free")

    assert exc.value.status_code == 429
    assert "60/7 days" in exc.value.detail


@pytest.mark.asyncio
async def test_redis_quota_check_uses_one_lua_call(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.calls = []

        async def eval(self, script, numkeys, *args):
            self.calls.append((script, numkeys, args))
            return [0, 9, 19, 99]

    fake = FakeRedis()

    async def fake_get_redis():
        return fake

    monkeypatch.setattr(rate_limit, "_get_redis", fake_get_redis)

    remaining = await rate_limit._redis_quota_check(
        "cg_test",
        {"daily": 10, "rolling_7d": 20, "monthly": 100},
    )

    assert remaining == {
        "daily_remaining": 9,
        "rolling_7d_remaining": 19,
        "monthly_remaining": 99,
    }
    assert len(fake.calls) == 1
    assert fake.calls[0][1] == 10


@pytest.mark.asyncio
async def test_redis_quota_check_raises_for_lua_rejection(monkeypatch):
    class FakeRedis:
        async def eval(self, script, numkeys, *args):
            return [-2, 7, 0, 90]

    async def fake_get_redis():
        return FakeRedis()

    monkeypatch.setattr(rate_limit, "_get_redis", fake_get_redis)

    with pytest.raises(HTTPException) as exc:
        await rate_limit._redis_quota_check(
            "cg_test",
            {"daily": 10, "rolling_7d": 20, "monthly": 100},
        )

    assert exc.value.status_code == 429
    assert "7-day limit exceeded" in exc.value.detail
