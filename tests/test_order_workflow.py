"""End-to-end rules of the human-led order workflow (prepare_order + ledger + orders).

Each test names the guarantee it protects:
  wrong order never sent, no duplicates, nothing missed, sent count, report.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests import package_fixtures
from tools import order_ledger as ledger
from tools import orders
from tools import prepare_order as po

TODAY = datetime.now(timezone.utc).date()


@pytest.fixture(autouse=True)
def world(monkeypatch, tmp_path):
    """Isolated ledger, fake mailbox, fake payments and fake pack builders."""
    monkeypatch.setenv("CAREGIST_ORDER_LEDGER", str(tmp_path / "ledger.sqlite"))
    state = {"payments": [], "drafts": [], "built": [], "invalid": {}}

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
        pdf.write_bytes(package_fixtures.brief_pdf(args.order_ref, package_fixtures.roster(30), geography=args.region))
        csv_path = order_dir / "brief.csv"
        csv_path.write_text(
            "cqc_provider_id,cqc_location_id,organisation_name\n"
            + "".join(f"P{i},L{i},Provider {i}\n" for i in range(30)),
            encoding="utf-8",
        )
        manifest = order_dir / "brief-manifest.json"
        manifest.write_text('{"generated_at":"2026-10-16"}', encoding="utf-8")
        summary = {"region": args.region, "provider_group": "Not yet inspected", "service_type": "All",
                   "locations_in_scope": 1221, "shortlisted": 30, "source_edition": "2026-10-16", "export": "x"}
        return checks, summary, [pdf, csv_path, manifest]

    def build_digest_issue(args, *, env, order_dir, now):
        state["built"].append(("digest", args.order_ref, args.issue, args.week_ending))
        checks = po.Checks()
        checks.add("digest_built", True, "ok")
        pdf = order_dir / f"issue{args.issue}.pdf"

        csv_path = order_dir / f"issue{args.issue}.csv"
        csv_path.write_text(
            "section,date,location_id,name,local_authority,detail,cqc_url\n",
            encoding="utf-8",
        )
        manifest = order_dir / f"issue{args.issue}.json"
        from api.services.customer_package import digest_binding, customer_email_reference
        import json
        binding = digest_binding(order_reference=args.order_ref,
            customer_reference=customer_email_reference(args.buyer_email), region=args.region,
            issue=args.issue, week_ending=args.week_ending, csv_bytes=csv_path.read_bytes())
        pdf.write_bytes(package_fixtures.digest_pdf(binding))
        manifest.write_text(json.dumps({"generated_at": "2026-10-16", "binding": binding}), encoding="utf-8")
        return checks, {"new_registrations": 4, "ratings_published": 0}, [pdf, csv_path, manifest]

    monkeypatch.setattr(po, "list_payments", list_payments)
    monkeypatch.setattr(po, "payment_still_valid", lambda env, session: state["invalid"].get(session))
    monkeypatch.setattr(po, "save_draft", save_draft)
    monkeypatch.setattr(po, "build_brief", build_brief)
    monkeypatch.setattr(po, "build_digest_issue", build_digest_issue)
    monkeypatch.setattr(po, "load_env", lambda: {"OUTREACH_IMAP_PASSWORD": "test-only"})
    # By default an earlier draft is gone from Drafts and unsent, so --redraft may replace it.
    monkeypatch.setattr(po, "draft_exists", lambda message_id, *, env: False)
    monkeypatch.setattr(orders, "find_sent", lambda env, pending, **kwargs: {})
    state["out"] = tmp_path / "orders"
    return state


def run(world, *argv):
    return po.main([*argv, "--out-base", str(world["out"])])


def pay(world, email, amount, *, when=None, session=None, order_ref=None):
    world["payments"].append({
        "email": email, "amount": amount, "source": "Stripe",
        "session": session or f"cs_{len(world['payments']) + 1}",
        "paid_at": (when or datetime.now(timezone.utc)).isoformat(),
        "order_ref": order_ref,
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
    assert set(world["drafts"][-1]["files"]) == {
        "brief.pdf",
        "brief.csv",
        "brief-manifest.json",
        next(path.name for path in (world["out"] / "packages" / ref).rglob("*.zip")),
    }


def test_manual_package_binds_a_hashed_buyer_not_the_plain_email(world):
    import json
    import zipfile

    ref = quote_brief(world, "a@example.com")
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", ref) == 0

    package = next((world["out"] / "packages" / ref).rglob("*.zip"))
    with zipfile.ZipFile(package) as archive:
        texts = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(texts["manifest.json"])
    assert manifest["customer_reference"].startswith("email-sha256:")
    # PDF streams are compressed, so read their text rather than the raw bytes.
    readable = {
        name: (_pdf_text(data) if name.endswith(".pdf") else data.decode("utf-8", "replace"))
        for name, data in texts.items()
    }
    assert "Prepared for: email-sha256:" in readable["selection-confirmation.pdf"]
    assert not any("a@example.com" in text for text in readable.values())


def _pdf_text(data: bytes) -> str:
    import io

    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


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
    assert f"no paid £745 sale found for {second}" in capsys.readouterr().out
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
    monkeypatch.setattr(po, "draft_exists", lambda message_id, *, env: False)
    assert run(world, "quote", "brief", "--region", "North East", "--provider-group", "new_90",
               "--buyer-email", "z@example.com") == 2
    assert "could not save the draft" in capsys.readouterr().out
    with ledger.connect() as conn:
        (o,) = ledger.orders_with_emails(conn)
    assert ledger.live(o["emails"], "quote") == []


def test_draft_saved_despite_lost_reply_is_kept_and_tracked(world, monkeypatch, capsys):
    def lost_reply(message, *, env):
        raise OSError("connection reset after APPEND")

    monkeypatch.setattr(po, "save_draft", lost_reply)
    monkeypatch.setattr(po, "draft_exists", lambda message_id, *, env: True)
    assert run(world, "quote", "brief", "--region", "North East", "--provider-group", "new_90",
               "--buyer-email", "z@example.com") == 0
    with ledger.connect() as conn:
        (o,) = ledger.orders_with_emails(conn)
    (live,) = ledger.live(o["emails"], "quote")
    assert "confirmed after a connection error" in live["draft_location"]


def test_uncertain_draft_blocks_a_plain_rerun(world, monkeypatch, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)

    def lost_reply(message, *, env):
        raise OSError("connection reset after APPEND")

    def cannot_tell(message_id, *, env):
        raise OSError("mailbox unreachable")

    monkeypatch.setattr(po, "save_draft", lost_reply)
    monkeypatch.setattr(po, "draft_exists", cannot_tell)
    assert run(world, "deliver", "--order-ref", ref) == 2
    assert "may or may not be in outreach@ Drafts" in capsys.readouterr().out
    # The possibly-saved draft stays tracked, so a plain re-run cannot add a second one.
    assert len(ledger.live(order(ref)["emails"], "deliver")) == 1
    assert run(world, "deliver", "--order-ref", ref) == 2
    assert "already exists" in capsys.readouterr().out


def test_redraft_refused_while_the_earlier_draft_is_still_in_drafts(world, monkeypatch, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", ref) == 0
    monkeypatch.setattr(po, "draft_exists", lambda message_id, *, env: True)
    assert run(world, "deliver", "--order-ref", ref, "--redraft") == 2
    assert "still in outreach@ Drafts" in capsys.readouterr().out
    assert len(ledger.live(order(ref)["emails"], "deliver")) == 1


def test_redraft_refused_when_the_earlier_draft_was_sent(world, monkeypatch, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", ref) == 0
    monkeypatch.setattr(orders, "find_sent", lambda env, pending, **kwargs: {pending[0]["message_id"]: "2026-10-20T12:00:00"})
    assert run(world, "deliver", "--order-ref", ref, "--redraft") == 2
    assert "has been sent" in capsys.readouterr().out


def test_redraft_refused_when_drafts_cannot_be_checked(world, monkeypatch, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", ref) == 0

    def down(message_id, *, env):
        raise OSError("mailbox unreachable")

    monkeypatch.setattr(po, "draft_exists", down)
    assert run(world, "deliver", "--order-ref", ref, "--redraft") == 2
    assert "could not confirm the earlier draft is gone" in capsys.readouterr().out


def test_uncertain_draft_is_shown_as_needing_a_check(world, monkeypatch):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    monkeypatch.setattr(po, "save_draft", lambda message, *, env: (_ for _ in ()).throw(OSError("reset")))
    monkeypatch.setattr(po, "draft_exists", lambda message_id, *, env: (_ for _ in ()).throw(OSError("down")))
    assert run(world, "deliver", "--order-ref", ref) == 2
    action = ledger.next_action(order(ref), TODAY)
    assert action["status"] == "Deliver draft not confirmed in outreach@"
    assert "--redraft" in action["next"]


def test_dry_run_records_no_order(world, capsys):
    assert run(world, "quote", "brief", "--region", "North East", "--provider-group", "new_90",
               "--buyer-email", "dry@example.com", "--no-draft") == 0
    assert "DRY RUN" in capsys.readouterr().out
    with ledger.connect() as conn:
        assert ledger.orders_with_emails(conn) == []


def test_payment_that_cannot_be_rechecked_is_a_problem(world, monkeypatch):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500, order_ref=ref)

    def stripe_down(env, session):
        raise OSError("stripe unreachable")

    monkeypatch.setattr(po, "payment_still_valid", stripe_down)
    orders.refresh({})
    assert "could not be re-checked" in order(ref)["payment_problem"]
    assert orders.totals(orders.rows())["revenue_gbp"] == 0


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
    monkeypatch.setattr(orders, "find_sent", lambda env, pending, **kwargs: {})

    notes, unmatched = orders.refresh({})
    todo = orders.actions(orders.rows(), unmatched)

    text = "\n".join(todo)
    assert f"{drafted}" in text and "Send the quote draft" in text
    assert f"{paid}" in text and f"prepare_order deliver --order-ref {paid}" in text
    assert "PAYMENT WITH NO ORDER" in text and "cs_orphan" in text


def test_refund_found_on_first_refresh_is_not_counted_as_revenue(world, monkeypatch):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500, session="cs_refunded", order_ref=ref)
    world["invalid"]["cs_refunded"] = "the payment has been refunded"
    monkeypatch.setattr(orders, "find_sent", lambda env, pending, **kwargs: {})

    orders.refresh({})

    assert order(ref)["payment_problem"] == "the payment has been refunded"
    t = orders.totals(orders.rows())
    assert t["revenue_gbp"] == 0 and t["payment_problems"] == 1


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
    monkeypatch.setattr(orders, "find_sent", lambda env, pending, **kwargs: {})
    orders.refresh({})

    table = orders.rows()
    t = orders.totals(table)
    md, csv_path = orders.write_report(table, orders.actions(table, []), [], out_dir=tmp_path / "reports")

    assert t == {"orders": 2, "quoted_not_paid": 1, "paid": 1, "complete": 1,
                 "paid_awaiting_delivery": 0, "revenue_gbp": 745, "overdue": 0, "payment_problems": 0}
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



# ---- Second independent review ---------------------------------------------- #


def test_quote_link_carries_the_order_ref(world):
    ref = quote_brief(world)
    with ledger.connect() as conn:
        folder = ledger.get_order(conn, ref)["emails"][0]["folder"]
    import email
    import email.policy

    message = email.message_from_bytes((Path(folder) / "email.eml").read_bytes(), policy=email.policy.default)
    assert f"{po.BRIEF_PAYMENT_LINK}?client_reference_id={ref}" in message.get_body(("plain",)).get_content()


def test_payment_bound_to_an_order_ref_goes_to_that_order_even_with_another_email(world):
    first = quote_brief(world, "a@example.com")
    second = quote_brief(world, "a@example.com", "--new-order")
    # The buyer pays for the SECOND order first, from a different email address.
    pay(world, "accounts@a-ltd.example", 74500, session="cs_for_second", order_ref=second)

    assert run(world, "deliver", "--order-ref", first) == 2   # not taken by the first order
    assert run(world, "deliver", "--order-ref", second) == 0
    assert order(second)["payment_session"] == "cs_for_second"


def test_a_payment_bound_to_another_ref_is_never_used(world):
    ref = quote_brief(world, "a@example.com")
    pay(world, "a@example.com", 74500, order_ref="TOB-SOMEONE-ELSE")
    assert run(world, "deliver", "--order-ref", ref) == 2


def test_refunded_payment_blocks_delivery(world, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500, session="cs_refunded", order_ref=ref)
    world["invalid"]["cs_refunded"] = "the payment has been refunded"

    assert run(world, "deliver", "--order-ref", ref) == 2
    assert "refunded" in capsys.readouterr().out


def test_unreachable_payment_check_refuses_delivery(world, monkeypatch, capsys):
    ref = quote_brief(world)

    def down(*a, **k):
        raise OSError("stripe unreachable")

    monkeypatch.setattr(po, "list_payments", down)
    assert run(world, "deliver", "--order-ref", ref) == 2
    assert "could not be checked" in capsys.readouterr().out


def test_ledger_refuses_scope_change_of_a_paid_order_inside_the_transaction(world):
    ref = quote_brief(world)
    with ledger.connect() as conn:
        ledger.record_payment(conn, ref, {"paid_at": "2026-10-20", "session": "cs_p", "source": "Stripe"})
    with pytest.raises(ledger.LedgerError):
        ledger.record_email(
            order_ref=ref, product="brief", stage="quote", buyer_email="a@example.com", buyer_name="", company="",
            scope="London", scope_args={"region": "London"}, amount_pence=74500, quoted_count=10,
            message_id="<late>", subject="S (ref x)", draft_location="saved", folder="/tmp",
        )
    assert order(ref)["scope_args"]["region"] == "North East"


def test_requote_is_refused_when_stripe_shows_it_paid_but_ledger_does_not_yet(world, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500, order_ref=ref)
    assert run(world, "quote", "brief", "--region", "London", "--provider-group", "new_90",
               "--buyer-email", "a@example.com", "--order-ref", ref, "--redraft") == 2
    assert "has been paid" in capsys.readouterr().out


def test_ledger_allows_only_one_unsent_draft_per_step(world):
    ref = quote_brief(world)
    with pytest.raises(ledger.LedgerError):
        ledger.record_email(
            order_ref=ref, product="brief", stage="quote", buyer_email="a@example.com", buyer_name="", company="",
            scope="North East", scope_args={"region": "North East"}, amount_pence=74500, quoted_count=30,
            message_id="<concurrent>", subject="S (ref x)", draft_location="saved", folder="/tmp",
        )


def test_drafted_unsent_delivery_keeps_its_due_date_and_overdue_flag(world):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500, order_ref=ref)
    assert run(world, "deliver", "--order-ref", ref) == 0
    with ledger.connect() as conn:
        conn.execute("UPDATE orders SET paid_at = '2026-10-01T10:00:00+00:00' WHERE order_ref = ?", (ref,))
    action = ledger.next_action(order(ref), date(2026, 10, 20))
    assert action["status"] == "Delivery drafted: press Send"
    assert action["due"] == date(2026, 10, 6) and action["overdue"]


def test_one_failed_payment_lookup_does_not_stop_rechecks_of_other_orders(world, monkeypatch):
    unpaid = quote_brief(world, "a@example.com")
    paid = quote_brief(world, "b@example.com")
    pay(world, "b@example.com", 74500, session="cs_b", order_ref=paid)
    with ledger.connect() as conn:
        ledger.record_payment(conn, paid, world["payments"][0])
    world["invalid"]["cs_b"] = "the payment has been refunded"
    real_find = po.find_payment

    def flaky(env, email, amount, **kw):
        if kw.get("order_ref") == unpaid:
            raise OSError("stripe timeout")
        return real_find(env, email, amount, **kw)

    monkeypatch.setattr(po, "find_payment", flaky)
    notes, _ = orders.refresh({})
    assert any(unpaid in n for n in notes)
    assert order(paid)["payment_problem"] == "the payment has been refunded"


def test_draft_left_pending_by_a_crash_is_not_shown_as_press_send(world):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    assert run(world, "deliver", "--order-ref", ref) == 0
    with ledger.connect() as conn:
        conn.execute("UPDATE order_emails SET draft_location = 'pending' WHERE stage = 'deliver'")
    action = ledger.next_action(order(ref), TODAY)
    assert action["status"] == "Deliver draft not confirmed in outreach@"


def _lost_reply(message, *, env):
    raise OSError("connection reset after APPEND")


def test_lost_reply_draft_already_sent_is_recorded_not_freed(world, monkeypatch, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)
    monkeypatch.setattr(po, "save_draft", _lost_reply)
    monkeypatch.setattr(po, "draft_exists", lambda message_id, *, env: False)
    monkeypatch.setattr(orders, "find_sent",
                        lambda env, pending, strict=False: {pending[0]["message_id"]: "2026-10-20T12:00:00+00:00"})
    assert run(world, "deliver", "--order-ref", ref) == 0
    assert "ALREADY SENT" in capsys.readouterr().out
    (delivery,) = ledger.live(order(ref)["emails"], "deliver")
    assert delivery["sent_at"]
    assert run(world, "deliver", "--order-ref", ref, "--redraft") == 2


def test_lost_reply_with_sent_folder_unreadable_stays_tracked(world, monkeypatch, capsys):
    ref = quote_brief(world)
    pay(world, "a@example.com", 74500)

    def sent_unreadable(env, pending, strict=False):
        raise RuntimeError("Sent folder could not be checked")

    monkeypatch.setattr(po, "save_draft", _lost_reply)
    monkeypatch.setattr(po, "draft_exists", lambda message_id, *, env: False)
    monkeypatch.setattr(orders, "find_sent", sent_unreadable)
    assert run(world, "deliver", "--order-ref", ref) == 2
    assert "NOT CONFIRMED" in capsys.readouterr().out
    assert len(ledger.live(order(ref)["emails"], "deliver")) == 1


def test_sent_quote_scope_cannot_be_changed(world, capsys):
    ref = quote_brief(world)
    mark_all_sent(ref)
    assert run(world, "quote", "brief", "--region", "London", "--provider-group", "new_90",
               "--buyer-email", "a@example.com", "--order-ref", ref, "--redraft") == 2
    assert "has been sent" in capsys.readouterr().out
    assert order(ref)["scope"].startswith("North East")
    # A different scope is a separate order with its own ref and payment link.
    assert run(world, "quote", "brief", "--region", "London", "--provider-group", "new_90",
               "--buyer-email", "a@example.com", "--new-order") == 0


def test_delivery_builds_exactly_the_quoted_number(world, monkeypatch):
    ref = quote_brief(world, "a@example.com", "--shortlist", "50")
    with ledger.connect() as conn:
        conn.execute("UPDATE orders SET quoted_count = 50 WHERE order_ref = ?", (ref,))
    pay(world, "a@example.com", 74500)
    seen = {}
    real_build = po.build_brief

    def capture(args, **kw):
        seen["shortlist"] = args.shortlist
        return real_build(args, **kw)

    monkeypatch.setattr(po, "build_brief", capture)
    run(world, "deliver", "--order-ref", ref)
    assert seen["shortlist"] == 50


def test_a_second_concurrent_run_is_refused(world, capsys):
    import fcntl

    lock_path = ledger.ledger_path().with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        assert run(world, "quote", "brief", "--region", "North East", "--provider-group", "new_90",
                   "--buyer-email", "c@example.com") == 2
        fcntl.flock(held, fcntl.LOCK_UN)
    assert "another prepare_order run is in progress" in capsys.readouterr().out
    with ledger.connect() as conn:
        assert ledger.orders_with_emails(conn) == []
