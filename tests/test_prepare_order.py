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
        ("not_yet_inspected", _row("1-c", registrationDate="2026-02-01"), "not_yet_inspected", "No published rating"),
        ("stale_inspection", _row("1-d", lastInspection={"date": "2021-06-01"}), "stale_inspection", "No recent inspection"),
        ("stale_inspection", _row("1-e", registrationDate="2019-01-01"), "stale_inspection", "No recent inspection"),
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
    assert all(o.primary_signal == "No recent inspection" for o in brief.shortlist)
    assert "No inspection in the last 3 years, or none recorded" in brief.executive_summary["headline"]
    assert brief.executive_summary["provider_group"] == "No inspection in the last 3 years, or none recorded"


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
    with pytest.raises(RuntimeError, match="OUTREACH_IMAP_PASSWORD"):
        po.save_draft(po.build_email(to="b@example.com", subject="S", body="B"), env={})


def test_without_a_password_no_order_or_draft_is_recorded(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CAREGIST_ORDER_LEDGER", str(tmp_path / "ledger.sqlite"))
    monkeypatch.setattr(po, "load_env", lambda: {})
    monkeypatch.setattr(po, "build_brief", lambda *a, **k: pytest.fail("must not build"))
    code = po.main(["quote", "brief", "--region", "North East", "--provider-group", "new_90",
                    "--buyer-email", "b@example.com", "--out-base", str(tmp_path)])
    assert code == 2 and "OUTREACH_IMAP_PASSWORD is not set" in capsys.readouterr().out
    from tools import order_ledger
    with order_ledger.connect() as conn:
        assert order_ledger.orders_with_emails(conn) == []


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
    monkeypatch.setattr(po, "load_env", lambda: {"OUTREACH_IMAP_PASSWORD": "test-only"})

    code = po.main([
        "brief", "quote", "--region", "North East", "--provider-group", "requires_improvement",
        "--buyer-email", "b@example.com", "--out-base", str(tmp_path),
    ])

    assert code == 2
    out = capsys.readouterr().out
    assert "NOT READY" in out and "shortlist_minimum: 21 organisations shortlisted" in out
    assert not list(tmp_path.rglob("email.eml"))






def test_shortlist_promise_is_up_to_fifty_in_terms_and_tool():
    terms = (REPO / "frontend" / "app" / "terms" / "page.tsx").read_text(encoding="utf-8")
    assert "shortlist of up to 50 organisations" in terms
    assert "25 to 50" not in terms
    assert po.MAX_SHORTLIST == 50










class _ListOnly:
    def __init__(self, lines):
        self.lines = lines

    def list(self):
        return "OK", self.lines


PRIVATE_EMAIL_LIST = [
    b'(\\HasNoChildren \\UnMarked \\Archive) "/" Archive',
    b'(\\HasNoChildren \\UnMarked \\Sent) "/" Sent',
    b'(\\HasNoChildren \\Marked \\Trash) "/" Trash',
    b'(\\HasNoChildren \\UnMarked \\Drafts) "/" Drafts',
    b'(\\HasNoChildren) "/" INBOX',
]


def test_special_mailbox_reads_private_email_unquoted_names():
    conn = _ListOnly(PRIVATE_EMAIL_LIST)
    assert po.special_mailbox(conn, "\\Drafts", "x") == "Drafts"
    assert po.special_mailbox(conn, "\\Sent", "x") == "Sent"


def test_special_mailbox_reads_quoted_names_with_spaces():
    conn = _ListOnly([b'(\\HasNoChildren \\Drafts) "." "Draft Messages"', b'(\\Sent) NIL "Sent Items"'])
    assert po.special_mailbox(conn, "\\Drafts", "x") == "Draft Messages"
    assert po.special_mailbox(conn, "\\Sent", "x") == "Sent Items"


def test_special_mailbox_falls_back_when_no_flag():
    assert po.special_mailbox(_ListOnly([b'(\\HasNoChildren) "/" INBOX']), "\\Drafts", "Drafts") == "Drafts"
