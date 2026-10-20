from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from api.services import territory_brief as tb
from tools import prepare_order as po

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolated_ledger(monkeypatch, tmp_path):
    # prepare_order records every drafted email; never touch the real ledger.
    monkeypatch.setenv("CAREGIST_ORDER_LEDGER", str(tmp_path / "ledger.sqlite"))


def test_opportunity_sql_matches_the_website_coverage_query_exactly():
    # The Brief must cover what the buyer was shown; any drift fails here.
    source = (REPO / "frontend" / "lib" / "directory-query-clauses.ts").read_text(encoding="utf-8")
    for group, sql in po.OPPORTUNITY_SQL.items():
        assert f'case "{group}":' in source, group
        assert f'return "{sql}";' in source, group


def test_opportunity_groups_match_the_brief_generator_and_the_site():
    constants = (REPO / "frontend" / "lib" / "directory-constants.ts").read_text(encoding="utf-8")
    assert set(po.OPPORTUNITY_SQL) == set(tb.PROVIDER_GROUP_LABELS)
    for group in po.OPPORTUNITY_SQL:
        assert f'value: "{group}"' in constants


def test_service_aliases_resolve_website_labels_like_the_frontend():
    assert "Domiciliary care service" in po.service_aliases("Homecare Agencies")
    assert "Care home service with nursing" in po.service_aliases("Nursing Homes")
    assert set(po.service_aliases("Doctors/Gps")) >= {"Doctors consultation service", "Doctors treatment service"}
    assert po.service_aliases("home-care") == po.service_aliases("Homecare Agencies")
    assert po.service_aliases("") == []
    assert po.service_aliases("Something new") == ["Something new"]


def test_coverage_query_uses_status_region_aliases_and_group():
    sql, params = po.coverage_query("North West", "stale_inspection", "Homecare Agencies")

    assert "status = 'ACTIVE'" in sql and "region = $1" in sql
    assert "unnest($2::text[])" in sql
    assert po.OPPORTUNITY_SQL["stale_inspection"] in sql
    assert params[0] == "North West" and "Domiciliary care service" in params[1]
    sql_no_service, params_no_service = po.coverage_query("London", "new_90", None)
    assert params_no_service == ["London"] and "unnest" not in sql_no_service


def test_working_days_skip_weekends():
    assert po.add_working_days(date(2026, 10, 16), 3) == date(2026, 10, 21)  # Fri -> Wed
    assert po.add_working_days(date(2026, 10, 20), 3) == date(2026, 10, 23)  # Tue -> Fri


def _row(location_id, **extra):
    row = {
        "locationId": location_id,
        "providerId": f"P-{location_id}",
        "name": f"Home {location_id}",
        "region": "North East",
        "localAuthority": "Gateshead",
        "registrationStatus": "Registered",
        "registrationDate": "2020-01-10",
        "gacServiceTypes": [{"description": "Domiciliary care service"}],
    }
    row.update(extra)
    return row


AS_OF = date(2026, 10, 16)


@pytest.mark.parametrize(
    ("group", "row", "event_type", "signal"),
    [
        ("inadequate", _row("1-a", currentRatings={"overall": {"rating": "Inadequate", "reportDate": "2025-03-01"}}), "rating_current", "Current rating"),
        ("requires_improvement", _row("1-b", currentRatings={"overall": {"rating": "Requires improvement", "reportDate": "2024-05-01"}}), "rating_current", "Current rating"),
        ("not_yet_inspected", _row("1-c", registrationDate="2026-02-01"), "not_yet_inspected", "Not yet inspected"),
        ("stale_inspection", _row("1-d", lastInspection={"date": "2021-06-01"}), "stale_inspection", "Inspection overdue"),
        ("stale_inspection", _row("1-e", registrationDate="2019-01-01"), "stale_inspection", "Inspection overdue"),
    ],
)
def test_each_standing_group_has_dated_cited_evidence(group, row, event_type, signal):
    event = tb._provider_group_event(row, group, as_of=AS_OF)

    assert event is not None and event.event_type == event_type
    assert event.source_url == f"https://www.cqc.org.uk/location/{row['locationId']}"
    assert tb._primary_signal([event]) == signal
    reason = tb._reason(
        org_name="Org", events=[event], beds=None, service_types=("Domiciliary care service",),
        territory="North East", provider_cluster=1, current_rating=None, has_rating_history=False, as_of=AS_OF,
    )
    assert reason and "CQC" in reason
    assert tb._qualification_question(signal, provider_cluster=1, territory="North East") != (
        "What is this organisation's current supplier arrangement, and who decides changes?"
    )


def _write_export(tmp_path, rows):
    locations = tmp_path / "locations.ndjson"
    providers = tmp_path / "providers.ndjson"
    locations.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    providers.write_text(
        "\n".join(json.dumps({"providerId": r["providerId"], "name": f"Provider {r['locationId']}"}) for r in rows) + "\n",
        encoding="utf-8",
    )
    return locations, providers


