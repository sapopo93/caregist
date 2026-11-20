"""Operator History: pure logic, wording guards and the flag gate (no database)."""

from __future__ import annotations

import itertools
import re
from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.config import Settings
from api.main import app
from api.middleware import ip_rate_limit
from api.services import operator_history as oh

# Words and phrases the customer-facing text must never contain: a claim of
# completeness, or any scoring, ranking, prediction or risk language.
BANNED = (
    "every location", "complete", "all history", "entire", "full history", "exhaustive",
    "risk", "score", "predict", "likely", "probab", "rank", "best", "worst", "safe",
    "concern", "warning", "red flag",
)


def _all_customer_text() -> list[str]:
    texts = [
        oh.LIMIT_CLOSURE, oh.LIMIT_STATUS_START, oh.LIMIT_STATUS_START_NONE, oh.LIMIT_RATING,
        oh.LIMIT_RATING_NONE, oh.LIMIT_NAMES, oh.LIMIT_LOCATIONS, oh.LIMIT_CUTOFF, oh.LIMIT_CUTOFF_NONE,
        *oh.EVENT_TEXT.values(), *oh.STATUS_LABELS.values(), *oh.REFUSAL_MESSAGES.values(),
    ]
    return texts


@pytest.mark.parametrize("text", _all_customer_text())
def test_customer_text_has_no_completeness_score_or_risk_wording(text):
    lowered = text.lower()
    assert [phrase for phrase in BANNED if phrase in lowered] == []


def test_every_limit_combination_is_built_only_from_fixed_templates():
    day = date(2026, 3, 31)
    templates = [
        oh.LIMIT_CLOSURE, oh.LIMIT_STATUS_START, oh.LIMIT_STATUS_START_NONE, oh.LIMIT_RATING,
        oh.LIMIT_RATING_NONE, oh.LIMIT_NAMES, oh.LIMIT_LOCATIONS, oh.LIMIT_CUTOFF, oh.LIMIT_CUTOFF_NONE,
    ]
    patterns = [re.compile("^" + re.escape(t).replace(r"\{date\}", r"\d{1,2} [A-Z][a-z]+ \d{4}") + "$") for t in templates]
    for rating, edition, status, cutoff in itertools.product([day, None], repeat=4):
        limits = oh.build_limits(
            first_rating_recorded_on=rating, earliest_edition_on=edition,
            first_status_observed_on=status, history_cutoff=cutoff,
        )
        assert limits[0] == oh.LIMIT_CLOSURE
        assert oh.LIMIT_LOCATIONS in limits
        for line in limits:
            assert any(p.match(line) for p in patterns), line
            assert not [b for b in BANNED if b in line.lower()]


def test_limits_carry_the_dates_computed_from_the_data():
    limits = oh.build_limits(
        first_rating_recorded_on=date(2026, 3, 31), earliest_edition_on=date(2026, 9, 1),
        first_status_observed_on=date(2026, 8, 10), history_cutoff=date(2026, 11, 19),
    )
    joined = " ".join(limits)
    assert "from 31 March 2026" in joined
    assert "before 1 September 2026" in joined
    assert "on 10 August 2026" in joined
    assert "up to 19 November 2026" in joined
    assert "not CQC's deregistration date" in joined


def test_closure_wording_never_claims_a_deregistration_date():
    for kind in ("closure_observed", "reinstatement_observed"):
        assert "observed" in oh.EVENT_TEXT[kind]
    assert "not CQC's deregistration date" in oh.EVENT_TEXT["closure_observed"]


def test_refusal_codes_are_stable_and_each_has_message_and_status():
    assert set(oh.REFUSAL_MESSAGES) == {
        "not_found", "ambiguous", "identity_disputed", "no_legal_name_held", "not_enough_history", "invalid_input",
    }
    assert (oh.NOT_FOUND, oh.AMBIGUOUS, oh.IDENTITY_DISPUTED, oh.NO_LEGAL_NAME_HELD, oh.NOT_ENOUGH_HISTORY) == (
        "not_found", "ambiguous", "identity_disputed", "no_legal_name_held", "not_enough_history",
    )
    for code in oh.REFUSAL_MESSAGES:
        refusal = oh.OperatorRefusal(code)
        assert refusal.http_status in {404, 409, 422}
        assert refusal.as_detail()["code"] == code


def test_ambiguity_detail_exposes_only_id_name_and_count():
    candidates = [{"provider_id": "1-100", "name": "A Ltd", "location_count": 3}]
    detail = oh.OperatorRefusal(oh.AMBIGUOUS, candidates=candidates, total_matches=1).as_detail()
    assert set(detail["candidates"][0]) == {"provider_id", "name", "location_count"}


