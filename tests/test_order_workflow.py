"""End-to-end rules of the human-led order workflow (prepare_order + ledger + orders).

Each test names the guarantee it protects:
  wrong order never sent, no duplicates, nothing missed, sent count, report.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools import order_ledger as ledger
from tools import orders
from tools import prepare_order as po

TODAY = datetime.now(timezone.utc).date()


@pytest.fixture(autouse=True)
def world(monkeypatch, tmp_path):
    """Isolated ledger, fake mailbox, fake payments and fake pack builders."""
    monkeypatch.setenv("CAREGIST_ORDER_LEDGER", str(tmp_path / "ledger.sqlite"))
    state = {"payments": [], "drafts": [], "built": []}

    def list_payments(env, *, buyer_email=None, amount_pence=None, since_days=180):
        found = [
            p for p in state["payments"]
            if (buyer_email is None or p["email"].lower() == buyer_email.strip().lower())
            and (amount_pence is None or p["amount"] == amount_pence)
        ]
        return sorted(found, key=lambda p: p["paid_at"])

    def save_draft(message, *, env):
        state["drafts"].append({"to": message["To"], "subject": message["Subject"],
                                "files": [a.get_filename() for a in message.iter_attachments()]})
        return "saved to outreach@caregist.co.uk Drafts"

    def build_brief(args, *, env, order_dir, now):
        state["built"].append(("brief", args.order_ref, args.buyer_email, args.region, args.provider_group))
        checks = po.Checks()
        checks.add("shortlist_not_empty", True, "30 organisations")
        if args.stage == "deliver":
            checks.add("matches_quote", 30 >= (args.quoted_count or 0), "ok")
        pdf = order_dir / "brief.pdf"
        pdf.write_bytes(b"%PDF")
        summary = {"region": args.region, "provider_group": "Not yet inspected", "service_type": "All",
                   "locations_in_scope": 1221, "shortlisted": 30, "source_edition": "2026-10-16", "export": "x"}
        return checks, summary, [pdf]

    def build_digest_issue(args, *, env, order_dir, now):
        state["built"].append(("digest", args.order_ref, args.issue, args.week_ending))
        checks = po.Checks()
        checks.add("digest_built", True, "ok")
        pdf = order_dir / f"issue{args.issue}.pdf"
        pdf.write_bytes(b"%PDF")
        return checks, {"new_registrations": 4, "ratings_published": 0}, [pdf]

    monkeypatch.setattr(po, "list_payments", list_payments)
    monkeypatch.setattr(po, "save_draft", save_draft)
    monkeypatch.setattr(po, "build_brief", build_brief)
    monkeypatch.setattr(po, "build_digest_issue", build_digest_issue)
    monkeypatch.setattr(po, "load_env", lambda: {})
    state["out"] = tmp_path / "orders"
    return state


def run(world, *argv):
    return po.main([*argv, "--out-base", str(world["out"])])


def pay(world, email, amount, *, when=None, session=None):
    world["payments"].append({
        "email": email, "amount": amount, "source": "Stripe",
        "session": session or f"cs_{len(world['payments']) + 1}",
        "paid_at": (when or datetime.now(timezone.utc)).isoformat(),
    })


def quote_brief(world, email="a@example.com", *extra):
    assert run(world, "quote", "brief", "--region", "North East", "--provider-group", "not_yet_inspected",
               "--buyer-email", email, *extra) == 0
    # The ref is read from the drafted subject, exactly as a person would see it.
    return world["drafts"][-1]["subject"].rsplit("(ref ", 1)[1].rstrip(")")


def order(ref):
    with ledger.connect() as conn:
        return ledger.get_order(conn, ref)


def mark_all_sent(ref):
    with ledger.connect() as conn:
        for e in ledger.get_order(conn, ref)["emails"]:
            ledger.mark_sent(conn, e["message_id"], datetime.now(timezone.utc).isoformat())


# ---- Wrong order never sent ----------------------------------------------- #


def test_delivery_takes_only_the_order_ref_and_uses_the_recorded_buyer_and_scope(world):
    ref = quote_brief(world, "a@example.com")
    pay(world, "a@example.com", 74500)

    assert run(world, "deliver", "--order-ref", ref) == 0

    assert world["built"][-1] == ("brief", ref, "a@example.com", "North East", "not_yet_inspected")
    assert world["drafts"][-1]["to"] == "a@example.com"
    assert f"(ref {ref})" in world["drafts"][-1]["subject"]
    assert world["drafts"][-1]["files"] == ["brief.pdf"]


@pytest.mark.parametrize("typed", [["--region", "London"], ["--buyer-email", "b@example.com"], ["--provider-group", "inadequate"]])
def test_delivery_refuses_any_retyped_detail(world, typed):
    ref = quote_brief(world)
    with pytest.raises(SystemExit):
        run(world, "deliver", "--order-ref", ref, *typed)


def test_unknown_ref_is_refused_and_nothing_is_built(world, capsys):
    assert run(world, "deliver", "--order-ref", "TOB-NOPE") == 2
    assert "there is no order" in capsys.readouterr().out
    assert world["built"] == [] and world["drafts"] == []


def test_quote_refuses_a_malformed_email(world):
    with pytest.raises(SystemExit):
        run(world, "quote", "brief", "--region", "North East", "--provider-group", "new_90", "--buyer-email", "not an email")


# ---- Nothing delivered unpaid; one payment, one order ---------------------- #


def test_unpaid_delivery_is_refused(world, capsys):
    ref = quote_brief(world)
    assert run(world, "deliver", "--order-ref", ref) == 2
    assert "payment_received" in capsys.readouterr().out
    assert [b for b in world["built"] if b[0] == "brief" and len(world["built"]) > 1] == []
    assert len(world["drafts"]) == 1  # the quote only


def test_one_payment_cannot_pay_for_two_orders(world, capsys):
    first = quote_brief(world, "a@example.com")
    second = quote_brief(world, "a@example.com", "--new-order")
    pay(world, "a@example.com", 74500, session="cs_only")

    assert run(world, "deliver", "--order-ref", first) == 0
    assert run(world, "deliver", "--order-ref", second) == 2
    assert "no unclaimed paid £745" in capsys.readouterr().out
    assert order(first)["payment_session"] == "cs_only" and order(second)["paid_at"] is None


def test_a_payment_made_before_the_order_existed_is_not_used(world):
    pay(world, "a@example.com", 74500, when=datetime.now(timezone.utc) - timedelta(days=30))
    ref = quote_brief(world, "a@example.com")
    assert run(world, "deliver", "--order-ref", ref) == 2


def test_the_wrong_amount_does_not_count(world):
    ref = quote_brief(world, "a@example.com")
    pay(world, "a@example.com", 15000)
    assert run(world, "deliver", "--order-ref", ref) == 2


# ---- No duplicates ---------------------------------------------------------- #


def test_second_delivery_draft_is_refused_then_redraft_replaces_it(world, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", ref) == 0

    assert run(world, "deliver", "--order-ref", ref) == 2
    assert "already exists" in capsys.readouterr().out

    assert run(world, "deliver", "--order-ref", ref, "--redraft") == 0
    live = ledger.live(order(ref)["emails"], "deliver")
    assert len(live) == 1  # the old draft is superseded, not counted


def test_delivery_after_it_was_sent_is_refused_even_with_redraft(world, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", ref) == 0
    mark_all_sent(ref)

    assert run(world, "deliver", "--order-ref", ref, "--redraft") == 2
    assert "already fully delivered" in capsys.readouterr().out


def test_second_open_order_for_the_same_buyer_needs_a_deliberate_choice(world, capsys):
    ref = quote_brief(world, "a@example.com")
    assert run(world, "quote", "brief", "--region", "North East", "--provider-group", "new_90",
               "--buyer-email", "A@Example.com") == 2
    assert ref in capsys.readouterr().out

    # Changing that order is explicit; an unsent quote draft must be replaced deliberately.
    assert run(world, "quote", "brief", "--region", "North East", "--provider-group", "new_90",
               "--buyer-email", "a@example.com", "--order-ref", ref) == 2
    assert run(world, "quote", "brief", "--region", "North East", "--provider-group", "new_90",
               "--buyer-email", "a@example.com", "--order-ref", ref, "--redraft") == 0
    assert len(ledger.live(order(ref)["emails"], "quote")) == 1


def test_paid_order_scope_cannot_be_changed(world, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", ref) == 0
    assert run(world, "quote", "brief", "--region", "London", "--provider-group", "new_90",
               "--buyer-email", "a@example.com", "--order-ref", ref, "--redraft") == 2
    assert "already paid" in capsys.readouterr().out


def test_failed_mailbox_save_leaves_no_phantom_draft(world, monkeypatch, capsys):
    def broken(message, *, env):
        raise OSError("mailbox down")

    monkeypatch.setattr(po, "save_draft", broken)
    assert run(world, "quote", "brief", "--region", "North East", "--provider-group", "new_90",
               "--buyer-email", "z@example.com") == 2
    assert "could not save the draft" in capsys.readouterr().out
    with ledger.connect() as conn:
        (o,) = ledger.orders_with_emails(conn)
    assert ledger.live(o["emails"], "quote") == []


# ---- Weekly Digest: right issue, on time, exactly four ---------------------- #


def test_digest_issues_are_numbered_and_dated_from_the_order(world, capsys):
    start = TODAY - timedelta(days=8)
    assert run(world, "quote", "digest", "--region", "North West", "--start-date", start.isoformat(),
               "--buyer-email", "d@example.com") == 0
    ref = world["drafts"][-1]["subject"].rsplit("(ref ", 1)[1].rstrip(")")
    pay(world, "d@example.com", 15000)

    assert run(world, "deliver", "--order-ref", ref) == 0
    assert world["built"][-1] == ("digest", ref, 1, (start - timedelta(days=1)).isoformat())
    mark_all_sent(ref)
    assert run(world, "deliver", "--order-ref", ref) == 0
    assert world["built"][-1][2] == 2
    mark_all_sent(ref)

    assert run(world, "deliver", "--order-ref", ref) == 2  # issue 3 is not due yet
    assert "not due until" in capsys.readouterr().out
    assert ledger.order_status(order(ref)).startswith("Paid: issue 3 of 4 due")


# ---- Nothing missed: actions, unmatched payments, overdue -------------------- #


def test_actions_list_every_open_step_and_payments_with_no_order(world, monkeypatch):
    drafted = quote_brief(world, "a@example.com")
    paid = quote_brief(world, "b@example.com")
    pay(world, "b@example.com", 74500)
    pay(world, "stranger@example.com", 15000, session="cs_orphan")
    monkeypatch.setattr(orders, "find_sent", lambda env, pending: {})

    notes, unmatched = orders.refresh({})
    todo = orders.actions(orders.rows(), unmatched)

    text = "\n".join(todo)
    assert f"{drafted}" in text and "Send the quote draft" in text
    assert f"{paid}" in text and f"prepare_order deliver --order-ref {paid}" in text
    assert "PAYMENT WITH NO ORDER" in text and "cs_orphan" in text


def test_paid_brief_becomes_overdue_after_three_working_days(world):
    ref = quote_brief(world)
    with ledger.connect() as conn:
        ledger.record_payment(conn, ref, {"paid_at": "2026-10-16T10:00:00+00:00", "session": "cs_x", "source": "Stripe"})
    action = ledger.next_action(order(ref), date(2026, 10, 22))
    assert action["due"] == date(2026, 10, 21) and action["overdue"]


# ---- Count and report ------------------------------------------------------- #


def test_totals_and_report_show_bought_not_bought_and_delivered(world, tmp_path, monkeypatch):
    delivered = quote_brief(world, "a@example.com")
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", delivered) == 0
    mark_all_sent(delivered)
    not_bought = quote_brief(world, "b@example.com")
    monkeypatch.setattr(orders, "find_sent", lambda env, pending: {})
    orders.refresh({})

    table = orders.rows()
    t = orders.totals(table)
    md, csv_path = orders.write_report(table, orders.actions(table, []), [], out_dir=tmp_path / "reports")

    assert t == {"orders": 2, "quoted_not_paid": 1, "paid": 1, "complete": 1,
                 "paid_awaiting_delivery": 0, "revenue_gbp": 745, "overdue": 0}
    report = md.read_text()
    assert "## Bought (1)" in report and "## Not bought yet (1)" in report and "## Delivered in full (1)" in report
    assert delivered in report and not_bought in report
    assert csv_path.read_text().splitlines()[0].startswith("Ref,Product,Buyer")


def test_ledger_rejects_attaching_one_payment_to_two_orders_directly(world):
    a = quote_brief(world, "a@example.com")
    b = quote_brief(world, "b@example.com")
    with ledger.connect() as conn:
        ledger.record_payment(conn, a, {"paid_at": "2026-10-20", "session": "cs_dup", "source": "Stripe"})
        with pytest.raises(ledger.LedgerError):
            ledger.record_payment(conn, b, {"paid_at": "2026-10-20", "session": "cs_dup", "source": "Stripe"})


def test_order_folder_and_eml_exist_for_every_draft(world):
    ref = quote_brief(world)
    emls = list(Path(world["out"]).rglob("email.eml"))
    assert len(emls) == 1 and ref in str(emls[0])
