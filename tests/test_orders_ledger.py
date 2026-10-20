from __future__ import annotations

import pytest

from tools import order_ledger as ledger
from tools import orders
from tools import prepare_order as po


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("CAREGIST_ORDER_LEDGER", str(path))
    return path


def _record(ref, *, stage="quote", product="brief", email="b@example.com", issue=None, message_id=None, payment=None):
    ledger.record_email(
        order_ref=ref, product=product, stage=stage, buyer_email=email, buyer_name="B", company="Co",
        scope="North East · Not yet inspected · All services", scope_args={"region": "North East"},
        amount_pence=74500 if product == "brief" else 15000, quoted_count=30 if stage == "quote" and product == "brief" else None,
        message_id=message_id or f"<{ref}-{stage}-{issue}@caregist.co.uk>", subject=f"Subject {stage} (ref {ref})",
        draft_location="saved", folder="/tmp/x", issue=issue, payment=payment,
    )


def _order(ref):
    with ledger.connect() as conn:
        return next(o for o in ledger.orders_with_emails(conn) if o["order_ref"] == ref)


def test_status_moves_from_quote_to_complete(db):
    _record("TOB-1")
    assert ledger.order_status(_order("TOB-1")) == "Quote drafted: not sent yet"

    with ledger.connect() as conn:
        ledger.mark_sent(conn, "<TOB-1-quote-None@caregist.co.uk>", "2026-10-20T15:00:00+00:00")
    assert ledger.order_status(_order("TOB-1")) == "Quote sent: awaiting payment"

    with ledger.connect() as conn:
        ledger.record_payment(conn, "TOB-1", {"paid_at": "2026-10-20T16:00:00+00:00", "session": "cs_1", "source": "Stripe"})
    assert ledger.order_status(_order("TOB-1")) == "Paid: prepare delivery"

    _record("TOB-1", stage="deliver")
    assert ledger.order_status(_order("TOB-1")) == "Delivery drafted: press Send"

    with ledger.connect() as conn:
        ledger.mark_sent(conn, "<TOB-1-deliver-None@caregist.co.uk>", "2026-10-21T09:00:00+00:00")
    assert ledger.order_status(_order("TOB-1")) == "Complete"


def test_digest_needs_four_sent_issues(db):
    _record("WDP-1", product="digest", payment={"paid_at": "2026-10-20", "session": "cs_2", "source": "Stripe"})
    for issue in (1, 2):
        _record("WDP-1", product="digest", stage="deliver", issue=issue)
        with ledger.connect() as conn:
            ledger.mark_sent(conn, f"<WDP-1-deliver-{issue}@caregist.co.uk>", "2026-10-27")
    assert ledger.order_status(_order("WDP-1")) == "Paid: issue 3 of 4 due"
    assert orders.rows()[0]["Delivered"] == "2/4 sent"


def test_simultaneous_orders_stay_separate(db):
    _record("TOB-A", email="a@example.com")
    _record("TOB-B", email="b@example.com")
    with ledger.connect() as conn:
        ledger.record_payment(conn, "TOB-B", {"paid_at": "2026-10-20", "session": "cs_b", "source": "Stripe"})

    statuses = {row["Ref"]: row["Status"] for row in orders.rows()}

    assert statuses == {"TOB-A": "Quote drafted: not sent yet", "TOB-B": "Paid: prepare delivery"}


def test_requote_replaces_the_promised_count(db):
    _record("TOB-2")
    first_id = _order("TOB-2")["emails"][0]["id"]
    ledger.record_email(supersede_email_id=first_id, 
        order_ref="TOB-2", product="brief", stage="quote", buyer_email="b@example.com", buyer_name="", company="",
        scope="London · Stale", scope_args={"region": "London"}, amount_pence=74500, quoted_count=21,
        message_id="<requote@caregist.co.uk>", subject="S (ref TOB-2)", draft_location="saved", folder="/tmp",
    )
    assert _order("TOB-2")["quoted_count"] == 21