def test_brief_covers_exactly_the_supplied_location_ids_with_group_evidence(tmp_path):
    rows = [
        _row(f"1-{i}", lastInspection={"date": "2021-01-01"}, registrationDate="2018-01-01") for i in range(4)
    ] + [_row("1-recent", lastInspection={"date": "2026-01-01"}, registrationDate="2026-09-01")]
    locations, providers = _write_export(tmp_path, rows)

    brief = tb.generate_territory_opportunity_brief(
        {"kind": "region", "name": "North East", "window_days": 90, "shortlist_target": 10},
        tb.PurchaseContext(order_reference="t", generated_at=datetime(2026, 10, 20, tzinfo=timezone.utc)),
        locations_source=locations,
        providers_source=providers,
        location_ids=["1-0", "1-1", "1-2"],
        provider_group="stale_inspection",
    )

    assert {o.location_id for o in brief.shortlist} == {"1-0", "1-1", "1-2"}
    assert all(o.primary_signal == "Inspection overdue" for o in brief.shortlist)
    assert "Inspection older than 3 years" in brief.executive_summary["headline"]
    assert brief.executive_summary["provider_group"] == "Inspection older than 3 years"


def test_unknown_provider_group_is_refused(tmp_path):
    locations, providers = _write_export(tmp_path, [_row("1-x")])
    with pytest.raises(tb.ScopeError):
        tb.generate_territory_opportunity_brief(
            {"kind": "region", "name": "North East"},
            tb.PurchaseContext(order_reference="t", generated_at=datetime(2026, 10, 20, tzinfo=timezone.utc)),
            locations_source=locations, providers_source=providers, provider_group="hot_leads",
        )


def test_email_carries_signature_and_attachments(tmp_path):
    pdf = tmp_path / "brief.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    message = po.build_email(to="buyer@example.com", subject="S", body="Hello", attachments=[pdf])

    assert message["From"] == "CareGist <outreach@caregist.co.uk>"
    assert "H-Kay Limited" in message.get_body(("plain",)).get_content()
    assert [a.get_filename() for a in message.iter_attachments()] == ["brief.pdf"]


