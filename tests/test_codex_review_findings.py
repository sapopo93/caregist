"""Regression tests for the independent (Codex) review of 20 Oct 2026.

Each test reproduces a finding with the reviewer's own example and pins the fix.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from api.routers import billing
from api.services import crm_ai
from api.services import territory_brief as tb
from tools import order_ledger as ledger
from tools import orders
from tools import prepare_order as po

AS_OF = date(2026, 10, 20)


def _row(**extra):
    row = {"locationId": "1-x", "providerId": "P-x", "name": "Home", "region": "North West",
           "registrationStatus": "Registered", "gacServiceTypes": [{"description": "Domiciliary care service"}]}
    row.update(extra)
    return row


def _reason(event):
    return tb._reason(org_name="Org", events=[event], beds=None, service_types=("Domiciliary care service",),
                      territory="North West", provider_cluster=1, current_rating=None,
                      has_rating_history=False, as_of=AS_OF)


# Finding 5: "No CQC inspection recorded since registration on 01 Oct 2026, over 3 years ago."
def test_recent_registration_without_inspection_is_not_called_three_years_old():
    event = tb._provider_group_event(_row(registrationDate="2026-10-01"), "stale_inspection", as_of=AS_OF)
    text = _reason(event)

    assert "over 3 years" not in text and "years ago" not in text
    assert "01 Oct 2026 (19 days ago)" in text
    assert "not because an inspection is overdue" in text


def test_genuinely_old_inspection_states_its_real_age():
    event = tb._provider_group_event(_row(lastInspection={"date": "2019-06-01"}), "stale_inspection", as_of=AS_OF)
    assert "about 7 years ago before the source date" in _reason(event)


# Finding 6: missing rating must not become "not yet inspected / first inspection ahead".
def test_no_published_rating_makes_no_inspection_claim():
    event = tb._provider_group_event(_row(registrationDate="2024-02-01"), "not_yet_inspected", as_of=AS_OF)
    text = _reason(event)

    assert "first inspection" not in text and "not yet inspected" not in text.lower()
    assert "No published CQC rating on record" in text
    assert tb._primary_signal([event]) == "No published rating"


def test_missing_registration_date_is_never_presented_as_one():
    event = tb._provider_group_event(_row(), "not_yet_inspected", as_of=AS_OF)
    text = _reason(event)

    assert "does not record a registration date" in text
    assert AS_OF.strftime("%d %b %Y") not in text


# Finding 1: a sent issue 1 must not mark pending issue 2 as sent.
def test_sent_digest_issue_one_does_not_mark_issue_two(monkeypatch):
    issue1 = "Your CareGist Weekly Digest: North West, issue 1 of 4 (ref WDP-1)"
    issue2 = "Your CareGist Weekly Digest: North West, issue 2 of 4 (ref WDP-1)"
    encoded = "=?utf-8?q?Your_CareGist_Weekly_Digest=3A_North_West=2C_issue_1_of_4_=28ref_WDP-1=29?="

    class FakeImap:
        def __init__(self, *a, **k):
            pass

        def login(self, *a):
            pass

        def list(self):
            return "OK", [b'(\\Sent) "/" "Sent"']

        def select(self, *a, **k):
            return "OK", [b"1"]

        def search(self, charset, *criteria):
            return ("OK", [b""]) if criteria[0] == "HEADER" else ("OK", [b"5"])

        def fetch(self, number, query):
            return "OK", [(b"5", f"Subject: {encoded}\r\nDate: Mon, 26 Oct 2026 09:00:00 +0000\r\n\r\n".encode())]

        def logout(self):
            pass

    monkeypatch.setattr(orders.imaplib, "IMAP4_SSL", FakeImap)
    pending = [
        {"order_ref": "WDP-1", "buyer_email": "d@example.com", "message_id": "<i1>", "subject": issue1,
         "drafted_at": "2026-10-26T08:00:00+00:00"},
        {"order_ref": "WDP-1", "buyer_email": "d@example.com", "message_id": "<i2>", "subject": issue2,
         "drafted_at": "2026-10-26T08:00:00+00:00"},
    ]

    found = orders.find_sent({"OUTREACH_IMAP_PASSWORD": "pw"}, pending)

    assert found == {"<i1>": "2026-10-26T09:00:00+00:00"}


# Finding 2: re-quoting a Digest must replace the recorded scope.
def test_digest_requote_replaces_the_recorded_scope(monkeypatch, tmp_path):
    monkeypatch.setenv("CAREGIST_ORDER_LEDGER", str(tmp_path / "l.sqlite"))
    common = dict(order_ref="WDP-2", product="digest", stage="quote", buyer_email="d@example.com",
                  buyer_name="", company="", amount_pence=15000, quoted_count=None,
                  draft_location="saved", folder="/tmp")
    ledger.record_email(**common, scope="North West · from 2026-10-26",
                        scope_args={"region": "North West", "start_date": "2026-10-26"},
                        message_id="<q1>", subject="S1 (ref WDP-2)")
    with ledger.connect() as conn:
        first_id = ledger.get_order(conn, "WDP-2")["emails"][0]["id"]
    ledger.record_email(**common, scope="London · from 2026-11-02",
                        scope_args={"region": "London", "start_date": "2026-11-02"},
                        message_id="<q2>", subject="S2 (ref WDP-2)", supersede_email_id=first_id)

    with ledger.connect() as conn:
        order = ledger.get_order(conn, "WDP-2")
    assert order["scope_args"] == {"region": "London", "start_date": "2026-11-02"}


# Findings 3 and 4: payment identity and timing.
def _stripe_session(**overrides):
    session = {"id": "cs_ok", "payment_status": "paid", "amount_total": 74500, "currency": "gbp",
               "payment_link": po.PRODUCT_PAYMENT_LINKS[74500], "created": 1792500000,
               "customer_details": {"email": "b@example.com"}}
    session.update(overrides)
    return session


@pytest.mark.parametrize(
    "overrides",
    [
        {"payment_link": "plink_other_business"},
        {"currency": "usd"},
        {"payment_link": po.PRODUCT_PAYMENT_LINKS[15000]},  # Digest link at the Brief price
        {"payment_status": "unpaid"},
    ],
)
def test_only_the_products_own_link_in_gbp_counts(monkeypatch, overrides):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"data": [_stripe_session(**overrides)]}

    monkeypatch.setattr("httpx.get", lambda *a, **k: Response())
    assert po._payments_from_stripe("sk_test_dummy", "b@example.com", 74500, 30) == []


def test_stripe_is_authoritative_and_the_sales_record_only_a_fallback(monkeypatch):
    calls = []
    monkeypatch.setattr(po, "_payments_from_stripe", lambda *a: calls.append("stripe") or [])
    monkeypatch.setattr(po, "_payments_from_sales_record", lambda *a: calls.append("db") or [])

    po.list_payments({"STRIPE_SECRET_KEY": "k", "DATABASE_URL": "d"})
    assert calls == ["stripe"]
    calls.clear()
    po.list_payments({"DATABASE_URL": "d"})
    assert calls == ["db"]


def test_payment_before_the_order_is_rejected_beyond_two_minutes(monkeypatch):
    created = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    payments = [
        {"session": "cs_old", "paid_at": (created - timedelta(minutes=10)).isoformat(), "email": "b@example.com", "amount": 74500, "source": "Stripe"},
        {"session": "cs_skew", "paid_at": (created - timedelta(minutes=1)).isoformat(), "email": "b@example.com", "amount": 74500, "source": "Stripe"},
    ]
    monkeypatch.setattr(po, "list_payments", lambda env, **k: payments)

    found = po.find_payment({}, "b@example.com", 74500, not_before=created.isoformat())
    assert found["session"] == "cs_skew"
    assert po.CLOCK_SKEW == timedelta(minutes=2)


# Finding 7: "Please do not call me again, I have cancer." must still be flagged.
@pytest.mark.parametrize("profile", ["local", "strict"])
def test_do_not_contact_survives_sensitive_line_redaction(profile):
    redacted = crm_ai.redact_transcript(
        "[0000.00] Agent: hello.\n[0002.00] Contact: Please do not call me again, I have cancer.",
        known_entities=(), require_local_ner=(profile == "local"), profile=profile,
    )
    assert "cancer" not in redacted.text and redacted.do_not_contact

    model = crm_ai.CallEvaluation.model_validate({
        "summary": "Declined.", "suggested_disposition": "not_interested", "overall_qa_score": 50,
        "customer_sentiment": "negative", "outcome": "Declined", "strengths": [], "coaching_actions": [],
        "compliance_flags": [],
    })
    result = crm_ai.apply_compliance_rules(model, redacted.text, detected_before_redaction=redacted.do_not_contact)

    assert result.suggested_disposition == "do_not_call"
    assert result.compliance_flags[0] == crm_ai.DO_NOT_CONTACT_FLAG


# Finding 9: unpaid sessions are not recorded; a session is recorded once.
class _Conn:
    def __init__(self):
        self.calls = []

    async def execute(self, query, *args):
        self.calls.append((query, args))
        return "INSERT 0 1"


@pytest.mark.asyncio
async def test_unpaid_payment_link_session_is_not_recorded_as_a_sale():
    conn = _Conn()
    await billing._record_manual_payment_link_sale(conn, {"id": "cs_u", "payment_status": "unpaid", "payment_link": "plink"})
    assert conn.calls == []


@pytest.mark.asyncio
async def test_paid_session_is_recorded_once_per_session():
    conn = _Conn()
    await billing._record_manual_payment_link_sale(conn, {
        "id": "cs_p", "payment_status": "paid", "payment_link": "plink", "amount_total": 74500,
        "currency": "gbp", "customer_details": {"email": "b@example.com"},
    })
    (lock_query, lock_args), (query, args) = conn.calls
    assert "pg_advisory_xact_lock" in lock_query and lock_args == ("manual_sale:cs_p",)
    assert "WHERE NOT EXISTS" in query and "stripe_checkout_session_id' = $3" in query
    assert args[2] == "cs_p" and json.loads(args[1])["payment_status"] == "paid"


# ---- Second review ----------------------------------------------------------- #


def _imap_returning(raw_header: bytes):
    class FakeImap:
        def __init__(self, *a, **k):
            pass

        def login(self, *a):
            pass

        def list(self):
            return "OK", [b'(\\Sent) "/" "Sent"']

        def select(self, *a, **k):
            return "OK", [b"1"]

        def search(self, charset, *criteria):
            return ("OK", [b""]) if criteria[0] == "HEADER" else ("OK", [b"5"])

        def fetch(self, number, query):
            return "OK", [(b"5", raw_header)]

        def logout(self):
            pass

    return FakeImap


def _pending(subject, drafted_at="2026-10-20T12:00:00+00:00"):
    return [{"order_ref": "TOB-1", "buyer_email": "b@example.com", "message_id": "<m>",
             "subject": subject, "drafted_at": drafted_at}]


def test_unreadable_subject_charset_is_skipped_not_fatal(monkeypatch):
    monkeypatch.setattr(orders.imaplib, "IMAP4_SSL", _imap_returning(
        b"Subject: =?x-unknown-charset?q?Hello?=\r\nDate: Tue, 20 Oct 2026 13:00:00 +0000\r\n\r\n"))
    assert orders.find_sent({"OUTREACH_IMAP_PASSWORD": "pw"}, _pending("Hello (ref TOB-1)")) == {}


def test_an_email_sent_before_this_draft_does_not_mark_it_sent(monkeypatch):
    subject = "Your Territory Opportunity Brief scope: North East (ref TOB-1)"
    monkeypatch.setattr(orders.imaplib, "IMAP4_SSL", _imap_returning(
        f"Subject: {subject}\r\nDate: Tue, 20 Oct 2026 09:00:00 +0000\r\n\r\n".encode()))
    assert orders.find_sent({"OUTREACH_IMAP_PASSWORD": "pw"}, _pending(subject)) == {}


def test_stripe_lookup_follows_every_page(monkeypatch):
    pages = [
        {"data": [_stripe_session(id="cs_a")], "has_more": True},
        {"data": [_stripe_session(id="cs_b", client_reference_id="TOB-9")], "has_more": False},
    ]
    seen_params = []

    class Response:
        def __init__(self, body):
            self.body = body

        def raise_for_status(self):
            pass

        def json(self):
            return self.body

    def fake_get(url, params, auth, timeout):
        seen_params.append(dict(params))
        return Response(pages[len(seen_params) - 1])

    monkeypatch.setattr("httpx.get", fake_get)
    found = po._payments_from_stripe("sk_test_dummy", None, 74500, 30)

    assert [f["session"] for f in found] == ["cs_a", "cs_b"]
    assert seen_params[1]["starting_after"] == "cs_a"
    assert found[1]["order_ref"] == "TOB-9"


def test_payment_links_match_the_published_manifest():
    manifest = json.loads((po.REPO_ROOT / "deploy" / "stripe-price-manifest.json").read_text())
    brief = manifest["products"]["territory-opportunity-brief"]["payment_link"]
    assert brief["id"] == po.PRODUCT_PAYMENT_LINKS[po.BRIEF_AMOUNT_PENCE]
    assert brief["url"] == po.BRIEF_PAYMENT_LINK


# ---- Final review ------------------------------------------------------------ #


def _quote_row(ref="TOB-F", email="f@example.com", **extra):
    base = dict(order_ref=ref, product="brief", stage="quote", buyer_email=email, buyer_name="", company="",
                scope="North East", scope_args={"region": "North East"}, amount_pence=74500, quoted_count=30,
                message_id=f"<{ref}-q-{len(extra)}>", subject=f"S (ref {ref})", draft_location="saved", folder="/tmp")
    base.update(extra)
    return base


def test_ledger_steps_run_in_one_write_locked_transaction(monkeypatch, tmp_path):
    monkeypatch.setenv("CAREGIST_ORDER_LEDGER", str(tmp_path / "l.sqlite"))
    with ledger.connect() as conn:
        assert conn.in_transaction  # BEGIN IMMEDIATE taken before any read


def test_paid_guard_holds_even_if_the_earlier_read_was_stale(monkeypatch, tmp_path):
    monkeypatch.setenv("CAREGIST_ORDER_LEDGER", str(tmp_path / "l.sqlite"))
    ledger.record_email(**_quote_row())
    with ledger.connect() as conn:
        first_id = ledger.get_order(conn, "TOB-F")["emails"][0]["id"]
        ledger.record_payment(conn, "TOB-F", {"paid_at": "2026-10-20", "session": "cs_f", "source": "Stripe"})
    real_get = ledger.get_order

    def stale(conn, ref):  # the read misses the payment that committed in between
        order = real_get(conn, ref)
        return {**order, "paid_at": None} if order else order

    monkeypatch.setattr(ledger, "get_order", stale)
    with pytest.raises(ledger.LedgerError):
        ledger.record_email(**_quote_row(scope_args={"region": "London"}, message_id="<late>", supersede_email_id=first_id))
    monkeypatch.setattr(ledger, "get_order", real_get)
    with ledger.connect() as conn:
        assert ledger.get_order(conn, "TOB-F")["scope_args"] == {"region": "North East"}


def test_a_second_new_order_for_the_same_buyer_is_refused_inside_the_ledger(monkeypatch, tmp_path):
    # Simulates two quote runs that both passed the preflight check.
    monkeypatch.setenv("CAREGIST_ORDER_LEDGER", str(tmp_path / "l.sqlite"))
    ledger.record_email(**_quote_row(ref="TOB-1"))
    with pytest.raises(ledger.LedgerError):
        ledger.record_email(**_quote_row(ref="TOB-2", message_id="<two>"))
    ledger.record_email(**_quote_row(ref="TOB-3", message_id="<three>"), allow_new_order=True)


def test_email_sent_one_minute_before_the_replacement_draft_is_not_counted(monkeypatch):
    subject = "Your Territory Opportunity Brief scope: North East (ref TOB-1)"
    monkeypatch.setattr(orders.imaplib, "IMAP4_SSL", _imap_returning(
        f"Subject: {subject}\r\nDate: Tue, 20 Oct 2026 12:00:00 +0000\r\n\r\n".encode()))
    assert orders.find_sent({"OUTREACH_IMAP_PASSWORD": "pw"},
                            _pending(subject, drafted_at="2026-10-20T12:01:00+00:00")) == {}


def test_message_id_match_is_exact_and_preferred(monkeypatch):
    class FakeImap:
        def __init__(self, *a, **k):
            pass

        def login(self, *a):
            pass

        def list(self):
            return "OK", [b'(\\Sent) "/" "Sent"']

        def select(self, *a, **k):
            return "OK", [b"1"]

        def search(self, charset, *criteria):
            return ("OK", [b"9"]) if criteria[:2] == ("HEADER", "Message-ID") else ("OK", [b""])

        def fetch(self, number, query):
            return "OK", [(b"9", b"Date: Tue, 20 Oct 2026 12:05:00 +0000\r\n\r\n")]

        def logout(self):
            pass

    monkeypatch.setattr(orders.imaplib, "IMAP4_SSL", FakeImap)
    assert orders.find_sent({"OUTREACH_IMAP_PASSWORD": "pw"}, _pending("anything (ref TOB-1)")) == {
        "<m>": "2026-10-20T12:05:00+00:00"}


@pytest.mark.parametrize(
    "session",
    [
        {"payment_status": "paid", "payment_intent": None},
        {"payment_status": "paid", "payment_intent": "pi_not_expanded"},
        {"payment_status": "paid", "payment_intent": {"latest_charge": None}},
        {"payment_status": "paid", "payment_intent": {"latest_charge": {"id": "ch_1"}}},
    ],
)
def test_missing_charge_evidence_fails_closed(monkeypatch, session):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return session

    monkeypatch.setattr("httpx.get", lambda *a, **k: Response())
    assert "cannot be ruled out" in po.payment_still_valid({"STRIPE_SECRET_KEY": "sk_test_dummy"}, "cs_x")


def test_valid_charge_passes_and_refund_fails(monkeypatch):
    def respond(charge):
        class Response:
            def raise_for_status(self):
                pass

            def json(self):
                return {"payment_status": "paid", "payment_intent": {"latest_charge": charge}}

        return lambda *a, **k: Response()

    monkeypatch.setattr("httpx.get", respond({"refunded": False, "amount_refunded": 0, "disputed": False}))
    assert po.payment_still_valid({"STRIPE_SECRET_KEY": "sk_test_dummy"}, "cs_ok") is None
    monkeypatch.setattr("httpx.get", respond({"refunded": False, "amount_refunded": 5000, "disputed": False}))
    assert "refunded" in po.payment_still_valid({"STRIPE_SECRET_KEY": "sk_test_dummy"}, "cs_part")


def test_refund_after_payment_shows_as_a_payment_problem_and_leaves_revenue(monkeypatch, tmp_path):
    monkeypatch.setenv("CAREGIST_ORDER_LEDGER", str(tmp_path / "l.sqlite"))
    ledger.record_email(**_quote_row())
    with ledger.connect() as conn:
        ledger.record_payment(conn, "TOB-F", {"paid_at": "2026-10-20T10:00:00+00:00", "session": "cs_r", "source": "Stripe"})
    monkeypatch.setattr(po, "list_payments", lambda env, **k: [])
    monkeypatch.setattr(po, "payment_still_valid", lambda env, session: "the payment has been refunded")
    monkeypatch.setattr(orders, "find_sent", lambda env, pending: {})

    orders.refresh({"STRIPE_SECRET_KEY": "sk_test_dummy"})
    table = orders.rows()
    t = orders.totals(table)

    assert table[0]["Status"] == "Payment problem: the payment has been refunded"
    assert t["paid"] == 0 and t["revenue_gbp"] == 0 and t["payment_problems"] == 1
    assert any("Do not deliver" in item for item in orders.actions(table, []))
