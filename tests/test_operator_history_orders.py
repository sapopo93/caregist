"""Operator History paid path: flags, price, wording, rendering and webhook wiring.

No database and no Stripe. The paid flow itself runs against a real Postgres in
``tests/integration/test_operator_history_orders_pg.py``.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from pypdf import PdfReader

from api.config import Settings
from api.main import app
from api.middleware import ip_rate_limit
from api.middleware.auth import validate_billing_identity
from api.routers import billing
from api.routers import operator_history_orders as router_module
from api.services import operator_history as oh
from api.services import operator_history_orders as service
from api.services import operator_history_render as render
from tests.operator_history_orders_support import PRICE_ID, StripeStub, sample_record
from tests.test_operator_history import BANNED

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = "/api/v1/billing/operator-history-checkout"
BODY = {
    "provider_id": "1-1000001", "email": "buyer@example.com", "terms_version": "b2b-1",
    "business_use_confirmed": True,
}


@pytest.fixture(autouse=True)
def _isolation(monkeypatch):
    ip_rate_limit._ip_requests.clear()
    stub = StripeStub().install(monkeypatch)
    app.dependency_overrides[ip_rate_limit.check_ip_rate_limit] = lambda: None
    yield stub
    app.dependency_overrides.pop(ip_rate_limit.check_ip_rate_limit, None)
    app.dependency_overrides.pop(validate_billing_identity, None)


def _settings(monkeypatch, **values):
    for name, value in {
        "operator_history_enabled": True, "operator_history_checkout_enabled": True,
        "billing_checkout_enabled": True, "stripe_secret_key": "sk_test_x",
        "stripe_price_operator_history": PRICE_ID, "b2b_terms_version": "b2b-1", "b2b_terms_sha256": "a" * 64,
        **values,
    }.items():
        monkeypatch.setattr(router_module.settings, name, value)


def _no_database(monkeypatch):
    monkeypatch.setattr(
        router_module, "get_connection", MagicMock(side_effect=AssertionError("the database must not be touched"))
    )


async def _request(method: str, path: str, **kwargs):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.request(method, path, **kwargs)


# --- settings and the price --------------------------------------------------


def test_both_flags_default_off_and_the_price_has_one_definition():
    cfg = Settings(database_url="postgresql://localhost/x", api_master_key="m", support_internal_token="s")
    assert cfg.operator_history_enabled is False
    assert cfg.operator_history_checkout_enabled is False
    assert cfg.stripe_price_operator_history == ""
    assert service.OPERATOR_HISTORY_PRICE_PENCE == 9500 and service.OPERATOR_HISTORY_CURRENCY == "gbp"
    # No other module under api/ defines or repeats the Operator History price.
    offenders = [
        str(path.relative_to(REPO_ROOT)) for path in (REPO_ROOT / "api").rglob("*.py")
        if path.name != "operator_history_orders.py"
        and re.search(r"\b9500\b", path.read_text(encoding="utf-8"))
        and "operator_history" in path.read_text(encoding="utf-8").lower()
    ]
    assert offenders == []


def test_the_request_model_has_no_price_field_and_refuses_extras():
    fields = set(router_module.OperatorHistoryCheckoutRequest.model_fields)
    assert fields == {"provider_id", "email", "terms_version", "business_use_confirmed"}
    with pytest.raises(ValidationError):
        router_module.OperatorHistoryCheckoutRequest(**BODY, price_pence=1)


# --- the flag gates ---------------------------------------------------------


@pytest.mark.parametrize("method, path", [
    ("POST", CHECKOUT),
    ("GET", "/api/v1/operator-history/orders/00000000-0000-4000-8000-000000000000"),
    ("GET", "/api/v1/operator-history/orders/00000000-0000-4000-8000-000000000000/download?format=csv"),
])
async def test_flag_off_is_the_same_404_as_an_unknown_route_even_unauthenticated(monkeypatch, _isolation, method, path):
    _settings(monkeypatch, operator_history_enabled=False)
    _no_database(monkeypatch)
    response = await _request(method, path, json=BODY if method == "POST" else None)
    unknown = await _request("GET", "/api/v1/operator-history/no-such-route")
    assert response.status_code == 404
    assert (response.status_code, response.json()) == (unknown.status_code, unknown.json())
    assert _isolation.calls == []


@pytest.mark.parametrize("closed", [
    {"operator_history_checkout_enabled": False},
    {"billing_checkout_enabled": False},
    {"stripe_price_operator_history": ""},
    {"stripe_secret_key": ""},
])
async def test_checkout_is_a_plain_503_unless_every_switch_and_the_price_are_set(monkeypatch, _isolation, closed):
    _settings(monkeypatch, **closed)
    _no_database(monkeypatch)
    app.dependency_overrides[validate_billing_identity] = lambda: {
        "user_id": 1, "auth_method": "session", "is_verified": True, "email": "buyer@example.com",
    }
    response = await _request("POST", CHECKOUT, json=BODY)
    assert response.status_code == 503
    assert isinstance(response.json()["detail"], str)
    assert _isolation.calls == []


async def test_checkout_needs_the_approved_b2b_terms_and_a_confirmed_business_use(monkeypatch, _isolation):
    _settings(monkeypatch)
    _no_database(monkeypatch)
    app.dependency_overrides[validate_billing_identity] = lambda: {
        "user_id": 1, "auth_method": "session", "is_verified": True, "email": "buyer@example.com",
    }
    wrong_version = await _request("POST", CHECKOUT, json={**BODY, "terms_version": "b2b-old"})
    unconfirmed = await _request("POST", CHECKOUT, json={**BODY, "business_use_confirmed": False})
    _settings(monkeypatch, b2b_terms_version="", b2b_terms_sha256="")
    unapproved = await _request("POST", CHECKOUT, json=BODY)
    assert (wrong_version.status_code, unconfirmed.status_code, unapproved.status_code) == (409, 422, 503)
    assert _isolation.calls == []


async def test_an_api_key_cannot_start_a_purchase_only_a_browser_session(monkeypatch, _isolation):
    _settings(monkeypatch)
    _no_database(monkeypatch)
    app.dependency_overrides[validate_billing_identity] = lambda: {
        "user_id": 1, "auth_method": "api_key", "is_verified": True, "email": "buyer@example.com",
    }
    response = await _request("POST", CHECKOUT, json=BODY)
    assert response.status_code == 403
    assert _isolation.calls == []


# --- the readiness gate ---------------------------------------------------


async def test_readiness_gap_reports_each_closed_check_without_touching_the_edition_when_health_fails():
    conn = MagicMock()
    conn.fetchrow = AsyncMock(side_effect=AssertionError("edition not read"))

    def health(**parts):
        async def run(_conn):
            return {"readiness_ok": True, "source_fresh": True, "units": {"countsReconciled": True}, **parts}
        return run

    assert "readiness" in await service.readiness_gap(conn, health(readiness_ok=False))
    assert "not fresh" in await service.readiness_gap(conn, health(source_fresh=False))
    assert "reconciled" in await service.readiness_gap(conn, health(units={"countsReconciled": False}))


# --- pinning ---------------------------------------------------------------


def test_pin_takes_the_edition_ids_and_hashes_and_never_puts_an_id_in_the_record():
    record = sample_record()
    held = (
        oh.HeldName("Alpha Homes Ltd", date(2026, 6, 1), date(2026, 5, 31), "3" * 64, "4" * 64, edition_id=7),
        oh.HeldName("Alpha Care Ltd", date(2026, 9, 1), date(2026, 8, 31), "1" * 64, "2" * 64, edition_id=9),
        oh.HeldName("Alpha Care Ltd", date(2026, 9, 1), date(2026, 8, 31), "1" * 64, "2" * 64, edition_id=9),
    )
    operator = oh.ResolvedOperator("1-1000001", "Alpha Care Ltd", held, 2)
    pin = service.pin_record(operator, record)
    assert (pin.edition_id, pin.edition_ids) == (9, (7, 9))
    assert (pin.providers_sha256, pin.locations_sha256) == ("1" * 64, "2" * 64)
    assert pin.content_sha256 == record["content_sha256"] and pin.price_pence == 9500
    assert "edition_id" not in str(record)

    unpinned = oh.ResolvedOperator("1-1000001", "Alpha Care Ltd", (oh.HeldName("A", date(2026, 6, 1), date(2026, 6, 1), "1" * 64, "2" * 64),), 1)
    with pytest.raises(service.OperatorHistoryOrderError):
        service.pin_record(unpinned, record)


# --- the deliverables ------------------------------------------------------


def test_deliverables_are_deterministic_and_carry_the_required_fields():
    record = sample_record()
    built = date(2026, 11, 20)
    csv_a, csv_b = render.render_csv(record, built_on=built), render.render_csv(record, built_on=built)
    pdf_a, pdf_b = render.render_pdf(record, built_on=built), render.render_pdf(record, built_on=built)
    assert csv_a == csv_b and pdf_a == pdf_b
    assert render.render_csv(record, built_on=date(2026, 11, 21)) != csv_a

    rows = list(csv.DictReader(io.StringIO(csv_a.decode("utf-8"))))
    assert tuple(rows[0]) == render.CSV_COLUMNS
    for column, expected in {
        "report": "Operator History", "cqc_provider_id": "1-1000001", "legal_name_as_held": "Alpha Care Ltd",
        "edition_retrieved_on": "2026-09-01", "edition_providers_sha256": "1" * 64,
        "edition_locations_sha256": "2" * 64, "content_sha256": record["content_sha256"],
        "record_built_on": "2026-11-20",
    }.items():
        assert {row[column] for row in rows} == {expected}, column
    kinds = [row["row_type"] for row in rows]
    assert kinds[: len(record["limits"])] == ["limit"] * len(record["limits"])  # the limits come first
    assert [row["text"] for row in rows[: len(record["limits"])]] == record["limits"]
    assert kinds.count("location") == 2 and kinds.count("event") == 4 and kinds.count("earlier_name") == 1
    # The sentinel value is quoted as held and is not offered as a rating event.
    other = [row for row in rows if row["row_type"] == "rating_record"]
    assert len(other) == 1 and other[0]["rating"] == "Not Yet Inspected"
    assert "not a published overall rating" in other[0]["text"]
    assert all(row["source_label"] for row in rows if row["row_type"] in {"location", "event", "rating_record"})

    reader = PdfReader(io.BytesIO(pdf_a))
    text = "\n".join(page.extract_text() for page in reader.pages)
    flat = text.replace("\n", " ")
    assert "Operator History" in text and "1-1000001" in text and "Alpha Care Ltd" in text
    assert record["content_sha256"] in text.replace("\n", "")
    assert "1" * 64 in text.replace("\n", "") and "1 September 2026" in flat
    for limit in record["limits"]:
        assert limit[:50] in flat
    assert "fixed at that point" in flat and "Alpha Homes Ltd" in flat
    assert reader.pages and len(reader.pages) >= 1


def test_a_spreadsheet_will_not_read_a_provider_supplied_name_as_a_formula():
    rows = list(csv.DictReader(io.StringIO(render.render_csv(sample_record(), built_on=date(2026, 11, 20)).decode())))
    names = [row["location_name"] for row in rows if row["row_type"] == "location"]
    assert names[0].startswith("'=HYPERLINK") and names[1] == "Alpha Court"
    assert all(not value.startswith(("=", "+", "-", "@")) for row in rows for value in row.values())


def test_filenames_are_stable_and_carry_the_provider_id_and_build_date():
    assert render.deliverable_filename("1-1000001", date(2026, 11, 20), "csv") == "caregist-operator-history-1-1000001-2026-11-20.csv"
    assert render.deliverable_filename("1-1000001", date(2026, 11, 20), "pdf").endswith("2026-11-20.pdf")
    with pytest.raises(ValueError):
        render.deliverable_filename("1-1000001", date(2026, 11, 20), "zip")


def test_an_empty_record_still_renders_both_files():
    record = sample_record(events=[], locations=[])
    record["content_sha256"] = oh.content_sha256(record)
    assert render.render_csv(record, built_on=date(2026, 11, 20))
    assert PdfReader(io.BytesIO(render.render_pdf(record, built_on=date(2026, 11, 20)))).pages


# --- wording ---------------------------------------------------------------


def _new_customer_text() -> list[str]:
    return [
        render.PINNED_NOTICE, render.HASH_NOTICE, render.SOURCE_NOTICE, render.EARLIER_NAME_TEXT,
        render.LOCATION_TEXT, render.LOCATION_SERVICES_TEXT, render.RECORD_NOT_A_RATING_TEXT,
        render.RECORD_NO_DATE_TEXT, *(message for _status, message in router_module._NOT_DOWNLOADABLE.values()),
    ]


@pytest.mark.parametrize("text", _new_customer_text())
def test_new_customer_text_has_no_completeness_score_or_risk_wording(text):
    lowered = text.lower()
    assert [phrase for phrase in BANNED if phrase in lowered] == []


def test_the_rendered_files_hold_no_banned_wording_beyond_what_cqc_and_the_record_quote():
    record = sample_record()
    csv_text = render.render_csv(record, built_on=date(2026, 11, 20)).decode()
    own_text = " ".join(row["text"] for row in csv.DictReader(io.StringIO(csv_text)) if row["row_type"] != "rating_record")
    assert [phrase for phrase in BANNED if phrase in own_text.lower()] == []


def test_the_new_modules_pass_the_evidence_language_guard():
    from tools.evidence_language_guard import scan_text

    for name in ("api/services/operator_history_orders.py", "api/services/operator_history_render.py",
                 "api/routers/operator_history_orders.py", "tools/retry_operator_history_delivery.py"):
        assert scan_text(name, (REPO_ROOT / name).read_text(encoding="utf-8")) == []


# --- webhook wiring ----------------------------------------------------------


async def test_the_webhook_hands_only_operator_history_sessions_to_the_new_handler():
    conn = MagicMock()
    with patch.object(billing.operator_history_orders, "handle_checkout_completed", AsyncMock()) as handler:
        await billing._handle_checkout_completed(conn, {"id": "cs_1", "metadata": {"type": "operator_history"}})
    handler.assert_awaited_once()
    with patch.object(billing.operator_history_orders, "handle_checkout_completed", AsyncMock()) as handler, \
            patch.object(billing, "_record_manual_payment_link_sale", AsyncMock()):
        await billing._handle_checkout_completed(conn, {"id": "cs_2", "metadata": {}, "payment_link": "plink_1"})
    handler.assert_not_awaited()


async def test_a_full_refund_marks_the_operator_history_order_and_a_partial_one_does_not():
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    charge = {"object": "charge", "id": "ch_1", "amount": 9500, "payment_intent": "pi_1"}
    with patch.object(billing.operator_history_orders, "mark_refunded", AsyncMock()) as mark, \
            patch.object(billing, "write_audit_log", AsyncMock()):
        await billing._handle_refund(conn, {**charge, "amount_refunded": 9500, "refunded": True})
        mark.assert_awaited_once_with(conn, "pi_1")
        mark.reset_mock()
        await billing._handle_refund(conn, {**charge, "amount_refunded": 4000, "refunded": False})
        mark.assert_not_awaited()


def test_the_shared_webhook_records_a_delivery_failure_after_rollback():
    source = (REPO_ROOT / "api" / "routers" / "billing.py").read_text(encoding="utf-8")
    assert "operator_history_orders.DeliveryError" in source
    error = service.DeliveryError("order-1", "boom", {"payment_intent": "pi_1"})
    assert isinstance(error, RuntimeError) and hasattr(error, "record_failure")