def test_without_a_password_nothing_touches_the_mailbox(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("IMAP must not be used without a password")

    monkeypatch.setattr(po.imaplib, "IMAP4_SSL", boom)
    result = po.save_draft(po.build_email(to="b@example.com", subject="S", body="B"), env={})

    assert "OUTREACH_IMAP_PASSWORD not set" in result


def test_draft_is_appended_to_drafts_and_never_sent(monkeypatch):
    calls = {}

    class FakeImap:
        def __init__(self, host, port, ssl_context=None):
            calls["host"] = (host, port)

        def login(self, user, password):
            calls["login"] = user

        def list(self):
            return "OK", [b'(\\HasNoChildren) "/" "INBOX"', b'(\\HasNoChildren \\Drafts) "/" "Drafts"']

        def append(self, mailbox, flags, when, data):
            calls["append"] = (mailbox, flags)
            return "OK", [b"done"]

        def logout(self):
            calls["logout"] = True

    monkeypatch.setattr(po.imaplib, "IMAP4_SSL", FakeImap)
    monkeypatch.setattr(po, "smtplib", None, raising=False)

    result = po.save_draft(
        po.build_email(to="b@example.com", subject="S", body="B"),
        env={"OUTREACH_IMAP_PASSWORD": "pw"},
    )

    assert calls["host"] == ("mail.privateemail.com", 993)
    assert calls["login"] == "outreach@caregist.co.uk"
    assert calls["append"] == ("Drafts", "(\\Draft)")
    assert "Drafts" in result
    assert "smtplib" not in po.__dict__ or po.__dict__.get("smtplib") is None


def test_failed_checks_draft_nothing(monkeypatch, tmp_path, capsys):
    def failing_brief(args, *, env, order_dir, now):
        checks = po.Checks()
        checks.add("shortlist_minimum", False, "21 organisations shortlisted")
        return checks, {}, []

    monkeypatch.setattr(po, "build_brief", failing_brief)
    monkeypatch.setattr(po, "save_draft", lambda *a, **k: pytest.fail("must not draft"))

    code = po.main([
        "brief", "quote", "--region", "North East", "--provider-group", "requires_improvement",
        "--buyer-email", "b@example.com", "--out-base", str(tmp_path), "--order-ref", "T1",
    ])

    assert code == 2
    assert "NOT READY" in capsys.readouterr().out
    assert not list(tmp_path.rglob("email.eml"))


def test_digest_quote_lists_four_weekly_dates_and_the_150_link(tmp_path, monkeypatch):
    monkeypatch.setattr(po, "save_draft", lambda *a, **k: "saved")
    code = po.main([
        "digest", "quote", "--region", "North West", "--buyer-email", "b@example.com",
        "--start-date", "2026-10-26", "--out-base", str(tmp_path), "--order-ref", "D1",
    ])

    assert code == 0
    eml = next(tmp_path.rglob("email.eml")).read_text()
    assert po.DIGEST_PAYMENT_LINK in eml
    assert "Mon 26 Oct" in eml and "Mon 16 Nov" in eml


def test_quoted_shortlist_reads_the_latest_successful_quote(tmp_path):
    root = tmp_path / "TOB-1"
    (root / "quote-20261020T100000Z").mkdir(parents=True)
    (root / "quote-20261020T100000Z" / "checks.json").write_text(json.dumps({"ok": True, "summary": {"shortlisted": 19}}))
    (root / "quote-20261020T110000Z").mkdir()
    (root / "quote-20261020T110000Z" / "checks.json").write_text(json.dumps({"ok": False, "summary": {"shortlisted": 3}}))

    assert po.quoted_shortlist(root) == 19
    assert po.quoted_shortlist(tmp_path / "missing") is None


def test_shortlist_promise_is_up_to_fifty_in_terms_and_tool():
    terms = (REPO / "frontend" / "app" / "terms" / "page.tsx").read_text(encoding="utf-8")
    assert "shortlist of up to 50 organisations" in terms
    assert "25 to 50" not in terms
    assert po.MAX_SHORTLIST == 50


@pytest.mark.parametrize("product", ["brief", "digest"])
def test_delivery_is_refused_until_payment_is_found(monkeypatch, tmp_path, capsys, product):
    seen = {}

    def no_payment(env, email, amount):
        seen["args"] = (email, amount)
        return None

    monkeypatch.setattr(po, "find_payment", no_payment)
    monkeypatch.setattr(po, "build_brief", lambda *a, **k: pytest.fail("must not build an unpaid order"))
    monkeypatch.setattr(po, "build_digest_issue", lambda *a, **k: pytest.fail("must not build an unpaid order"))
    monkeypatch.setattr(po, "save_draft", lambda *a, **k: pytest.fail("must not draft an unpaid order"))
    extra = (
        ["--provider-group", "new_90"] if product == "brief"
        else ["--week-ending", "2026-10-25", "--issue", "1"]
    )

    code = po.main([product, "deliver", "--region", "North West", "--buyer-email", "Buyer@Example.com",
                    "--out-base", str(tmp_path), "--order-ref", "P1", *extra])

    assert code == 2
    assert "payment_received" in capsys.readouterr().out
    assert seen["args"] == ("Buyer@Example.com", 74500 if product == "brief" else 15000)
    assert not list(tmp_path.rglob("email.eml"))


def test_quote_never_requires_payment(monkeypatch, tmp_path):
    monkeypatch.setattr(po, "find_payment", lambda *a, **k: pytest.fail("quotes must not check payment"))
    monkeypatch.setattr(po, "save_draft", lambda *a, **k: "saved")

    assert po.main(["digest", "quote", "--region", "London", "--buyer-email", "b@example.com",
                    "--start-date", "2026-10-26", "--out-base", str(tmp_path), "--order-ref", "Q1"]) == 0


def test_paid_delivery_proceeds_and_records_the_payment(monkeypatch, tmp_path):
    pdf = tmp_path / "issue.pdf"
    pdf.write_bytes(b"%PDF")

    def built(args, *, env, order_dir, now):
        checks = po.Checks()
        checks.add("digest_built", True, "ok")
        return checks, {"new_registrations": 4, "ratings_published": 0}, [pdf]

    monkeypatch.setattr(po, "find_payment", lambda env, email, amount: {"source": "Stripe", "session": "cs_live_x", "paid_at": "2026-10-20T15:00:00+00:00"})
    monkeypatch.setattr(po, "build_digest_issue", built)
    monkeypatch.setattr(po, "save_draft", lambda *a, **k: "saved")

    code = po.main(["digest", "deliver", "--region", "North West", "--buyer-email", "b@example.com",
                    "--week-ending", "2026-10-25", "--issue", "1", "--out-base", str(tmp_path / "o"), "--order-ref", "P2"])

    assert code == 0
    report = json.loads(next((tmp_path / "o").rglob("checks.json")).read_text())
    assert report["checks"][0]["check"] == "payment_received" and report["checks"][0]["ok"]
    assert "cs_live_x" in report["checks"][0]["detail"]


def test_stripe_fallback_matches_only_paid_sessions_of_the_right_amount(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [
                {"id": "cs_unpaid", "payment_status": "unpaid", "amount_total": 74500, "created": 1792500000},
                {"id": "cs_other", "payment_status": "paid", "amount_total": 15000, "created": 1792500000},
                {"id": "cs_paid", "payment_status": "paid", "amount_total": 74500, "created": 1792500000},
            ]}

    captured = {}

    def fake_get(url, params, auth, timeout):
        captured["params"] = params
        return Response()

    monkeypatch.setattr("httpx.get", fake_get)

    found = po._payment_from_stripe("sk_test_dummy", " b@example.com ", 74500)

    assert found["session"] == "cs_paid" and found["source"] == "Stripe"
    assert captured["params"]["customer_details[email]"] == "b@example.com"
    assert captured["params"]["status"] == "complete"
