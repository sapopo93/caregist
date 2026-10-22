"""Independent adversarial checks for the round-four manual-order review."""

from datetime import timedelta

import pytest

from tests.test_order_workflow import TODAY, mark_all_sent, order, pay, quote_brief, run
from tests.test_order_workflow import world as world  # noqa: F401
from tools import order_ledger as ledger
from tools import orders
from tools import prepare_order as po

FIND_SENT = orders.find_sent
LIST_PAYMENTS = po.list_payments
PAYMENT_STILL_VALID = po.payment_still_valid


@pytest.mark.parametrize("previously_recorded", [False, True])
def test_validation_exception_excludes_payment_until_successful_recheck(world, monkeypatch, previously_recorded):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500, session="cs_recheck", order_ref=ref)
    if previously_recorded:
        with ledger.connect() as conn:
            ledger.record_payment(conn, ref, world["payments"][0])

    def unavailable(env, session):
        raise OSError("Stripe unavailable")

    monkeypatch.setattr(po, "payment_still_valid", unavailable)
    orders.refresh({"STRIPE_SECRET_KEY": "test-placeholder"})
    assert order(ref)["payment_problem"]
    assert orders.totals(orders.rows())["revenue_gbp"] == 0
    assert ledger.order_status(order(ref)).startswith("Payment problem:")

    monkeypatch.setattr(po, "payment_still_valid", lambda env, session: None)
    orders.refresh({"STRIPE_SECRET_KEY": "test-placeholder"})
    assert order(ref)["payment_problem"] is None
    assert orders.totals(orders.rows())["revenue_gbp"] == 745


@pytest.mark.parametrize("previously_recorded", [False, True])
def test_database_fallback_is_tracked_but_not_delivery_authority(world, monkeypatch, previously_recorded):
    ref = quote_brief(world)
    payment = {"email": "a@example.com", "amount": 74500, "session": "cs_database",
               "source": "CareGist sales record", "paid_at": "2026-10-20T23:00:00+00:00", "order_ref": ref}
    if previously_recorded:
        with ledger.connect() as conn:
            ledger.record_payment(conn, ref, payment)
    monkeypatch.setattr(po, "_payments_from_sales_record", lambda *a, **kw: [payment])
    monkeypatch.setattr(po, "list_payments", LIST_PAYMENTS)
    monkeypatch.setattr(po, "payment_still_valid", PAYMENT_STILL_VALID)
    orders.refresh({"DATABASE_URL": "postgresql://test-placeholder"})
    assert order(ref)["payment_session"] == "cs_database"
    assert "Stripe is not configured" in order(ref)["payment_problem"]
    assert orders.totals(orders.rows())["revenue_gbp"] == 0


@pytest.mark.parametrize("failure", ["select", "message_id", "subject", "fetch"])
def test_redraft_refuses_a_failed_sent_check(world, monkeypatch, failure):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", ref) == 0
    before = ledger.live(order(ref)["emails"], "deliver")[0]["message_id"]

    class Mailbox:
        def __init__(self, *a, **kw):
            pass

        def login(self, *a):
            pass

        def list(self):
            return "OK", [b'(\\Sent) "/" "Sent"']

        def select(self, *a, **kw):
            return ("NO", []) if failure == "select" else ("OK", [b"1"])

        def search(self, charset, *criteria):
            if criteria[0] == "HEADER":
                return ("NO", []) if failure == "message_id" else ("OK", [b""])
            return ("NO", []) if failure == "subject" else ("OK", [b"1"])

        def fetch(self, *a):
            return "NO", []

        def logout(self):
            pass

    monkeypatch.setattr(orders, "find_sent", FIND_SENT)
    monkeypatch.setattr(orders.imaplib, "IMAP4_SSL", Mailbox)
    assert run(world, "deliver", "--order-ref", ref, "--redraft") == 2
    assert ledger.live(order(ref)["emails"], "deliver")[0]["message_id"] == before


def test_all_four_digest_issues_keep_distinct_numbers(world):
    start = TODAY - timedelta(days=22)
    assert run(world, "quote", "digest", "--region", "North West", "--start-date", start.isoformat(),
               "--buyer-email", "digest@example.com") == 0
    ref = world["drafts"][-1]["subject"].rsplit("(ref ", 1)[1].rstrip(")")
    pay(world, "digest@example.com", 15000)
    for issue in range(1, 5):
        assert run(world, "deliver", "--order-ref", ref) == 0
        assert world["built"][-1][2] == issue
        assert f"issue {issue} of 4" in world["drafts"][-1]["subject"]
        mark_all_sent(ref)
    assert sorted(ledger.sent_issues(order(ref))) == [1, 2, 3, 4]
    assert run(world, "deliver", "--order-ref", ref) == 2


def test_uncertain_draft_can_be_redrafted_only_after_absence_is_confirmed(world, monkeypatch):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    save = po.save_draft

    def unavailable(*a, **kw):
        raise OSError("reply lost")

    monkeypatch.setattr(po, "save_draft", unavailable)
    monkeypatch.setattr(po, "draft_exists", unavailable)
    assert run(world, "deliver", "--order-ref", ref) == 2
    previous = ledger.live(order(ref)["emails"], "deliver")[0]
    assert previous["draft_location"].startswith("uncertain")
    assert run(world, "deliver", "--order-ref", ref, "--redraft") == 2
    monkeypatch.setattr(po, "draft_exists", lambda *a, **kw: False)
    monkeypatch.setattr(po, "save_draft", save)
    assert run(world, "deliver", "--order-ref", ref, "--redraft") == 0
    current = ledger.live(order(ref)["emails"], "deliver")
    assert len(current) == 1 and current[0]["id"] != previous["id"]


@pytest.mark.parametrize("date_header", ["Date: Tue, 20 Oct 2020 12:00:00 +0000\r\n", ""])
def test_redraft_refuses_ambiguous_sent_date(world, monkeypatch, date_header):
    from tests.test_codex_review_findings import _imap_returning

    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", ref) == 0
    previous = ledger.live(order(ref)["emails"], "deliver")[0]
    message = po.build_email(to="a@example.com", subject=previous["subject"], body="Delivered")
    del message["Date"]
    if date_header:
        message["Date"] = date_header.removeprefix("Date: ").strip()
    header = message.as_bytes()
    monkeypatch.setattr(orders, "find_sent", FIND_SENT)
    monkeypatch.setattr(orders.imaplib, "IMAP4_SSL", _imap_returning(header))
    assert run(world, "deliver", "--order-ref", ref, "--redraft") == 2
    assert ledger.live(order(ref)["emails"], "deliver")[0]["id"] == previous["id"]