@pytest.mark.parametrize(
    "provider_id, name",
    [
        (None, None), ("", ""), ("1-1000001", "Alpha Care"), (None, "ab"), (None, "x" * 121),
        ("1-1' OR '1'='1", None), ("1-12", None), ("2-1000001", None), ("1-1000001; DROP TABLE care_providers", None),
        (None, "bad\x00name"),
    ],
)
def test_inputs_must_be_exactly_one_safe_identifier(provider_id, name):
    with pytest.raises(oh.OperatorRefusal) as excinfo:
        oh.normalise_inputs(provider_id, name)
    assert excinfo.value.code == oh.INVALID_INPUT


def test_valid_inputs_are_normalised():
    assert oh.normalise_inputs(" 1-101234567 ", None) == ("1-101234567", None)
    assert oh.normalise_inputs(None, "  Alpha   Care  Ltd ") == (None, "Alpha Care Ltd")
    # Metacharacters are legal text for a name; they are only ever bound parameters.
    assert oh.normalise_inputs(None, "Robert'); DROP TABLE care_providers;--")[1].startswith("Robert')")


def test_like_wildcards_are_escaped_to_literals():
    assert oh.escape_like("100%_a\\b") == "100\\%\\_a\\\\b"


def test_content_hash_is_stable_and_ignores_only_its_own_field():
    record = {"b": 1, "a": [3, 2, {"z": None, "y": "x"}], "content_sha256": "ignored"}
    same_other_order = {"a": [3, 2, {"y": "x", "z": None}], "content_sha256": "different", "b": 1}
    assert oh.content_sha256(record) == oh.content_sha256(same_other_order)
    assert oh.content_sha256(record) != oh.content_sha256({**record, "b": 2})
    assert len(oh.content_sha256(record)) == 64


def test_status_classification_never_guesses():
    assert oh._classify_status("ACTIVE") == "on_active_directory"
    assert oh._classify_status(" inactive ") == "no_longer_on_active_directory"
    assert oh._classify_status(None) == "status_not_held"
    assert oh._classify_status("Registered") == "status_not_held"


def test_service_types_are_split_deduplicated_and_sorted():
    assert oh._split_services("Homecare|Residential||Homecare") == ["Homecare", "Residential"]
    assert oh._split_services(None) == []


# --- the flag gate ----------------------------------------------------------


def test_flag_defaults_off():
    cfg = Settings(database_url="postgresql://localhost/x", api_master_key="m", support_internal_token="s")
    assert cfg.operator_history_enabled is False


@pytest.fixture(autouse=True)
def _fresh_rate_limit():
    ip_rate_limit._public_ip_requests.clear()
    yield
    ip_rate_limit._public_ip_requests.clear()


async def _get(path, *, enabled, factory=None):
    factory = factory or MagicMock(side_effect=AssertionError("the database must not be touched"))
    with patch("api.routers.operator_history.get_connection", factory), \
         patch("api.routers.operator_history.settings.operator_history_enabled", enabled):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
            return await client.get(path)


@pytest.mark.parametrize("path", [
    "/api/v1/operator-history/coverage?provider_id=1-101234567",
    "/api/v1/operator-history/coverage?name=Alpha%20Care",
    "/api/v1/operator-history/coverage",
])
async def test_flag_off_is_the_same_404_as_an_unknown_route_and_reads_nothing(path):
    resp = await _get(path, enabled=False)
    unknown = await _get("/api/v1/operator-history/no-such-route", enabled=False)
    assert resp.status_code == 404
    assert (resp.status_code, resp.json()) == (unknown.status_code, unknown.json())


async def test_flag_on_maps_a_refusal_to_its_status_and_stable_code():
    @asynccontextmanager
    async def factory():
        conn = MagicMock()

        @asynccontextmanager
        async def transaction(**_kw):
            yield

        conn.transaction = transaction
        yield conn

    refusal = oh.OperatorRefusal(oh.AMBIGUOUS, candidates=[{"provider_id": "1-100", "name": "A", "location_count": 1}], total_matches=2)
    with patch("api.routers.operator_history.service.coverage_preview", AsyncMock(side_effect=refusal)):
        resp = await _get("/api/v1/operator-history/coverage?name=Alpha", enabled=True, factory=factory)
    assert resp.status_code == 409
    body = resp.json()["detail"]
    assert body["code"] == "ambiguous"
    assert body["message"] == oh.REFUSAL_MESSAGES["ambiguous"]
    assert body["candidates"] == [{"provider_id": "1-100", "name": "A", "location_count": 1}]


async def test_flag_on_refuses_neither_or_both_inputs_with_422_and_no_query():
    @asynccontextmanager
    async def factory():
        conn = MagicMock()
        conn.fetchval = AsyncMock(side_effect=AssertionError("no query for invalid input"))
        conn.fetch = AsyncMock(side_effect=AssertionError("no query for invalid input"))

        @asynccontextmanager
        async def transaction(**_kw):
            yield

        conn.transaction = transaction
        yield conn

    for path in ("/api/v1/operator-history/coverage",
                 "/api/v1/operator-history/coverage?provider_id=1-101234567&name=Alpha%20Care"):
        resp = await _get(path, enabled=True, factory=factory)
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "invalid_input"
