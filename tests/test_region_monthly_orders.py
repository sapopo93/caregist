"""Region Monthly stage 2: flags, price, wording, rendering, UK month boundaries and webhook wiring.

No database and no Stripe. The paid flow itself runs against a real Postgres in
``tests/integration/test_region_monthly_orders_pg.py``.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, timezone
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
from api.routers import region_monthly_orders as router_module
from api.services import region_monthly as rm
from api.services import region_monthly_orders as service
from api.services import region_monthly_render as render
from api.services.region_monthly import RegionMonthlyError
from tests.region_monthly_orders_support import PRICE_IDS, RegionMonthlyStripeStub, sample_build

REPO_ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
CHECKOUT = "/api/v1/billing/region-monthly-checkout"
ORDER = "/api/v1/region-monthly/orders/00000000-0000-4000-8000-000000000000"
BODY = {
    "region": "London", "kind": "six", "first_month": "2026-05", "email": "buyer@example.com",
    "terms_version": "b2b-1", "business_use_confirmed": True,
}

# Words that customer-facing text must not contain: a claim of completeness, or any
# scoring, ranking, prediction or risk language. The stage 1 limits are checked by their own
# tests (they say "not scores, rankings or predictions" on purpose), so they are left out here.
BANNED = (
    "every", "complete", "all history", "entire", "full history", "exhaustive",
    "risk", "score", "predict", "likely", "probab", "rank", "best", "worst", "safe",
    "concern", "warning", "red flag",
)


@pytest.fixture(autouse=True)
def _isolation(monkeypatch):
    ip_rate_limit._ip_requests.clear()
    stub = RegionMonthlyStripeStub().install(monkeypatch)
    app.dependency_overrides[ip_rate_limit.check_ip_rate_limit] = lambda: None
    yield stub
    app.dependency_overrides.pop(ip_rate_limit.check_ip_rate_limit, None)
    app.dependency_overrides.pop(validate_billing_identity, None)


def _settings(monkeypatch, **values):
    for name, value in {
        "region_monthly_enabled": True, "region_monthly_checkout_enabled": True,
        "billing_checkout_enabled": True, "stripe_secret_key": "sk_test_x",
        "stripe_price_region_monthly_single": PRICE_IDS["single"],
        "stripe_price_region_monthly_six": PRICE_IDS["six"],
        "stripe_price_region_monthly_twelve": PRICE_IDS["twelve"],
        "b2b_terms_version": "b2b-1", "b2b_terms_sha256": "a" * 64,
        **values,
    }.items():
        monkeypatch.setattr(router_module.settings, name, value)


def _no_database(monkeypatch):
    monkeypatch.setattr(
        router_module, "get_connection", MagicMock(side_effect=AssertionError("the database must not be touched"))
    )


def _session_identity(**overrides):
    app.dependency_overrides[validate_billing_identity] = lambda: {
        "user_id": 1, "auth_method": "session", "is_verified": True, "email": "buyer@example.com", **overrides,
    }


async def _request(method: str, path: str, **kwargs):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.request(method, path, **kwargs)


def d(y: int, m: int, day: int = 1) -> date:
    return date(y, m, day)


# --- settings and the price --------------------------------------------------


def test_the_flags_default_off_and_the_prices_have_one_definition():
    cfg = Settings(database_url="postgresql://localhost/x", api_master_key="m", support_internal_token="s")
    assert cfg.region_monthly_enabled is False
    assert cfg.region_monthly_checkout_enabled is False
    assert (cfg.stripe_price_region_monthly_single, cfg.stripe_price_region_monthly_six,
            cfg.stripe_price_region_monthly_twelve) == ("", "", "")
    assert {k: v.price_pence for k, v in rm.PURCHASE_KINDS.items()} == {"single": 4900, "six": 24500, "twelve": 44500}
    # No other module under api/ defines or repeats a Region Monthly price.
    offenders = [
        str(path.relative_to(REPO_ROOT)) for path in (REPO_ROOT / "api").rglob("*.py")
        if path.name != "region_monthly.py"
        and re.search(r"\b(4900|24500|44500)\b", path.read_text(encoding="utf-8"))
        and "region_monthly" in path.read_text(encoding="utf-8").lower()
    ]
    assert offenders == []


def test_the_request_model_has_no_price_field_and_refuses_extras():
    fields = set(router_module.RegionMonthlyCheckoutRequest.model_fields)
    assert fields == {"region", "service", "kind", "first_month", "accept_future_months", "email",
                      "terms_version", "business_use_confirmed"}
    for extra in ({"price_pence": 1}, {"amount": 100}, {"price_id": "price_cheap"}, {"months": ["2026-05"]}):
        with pytest.raises(ValidationError):
            router_module.RegionMonthlyCheckoutRequest(**BODY, **extra)


def test_the_stripe_lookup_keys_follow_the_catalogue_names():
    assert [service.stripe_price_lookup_key(kind) for kind in rm.PURCHASE_KINDS] == [
        "region_monthly_single_gbp_oneoff_v1", "region_monthly_six_gbp_oneoff_v1", "region_monthly_twelve_gbp_oneoff_v1",
    ]


@pytest.mark.parametrize("kind", ["single", "six", "twelve"])
def test_the_stripe_price_is_checked_against_the_central_price(monkeypatch, _isolation, kind):
    _settings(monkeypatch)
    assert service.validate_checkout_price(kind) is None
    for override in ({"unit_amount": rm.PURCHASE_KINDS[kind].price_pence - 100}, {"currency": "usd"},
                     {"type": "recurring"}, {"recurring": {"interval": "month"}}, {"active": False},
                     {"lookup_key": "other"}, {"lookup_key": f"region_monthly_{kind}_gbp_oneoff_v2"},
                     {"product": {"active": False}}, {"livemode": True}, {"id": "price_other"}):
        _isolation.set_price(kind, **override)
        assert service.validate_checkout_price(kind), override
    _isolation.set_price(kind)
    assert service.validate_checkout_price(kind) is None


def test_an_unknown_kind_has_no_price_and_no_stripe_price():
    with pytest.raises(RegionMonthlyError):
        service.configured_price_id("weekly")


# --- the flag gates ---------------------------------------------------------


@pytest.mark.parametrize("method, path", [
    ("POST", CHECKOUT),
    ("GET", ORDER),
    ("GET", f"{ORDER}/months/2026-10/download?format=csv"),
])
async def test_flag_off_is_the_same_404_as_an_unknown_route_even_unauthenticated(monkeypatch, _isolation, method, path):
    _settings(monkeypatch, region_monthly_enabled=False)
    _no_database(monkeypatch)
    response = await _request(method, path, json=BODY if method == "POST" else None)
    unknown = await _request("GET", "/api/v1/region-monthly/no-such-route")
    assert response.status_code == 404
    assert (response.status_code, response.json()) == (unknown.status_code, unknown.json())
    assert _isolation.calls == []


@pytest.mark.parametrize("closed", [
    {"region_monthly_checkout_enabled": False},
    {"billing_checkout_enabled": False},
    {"stripe_secret_key": ""},
    {"stripe_price_region_monthly_single": ""},
    {"stripe_price_region_monthly_six": ""},
    {"stripe_price_region_monthly_twelve": ""},
])
async def test_checkout_is_a_plain_503_unless_every_switch_and_all_three_prices_are_set(monkeypatch, _isolation, closed):
    _settings(monkeypatch, **closed)
    _no_database(monkeypatch)
    _session_identity()
    response = await _request("POST", CHECKOUT, json=BODY)
    assert response.status_code == 503
    assert isinstance(response.json()["detail"], str)
    assert _isolation.calls == []


async def test_checkout_needs_the_approved_b2b_terms_and_a_confirmed_business_use(monkeypatch, _isolation):
    _settings(monkeypatch)
    _no_database(monkeypatch)
    _session_identity()
    wrong_version = await _request("POST", CHECKOUT, json={**BODY, "terms_version": "b2b-old"})
    unconfirmed = await _request("POST", CHECKOUT, json={**BODY, "business_use_confirmed": False})
    _settings(monkeypatch, b2b_terms_version="", b2b_terms_sha256="")
    unapproved = await _request("POST", CHECKOUT, json=BODY)
    assert (wrong_version.status_code, unconfirmed.status_code, unapproved.status_code) == (409, 422, 503)
    assert _isolation.calls == []


async def test_an_api_key_cannot_start_a_purchase_only_a_browser_session(monkeypatch, _isolation):
    _settings(monkeypatch)
    _no_database(monkeypatch)
    _session_identity(auth_method="api_key")
    response = await _request("POST", CHECKOUT, json=BODY)
    assert response.status_code == 403
    assert _isolation.calls == []


async def test_a_request_with_a_price_in_it_is_refused_before_anything_else(monkeypatch, _isolation):
    _settings(monkeypatch)
    _no_database(monkeypatch)
    _session_identity()
    response = await _request("POST", CHECKOUT, json={**BODY, "price_pence": 1})
    assert response.status_code == 422
    assert _isolation.calls == []


# --- the readiness gate ---------------------------------------------------


async def test_readiness_gap_reports_each_closed_check():
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=True)

    def health(**parts):
        async def run(_conn):
            return {"readiness_ok": True, "source_fresh": True, "units": {"countsReconciled": True}, **parts}
        return run

    assert await service.readiness_gap(conn, health()) is None
    assert "readiness" in await service.readiness_gap(conn, health(readiness_ok=False))
    assert "not fresh" in await service.readiness_gap(conn, health(source_fresh=False))
    assert "reconciled" in await service.readiness_gap(conn, health(units={"countsReconciled": False}))
    assert "reconciled" in await service.readiness_gap(conn, health(units=None))
    conn.fetchval = AsyncMock(return_value=False)
    assert "builds" in await service.readiness_gap(conn, health())


# --- UK month boundaries around the clock changes ------------------------------

BUILT_TO_AUG = {d(2026, m) for m in range(4, 9)}  # April to August 2026


def resolve(kind, first, now, built, **kwargs):
    return rm.resolve_purchase(kind, first, now, region="London", built_months=built, **kwargs)


def refusal_code(*args, **kwargs) -> str:
    with pytest.raises(RegionMonthlyError) as raised:
        resolve(*args, **kwargs)
    return raised.value.code


def test_september_can_be_sold_unbuilt_only_until_midnight_on_the_7th_in_british_summer_time():
    first = d(2026, 9)
    # 00:00 BST on 7 October is 23:00Z on 6 October. One second earlier the month is still a future month.
    before = datetime(2026, 10, 6, 22, 59, 59, tzinfo=UTC)
    at = datetime(2026, 10, 6, 23, 0, 0, tzinfo=UTC)
    assert refusal_code("single", first, before, BUILT_TO_AUG) == "future_months_not_accepted"
    purchase = resolve("single", first, before, BUILT_TO_AUG, accept_future_months=True)
    assert [(m.status, m.available_from) for m in purchase.months] == [("future", d(2026, 10, 7))]
    # From the instant it can be built, an unbuilt month is refused as unbuilt, never sold as a future month.
    assert refusal_code("single", first, at, BUILT_TO_AUG) == "month_not_built"
    assert refusal_code("single", first, at, BUILT_TO_AUG, accept_future_months=True) == "month_not_built"
    assert resolve("single", first, at, BUILT_TO_AUG | {first}).months[0].status == "built"


def test_october_can_be_sold_unbuilt_only_until_midnight_on_the_7th_after_the_clocks_go_back():
    first = d(2026, 10)
    built = BUILT_TO_AUG | {d(2026, 9)}
    # In November the clocks are on GMT, so midnight on the 7th is 00:00Z.
    before = datetime(2026, 11, 6, 23, 59, 59, tzinfo=UTC)
    at = datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC)
    assert refusal_code("single", first, before, built) == "future_months_not_accepted"
    assert resolve("single", first, before, built, accept_future_months=True).future_months[0].available_from == d(2026, 11, 7)
    assert refusal_code("single", first, at, built) == "month_not_built"


def test_april_2027_follows_the_march_clock_change():
    first = d(2027, 4)
    built = {d(2026, m) for m in range(4, 13)} | {d(2027, m) for m in range(1, 4)}
    # BST began on 28 March 2027, so 00:00 on 7 May is 23:00Z on 6 May.
    assert refusal_code("single", first, datetime(2027, 5, 6, 22, 59, 59, tzinfo=UTC), built) == "future_months_not_accepted"
    assert refusal_code("single", first, datetime(2027, 5, 6, 23, 0, 0, tzinfo=UTC), built) == "month_not_built"


def test_a_twelve_month_purchase_across_both_clock_changes_covers_exactly_those_calendar_months():
    now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    built = {d(2026, m) for m in range(4, 11)}
    purchase = resolve("twelve", d(2026, 4), now, built, accept_future_months=True)
    assert [m.period_month for m in purchase.months] == [d(2026, m) for m in range(4, 13)] + [d(2027, 1), d(2027, 2), d(2027, 3)]
    assert [m.status for m in purchase.months] == ["built"] * 7 + ["future"] * 5
    assert [m.available_from for m in purchase.future_months] == [
        d(2026, 12, 7), d(2027, 1, 7), d(2027, 2, 7), d(2027, 3, 7), d(2027, 4, 7)]
    assert purchase.price_pence == 44500
    # The month list is dates, so no clock change can move a month: each starts on the 1st.
    assert all(m.period_month.day == 1 for m in purchase.months)


def test_the_twelve_month_horizon_moves_at_the_instant_a_month_becomes_buildable():
    # Latest buildable month is September until 00:00Z on 7 November, then October.
    before = datetime(2026, 11, 6, 23, 59, 59, tzinfo=UTC)
    at = datetime(2026, 11, 7, 0, 0, 0, tzinfo=UTC)
    assert rm.latest_buildable_month(before) == d(2026, 9) and rm.latest_buildable_month(at) == d(2026, 10)
    built = {d(2026, m) for m in range(4, 10)}
    # The 12 months from October 2026 end in September 2027: inside the horizon at both instants.
    resolve("twelve", d(2026, 10), before, built, accept_future_months=True)
    # The 12 months from November 2026 end in October 2027: past the horizon until October counts as buildable.
    assert refusal_code("twelve", d(2026, 11), before, built, accept_future_months=True) == "future_months_too_far"
    assert resolve("twelve", d(2026, 11), at, built | {d(2026, 10)}, accept_future_months=True).months[-1].period_month == d(2027, 10)


@pytest.mark.parametrize(("first", "expected"), [
    ("2026-03", "month_before_earliest"), ("2025-12", "month_before_earliest"), ("2026-13", "months_malformed"),
    ("2026-00", "months_malformed"), ("", "months_malformed"), ("October 2026", "months_malformed"),
])
def test_months_the_product_cannot_sell_are_refused_by_the_stage_one_rules(first, expected):
    now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    with pytest.raises(RegionMonthlyError) as raised:
        resolve("single", rm.parse_month(first), now, BUILT_TO_AUG)
    assert raised.value.code == expected


def test_a_purchase_must_cover_months_in_order_with_no_gaps():
    now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    built = {d(2026, m) for m in range(4, 11)}
    skipping = [d(2026, 5), d(2026, 6), d(2026, 8), d(2026, 9), d(2026, 10), d(2026, 11)]
    assert refusal_code("six", d(2026, 5), now, built, months=skipping, accept_future_months=True) == "months_not_consecutive"
    assert refusal_code("six", d(2026, 5), now, built, months=skipping[:3]) == "months_count_mismatch"


# --- pinned months, metadata and the buyer's view ---------------------------------


def fake_order(**overrides):
    months = [d(2026, 9), d(2026, 10), d(2026, 11), d(2026, 12)]
    order = {
        "id": "00000000-0000-4000-8000-000000000001", "user_id": 7, "region": "London", "service_slug": None,
        "kind": "six", "month_count": 6, "months": months, "future_months": [d(2026, 11), d(2026, 12)],
        "future_available_from": [d(2026, 12, 7), d(2027, 1, 7)], "price_pence": 24500, "currency": "gbp",
        "stripe_price_id": PRICE_IDS["six"], "terms_version": "b2b-1", "terms_sha256": "a" * 64, "state": "paid",
        "created_at": datetime(2026, 11, 20, 12, 0, tzinfo=UTC), "paid_at": datetime(2026, 11, 20, 12, 5, tzinfo=UTC),
        "refunded_at": None,
    }
    order.update(overrides)
    return order


def test_checkout_metadata_carries_the_pinned_purchase_and_no_empty_value():
    metadata = service.build_checkout_metadata(fake_order())
    assert metadata["type"] == "region_monthly" and metadata["service"] == "all-services"
    assert metadata["months"] == "2026-09,2026-10,2026-11,2026-12" and metadata["price_pence"] == "24500"
    assert all(value for value in metadata.values())  # Stripe drops a key whose value is empty
    assert service.build_checkout_metadata(fake_order(service_slug="home-care"))["service"] == "home-care"


def test_a_month_is_available_only_with_a_paid_order_an_entitlement_and_a_stored_build():
    now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    entitled = {d(2026, 9), d(2026, 10), d(2026, 11)}
    build = {"build_version": 1}

    def state(order, month, **kw):
        return service.month_availability(order, month, entitled=kw.get("entitled", entitled), build=kw.get("build"), now=now)

    paid = fake_order()
    assert state(paid, d(2026, 10), build=build) == "available"
    assert state(paid, d(2026, 11)) == "will_be_available"  # a future month with no build
    assert state(paid, d(2026, 11), build=build) == "available"  # a build exists, so it can be downloaded
    assert state(paid, d(2026, 10)) == "not_built"  # its day has passed and nothing was built
    assert state(paid, d(2026, 12), build=build) == "being_set_up"  # paid, but this month has no entitlement
    for other in ("pending_payment", "expired"):
        assert state(fake_order(state=other), d(2026, 10), build=build) == "not_paid"
    assert state(fake_order(state="refunded"), d(2026, 10), build=build) == "refunded"


def test_the_order_view_never_holds_stripe_identifiers_or_the_terms_hash():
    now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    view = service.order_view(
        fake_order(), builds={d(2026, 9): {"build_version": 2, "content_sha256": "b" * 64}},
        entitled={d(2026, 9), d(2026, 10), d(2026, 11), d(2026, 12)}, now=now,
    )
    assert "stripe" not in str(view).lower() and "a" * 64 not in str(view)
    assert [(m["month"], m["availability"]) for m in view["months"]] == [
        ("2026-09", "available"), ("2026-10", "not_built"), ("2026-11", "will_be_available"), ("2026-12", "will_be_available")]
    first, _october, november, _december = view["months"]
    assert (first["build_version"], first["content_sha256"], first["was_future_at_purchase"]) == (2, "b" * 64, False)
    assert (november["was_future_at_purchase"], november["available_from"]) == (True, "2026-12-07")
    assert november["text"] == "Will be available on 7 December 2026."
    assert view["future_month_notice"] == rm.FUTURE_MONTH_NOTICE and view["future_months"] == ["2026-11", "2026-12"]


# --- the deliverables ------------------------------------------------------


def csv_rows(data: bytes):
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"))))


def test_the_csv_is_deterministic_and_carries_every_required_field():
    build = sample_build(d(2026, 7))
    first, second = render.render_csv(build), render.render_csv(build)
    assert first == second
    rows = csv_rows(first)
    assert tuple(rows[0]) == render.CSV_COLUMNS
    for column, expected in {
        "report": "Region Monthly", "region": "London", "service": "All services", "service_slug": "",
        "period_month": "2026-07", "build_version": "1", "built_at": "2026-11-07T06:30:05.123456Z",
        "data_cutoff": "2026-11-20T12:00:00Z", "content_sha256": build["content_sha256"],
    }.items():
        assert {row[column] for row in rows} == {expected}, column
    limits = [row["text"] for row in rows if row["row_type"] == "limit"]
    assert limits[: len(build["limits"])] == build["limits"]  # the limits come first, as stored
    figures = [row for row in rows if row["row_type"] == "figure"]
    ratings = {row["breakdown"]: row["value"] for row in figures if row["metric"] == "ratings_published"}
    assert ratings == {"Outstanding": "1", "Good": "2", "Requires improvement": "1", "Inadequate": "1",
                       "No published rating value": "2", "Total": "7"}
    registrations = [row for row in figures if row["metric"] == "new_registrations"]
    assert [(row["value"], row["coverage_status"]) for row in registrations] == [("6", "available")]
    # July has no closure figure: the cell is empty, never zero, and says why.
    closures = [row for row in figures if row["metric"] == "closures_observed"]
    assert closures[0]["value"] == "" and closures[0]["coverage_status"] == "not_captured_before"
    assert closures[0]["coverage_text"] == "Not captured before 10 August 2026"
    assert "No figure is given" in closures[0]["text"]


def test_a_month_with_no_rating_figure_says_it_is_not_available_and_a_build_with_a_service_names_it():
    build = sample_build(d(2026, 9), service_slug="home-care")
    rows = csv_rows(render.render_csv(build))
    ratings = [row for row in rows if row["metric"] == "ratings_published"]
    assert len(ratings) == 1 and ratings[0]["value"] == "" and ratings[0]["coverage_status"] == "not_available_after"
    assert "11 August 2026" in ratings[0]["coverage_text"]
    assert {row["service"] for row in rows} == {"Home Care"} and {row["service_slug"] for row in rows} == {"home-care"}


def test_the_pdf_is_deterministic_and_states_the_build_the_coverage_and_the_limits():
    build = sample_build(d(2026, 7))
    pdf_a, pdf_b = render.render_pdf(build), render.render_pdf(build)
    assert pdf_a == pdf_b
    reader = PdfReader(io.BytesIO(pdf_a))
    text = "\n".join(page.extract_text() for page in reader.pages)
    flat = text.replace("\n", " ")
    for needle in ("Region Monthly", "London", "All services", "July 2026", "Build version: 1",
                   "2026-11-07T06:30:05.123456Z", "2026-11-20T12:00:00Z"):
        assert needle in flat, needle
    assert build["content_sha256"] in text.replace("\n", "")
    for limit in build["limits"]:
        assert limit[:50] in flat
    assert "Not captured before 10 August 2026" in flat and "No figure" in flat
    assert "Requires improvement" in flat
    september = PdfReader(io.BytesIO(render.render_pdf(sample_build(d(2026, 9))))).pages
    assert "not available from the rating history table after 11 august 2026" in " ".join(
        p.extract_text() for p in september).replace("\n", " ").lower()


def test_a_second_build_version_changes_the_files_and_the_name():
    one = sample_build(d(2026, 9))
    two = sample_build(d(2026, 9), build_version=2, metrics={**one["metrics"], "new_registrations": 7})
    assert render.render_csv(one) != render.render_csv(two) and one["content_sha256"] != two["content_sha256"]
    assert render.deliverable_filename("London", None, d(2026, 9), 1, "csv") == \
        "caregist-region-monthly-london-all-services-2026-09-v1.csv"
    assert render.deliverable_filename("Yorkshire & Humberside", "home-care", d(2026, 10), 2, "pdf") == \
        "caregist-region-monthly-yorkshire-and-humberside-home-care-2026-10-v2.pdf"
    with pytest.raises(ValueError):
        render.deliverable_filename("London", None, d(2026, 9), 1, "zip")


def test_a_build_whose_stored_hash_does_not_match_is_never_served():
    build = sample_build(d(2026, 9))
    assert render.verify_build(build)
    assert service.render_download(build, "csv").sha256
    tampered = {**build, "metrics": {**build["metrics"], "new_registrations": 99}}
    assert not render.verify_build(tampered)
    with pytest.raises(service.RegionMonthlyOrderError):
        service.render_download(tampered, "pdf")
    with pytest.raises(ValueError):
        service.render_download(build, "zip")


def test_download_bytes_hash_is_the_hash_of_the_bytes_and_is_stable():
    build = sample_build(d(2026, 8))
    a, b = service.render_download(build, "csv"), service.render_download(build, "csv")
    assert a.sha256 == b.sha256 and a.content == b.content
    import hashlib

    assert hashlib.sha256(a.content).hexdigest() == a.sha256
    assert service.render_download(build, "pdf").content_type == "application/pdf"


def test_a_spreadsheet_will_not_read_a_value_as_a_formula():
    build = sample_build(d(2026, 9), region="=cmd")
    rows = csv_rows(render.render_csv(build))
    assert {row["region"] for row in rows} == {"'=cmd"}


# --- wording ---------------------------------------------------------------


def _new_customer_text() -> list[str]:
    return [
        render.BUILD_NOTICE, render.CUTOFF_NOTICE, render.HASH_NOTICE, render.SOURCE_NOTICE, render.NO_FIGURE_TEXT,
        *(label for _field, label in render.RATING_ROWS),
        service.MONTHS_ALREADY_HELD, service.CHECKOUT_STILL_OPEN, service.NOT_PAID, service.REFUNDED_TEXT,
        service.BEING_SET_UP, service.WILL_BE_AVAILABLE, service.NOT_BUILT_YET, *service.AVAILABILITY_TEXT.values(),
    ]


@pytest.mark.parametrize("text", _new_customer_text())
def test_new_customer_text_has_no_completeness_score_or_risk_wording(text):
    assert [phrase for phrase in BANNED if phrase in text.lower()] == []


def test_the_limits_stored_with_every_build_make_no_claim_of_completeness():
    for limit in rm.LIMITS:
        lowered = limit.lower()
        assert not any(phrase in lowered for phrase in ("complete", "every", "all history")), limit
    assert not any(phrase in rm.FUTURE_MONTH_NOTICE.lower() for phrase in ("complete", "every", "all history"))


def test_the_rendered_files_hold_no_banned_wording_beyond_the_stored_limits_and_definitions():
    build = sample_build(d(2026, 7))
    own = [row["text"] for row in csv_rows(render.render_csv(build)) if row["row_type"] == "limit"][len(build["limits"]):]
    assert [phrase for text in own for phrase in BANNED if phrase in text.lower()] == []


def test_the_new_modules_pass_the_evidence_language_guard():
    from tools.evidence_language_guard import scan_text

    for name in ("api/services/region_monthly_orders.py", "api/services/region_monthly_render.py",
                 "api/routers/region_monthly_orders.py", "api/queries/region_monthly_orders.py",
                 "tools/retry_region_monthly_entitlements.py"):
        assert scan_text(name, (REPO_ROOT / name).read_text(encoding="utf-8")) == [], name


# --- webhook wiring ----------------------------------------------------------


async def test_the_webhook_hands_only_region_monthly_sessions_to_the_new_handler():
    conn = MagicMock()
    with patch.object(billing.region_monthly_orders, "handle_checkout_completed", AsyncMock()) as handler:
        await billing._handle_checkout_completed(conn, {"id": "cs_1", "metadata": {"type": "region_monthly"}})
    handler.assert_awaited_once()
    with patch.object(billing.region_monthly_orders, "handle_checkout_completed", AsyncMock()) as handler, \
            patch.object(billing, "_record_manual_payment_link_sale", AsyncMock()):
        await billing._handle_checkout_completed(conn, {"id": "cs_2", "metadata": {}, "payment_link": "plink_1"})
    handler.assert_not_awaited()
    with patch.object(billing.region_monthly_orders, "handle_checkout_completed", AsyncMock()) as handler, \
            patch.object(billing.operator_history_orders, "handle_checkout_completed", AsyncMock()) as other:
        await billing._handle_checkout_completed(conn, {"id": "cs_3", "metadata": {"type": "operator_history"}})
    handler.assert_not_awaited()
    other.assert_awaited_once()


async def test_a_full_refund_marks_the_region_monthly_order_and_a_partial_one_does_not():
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    charge = {"object": "charge", "id": "ch_1", "amount": 24500, "payment_intent": "pi_1"}
    with patch.object(billing.region_monthly_orders, "mark_refunded", AsyncMock()) as mark, \
            patch.object(billing.operator_history_orders, "mark_refunded", AsyncMock()), \
            patch.object(billing, "write_audit_log", AsyncMock()):
        await billing._handle_refund(conn, {**charge, "amount_refunded": 24500, "refunded": True})
        mark.assert_awaited_once_with(conn, "pi_1")
        mark.reset_mock()
        await billing._handle_refund(conn, {**charge, "amount_refunded": 8000, "refunded": False})
        mark.assert_not_awaited()


def test_the_shared_webhook_records_an_entitlement_failure_after_rollback():
    source = (REPO_ROOT / "api" / "routers" / "billing.py").read_text(encoding="utf-8")
    assert "region_monthly_orders.EntitlementError" in source
    error = service.EntitlementError("order-1", "boom", {"payment_intent": "pi_1"})
    assert isinstance(error, RuntimeError) and hasattr(error, "record_failure")