def test_find_sent_matches_ref_recipient_and_stage(monkeypatch):
    searched = {}

    class FakeImap:
        def __init__(self, *a, **k):
            pass

        def login(self, *a):
            pass

        def list(self):
            return "OK", [b'(\\HasNoChildren \\Sent) "/" "Sent"']

        def select(self, mailbox, readonly):
            searched["mailbox"] = (mailbox, readonly)
            return "OK", [b"1"]

        def search(self, charset, *criteria):
            if criteria[0] == "HEADER":
                return "OK", [b""]
            searched["criteria"] = criteria
            return "OK", [b"7"]

        def fetch(self, number, query):
            return "OK", [(b"7", b"Subject: Your Territory Opportunity Brief scope: North East (ref TOB-9)\r\nDate: Tue, 20 Oct 2026 16:05:00 +0100\r\n")]

        def logout(self):
            pass

    monkeypatch.setattr(orders.imaplib, "IMAP4_SSL", FakeImap)

    found = orders.find_sent(
        {"OUTREACH_IMAP_PASSWORD": "pw"},
        [{"order_ref": "TOB-9", "buyer_email": "b@example.com", "message_id": "<m1>",
          "subject": "Your Territory Opportunity Brief scope: North East (ref TOB-9)",
          "drafted_at": "2026-10-20T15:00:00+00:00"}],
    )

    assert found == {"<m1>": "2026-10-20T15:05:00+00:00"}
    assert searched["mailbox"] == ("Sent", True)
    assert searched["criteria"] == ("SUBJECT", '"TOB-9"', "TO", '"b@example.com"')




def test_order_refs_are_unique_within_the_same_second():
    refs = {po.new_order_ref("brief") for _ in range(200)}
    assert len(refs) > 190
    assert all(r.startswith("TOB-") for r in refs)


def _delivery_args(ref, message_id, **extra):
    return dict(order_ref=ref, product="brief", stage="deliver", buyer_email="a@example.com", buyer_name="",
                company="", scope="North East", scope_args={}, amount_pence=74500, quoted_count=None,
                message_id=message_id, subject="s", draft_location="d", folder="f", **extra)


def test_delivery_redraft_refused_when_original_was_sent_meanwhile(tmp_path):
    path = tmp_path / "l.sqlite"
    ledger.record_email(**{**_delivery_args("TOB-1", "<q@x>"), "stage": "quote"}, path=path)
    ledger.record_email(**_delivery_args("TOB-1", "<d1@x>"), path=path)
    with ledger.connect(path) as conn:
        first = next(e for e in ledger.get_order(conn, "TOB-1")["emails"] if e["stage"] == "deliver")
        # A refresh marks it sent after the redraft run's preflight read the ledger.
        ledger.mark_sent(conn, "<d1@x>", "2026-10-20T12:00:00+00:00")
    with pytest.raises(ledger.LedgerError, match="already sent"):
        ledger.record_email(**_delivery_args("TOB-1", "<d2@x>"), supersede_email_id=first["id"], path=path)
    with ledger.connect(path) as conn:
        deliveries = [e for e in ledger.get_order(conn, "TOB-1")["emails"] if e["stage"] == "deliver"]
    assert [e["message_id"] for e in deliveries] == ["<d1@x>"]


def test_supersede_of_an_already_replaced_draft_is_refused(tmp_path):
    path = tmp_path / "l.sqlite"
    ledger.record_email(**{**_delivery_args("TOB-2", "<q1@x>"), "stage": "quote"}, path=path)
    with ledger.connect(path) as conn:
        (q1,) = ledger.get_order(conn, "TOB-2")["emails"]
    ledger.record_email(**{**_delivery_args("TOB-2", "<q2@x>"), "stage": "quote"}, supersede_email_id=q1["id"], path=path)
    with pytest.raises(ledger.LedgerError, match="sent or replaced"):
        ledger.record_email(**{**_delivery_args("TOB-2", "<q3@x>"), "stage": "quote"},
                            supersede_email_id=q1["id"], path=path)


def test_ledger_refuses_requote_after_quote_sent(tmp_path):
    path = tmp_path / "l.sqlite"
    ledger.record_email(**{**_delivery_args("TOB-3", "<q1@x>"), "stage": "quote"}, path=path)
    with ledger.connect(path) as conn:
        ledger.mark_sent(conn, "<q1@x>", "2026-10-20T12:00:00+00:00")
    with pytest.raises(ledger.LedgerError, match="has been sent"):
        ledger.record_email(**{**_delivery_args("TOB-3", "<q2@x>"), "stage": "quote", "scope": "London"}, path=path)
