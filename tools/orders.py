"""Every order, what to do next, and a report: one screen for the whole business.

  .venv/bin/python -m tools.orders                 # refresh, then show totals, actions and the table
  .venv/bin/python -m tools.orders --no-refresh    # what is recorded, offline
  .venv/bin/python -m tools.orders --report        # also write orders/reports/orders-report-<date>.md and .csv

Refresh is read-only. Payments come from CareGist's sales record or Stripe and
are attached to the oldest unpaid order of the same buyer and amount that
existed before the payment; a payment can belong to one order only. A paid sale
that matches no order is listed under ACTION NEEDED. "Sent" is read from the
outreach@ Sent folder by the order reference in the subject and the buyer.
"""

from __future__ import annotations

import argparse
import csv
import imaplib
import ssl
from datetime import date, datetime, timezone
from email import message_from_bytes
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from tools import order_ledger as ledger
from tools import prepare_order as po

REPORT_DIR = ledger.REPO_ROOT / "orders" / "reports"


# --------------------------------------------------------------------------- #
# Refresh (read-only against Stripe, the database and the mailbox)
# --------------------------------------------------------------------------- #


def _sent_mailbox(conn: imaplib.IMAP4_SSL) -> str:
    status, folders = conn.list()
    if status == "OK":
        for raw in folders or []:
            line = raw.decode("utf-8", "replace")
            if "\\Sent" in line:
                return line.rsplit(' "', 1)[-1].strip('"') if ' "' in line else line.split()[-1]
    return "Sent"


def find_sent(env: dict[str, str], pending: list[dict[str, Any]], *, strict: bool = False) -> dict[str, str]:
    """message_id -> sent time, for drafted emails now found in the Sent folder.

    strict=True is for decisions that must prove an email was *not* sent: any
    search or fetch the server does not answer cleanly raises instead of being
    read as "not sent".
    """

    def unsure(why: str) -> None:
        if strict:
            raise RuntimeError(f"Sent folder could not be checked: {why}")

    password = env.get("OUTREACH_IMAP_PASSWORD") or ""
    if not password:
        unsure("OUTREACH_IMAP_PASSWORD is not set")
        return {}
    if not pending:
        return {}
    conn = imaplib.IMAP4_SSL(
        env.get("OUTREACH_IMAP_HOST") or "mail.privateemail.com", 993, ssl_context=ssl.create_default_context()
    )
    found: dict[str, str] = {}
    try:
        conn.login(env.get("OUTREACH_IMAP_USER") or po.FROM_ADDRESS, password)
        status, _ = conn.select(_sent_mailbox(conn), readonly=True)
        if status != "OK":
            unsure("could not open the Sent folder")
            return {}
        for email_row in pending:
            ref = email_row["order_ref"]
            drafted = datetime.fromisoformat(email_row["drafted_at"])
            # 1. Exact: the drafted message's own Message-ID, when the mailbox keeps it on Send.
            status, data = conn.search(None, "HEADER", "Message-ID", f'"{email_row["message_id"]}"')
            if status != "OK":
                unsure("Message-ID search failed")
                continue
            if data and data[0]:
                status, header = conn.fetch(data[0].split()[0], "(BODY.PEEK[HEADER.FIELDS (DATE)])")
                when = None
                if status == "OK" and header and isinstance(header[0], tuple):
                    try:
                        when = parsedate_to_datetime(message_from_bytes(header[0][1]).get("Date", "")).astimezone(timezone.utc)
                    except (TypeError, ValueError, LookupError, UnicodeError):
                        when = None
                found[email_row["message_id"]] = (when or datetime.now(timezone.utc)).isoformat(timespec="seconds")
                continue
            # 2. Otherwise the whole subject, same recipient, sent after this draft existed.
            status, data = conn.search(None, "SUBJECT", f'"{ref}"', "TO", f'"{email_row["buyer_email"]}"')
            if status != "OK":
                unsure("subject search failed")
                continue
            if not data or not data[0]:
                continue
            for number in data[0].split():
                status, header = conn.fetch(number, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE)])")
                if status != "OK" or not header or not isinstance(header[0], tuple):
                    unsure("header fetch failed")
                    continue
                try:
                    parsed = message_from_bytes(header[0][1])
                    sent_subject = " ".join(str(make_header(decode_header(parsed.get("Subject", "")))).split())
                except (LookupError, UnicodeError, ValueError):
                    unsure("unreadable candidate header")
                    continue  # unreadable header: never mark anything sent from it
                # The whole subject must match: ref, step and Digest issue number. Prefixes
                # such as "Re:" or a shared opening would otherwise mark the wrong email sent.
                if sent_subject == " ".join(email_row["subject"].split()):
                    date_line = "Date: " + parsed.get("Date", "")
                    try:
                        sent_dt = parsedate_to_datetime(date_line[5:].strip()).astimezone(timezone.utc)
                    except (TypeError, ValueError):
                        unsure("matching subject has no usable date")
                        continue  # undated: cannot prove it was sent after this draft
                    # Anything sent before this draft existed (e.g. an earlier, replaced draft
                    # with the same subject) does not count. No tolerance: a late clock can
                    # only leave an email showing "press Send", never mark one sent wrongly.
                    if sent_dt < drafted:
                        unsure("matching subject predates the ledger draft; it may retain its original Date")
                        continue
                    found[email_row["message_id"]] = sent_dt.isoformat(timespec="seconds")
                    break
    finally:
        try:
            conn.logout()
        except Exception:
            pass
    return found


def _payment_problem(env: dict[str, str], session: str) -> str | None:
    """Why this payment cannot be relied on, or None. Fails closed: an unchecked payment is a problem."""
    try:
        return po.payment_still_valid(env, session)
    except Exception as exc:
        return f"payment could not be re-checked ({type(exc).__name__}); refresh again before sending anything"


def refresh(env: dict[str, str], *, path: Path | None = None) -> tuple[list[str], list[dict[str, Any]]]:
    """Update paid and sent status. Returns (notes, payments that match no order)."""
    notes: list[str] = []
    unmatched: list[dict[str, Any]] = []
    with ledger.connect(path) as conn:
        orders = ledger.orders_with_emails(conn)
        claimed = ledger.claimed_sessions(conn)
        try:
            for order in sorted(orders, key=lambda o: o["created_at"]):
                if order["paid_at"]:
                    if order["payment_session"]:
                        ledger.set_payment_problem(conn, order["order_ref"], _payment_problem(env, order["payment_session"]))
                    continue
                try:
                    payment = po.find_payment(
                        env, order["buyer_email"], order["amount_pence"], order_ref=order["order_ref"],
                        exclude_sessions=claimed, not_before=order["created_at"],
                    )
                except Exception as exc:  # this order only: every other order is still checked
                    notes.append(f"{order['order_ref']}: payment lookup failed ({type(exc).__name__}); refresh again.")
                    continue
                if payment:
                    ledger.record_payment(conn, order["order_ref"], payment)
                    claimed.add(payment["session"])
                    # Validate now, not on the next refresh: a refunded or disputed
                    # checkout still reports payment_status "paid".
                    ledger.set_payment_problem(conn, order["order_ref"], _payment_problem(env, payment["session"]))
            unmatched = [p for p in po.list_payments(env) if p["session"] not in claimed]
        except Exception as exc:  # network or DB unavailable: keep the last known state
            notes.append(f"Payment check unavailable ({type(exc).__name__}); showing last known state.")

        orders = ledger.orders_with_emails(conn)
        pending = [
            {**email_row, "buyer_email": order["buyer_email"]}
            for order in orders
            for email_row in order["emails"]
            if not email_row["sent_at"] and not email_row["superseded_at"]
        ]
        if pending and not env.get("OUTREACH_IMAP_PASSWORD"):
            notes.append("Sent status not refreshed: add OUTREACH_IMAP_PASSWORD to .env.")
        else:
            try:
                for message_id, sent_at in find_sent(env, pending).items():
                    ledger.mark_sent(conn, message_id, sent_at)
            except (imaplib.IMAP4.error, OSError) as exc:
                notes.append(f"Sent folder unavailable ({type(exc).__name__}); showing last known state.")
    return notes, unmatched


# --------------------------------------------------------------------------- #
# Views
# --------------------------------------------------------------------------- #


def rows(today: date | None = None, *, path: Path | None = None) -> list[dict[str, str]]:
    today = today or datetime.now(timezone.utc).date()
    with ledger.connect(path) as conn:
        orders = ledger.orders_with_emails(conn)
    table = []
    for order in orders:
        quotes = ledger.live(order["emails"], "quote")
        deliveries = ledger.live(order["emails"], "deliver")
        expected = ledger.DIGEST_ISSUES if order["product"] == "digest" else 1
        action = ledger.next_action(order, today)
        due = action["due"].isoformat() if action["due"] else "-"
        table.append({
            "Ref": order["order_ref"],
            "Product": "Brief £745" if order["product"] == "brief" else "Digest £150",
            "Buyer": order["buyer_email"] + (f" ({order['company']})" if order["company"] else ""),
            "Scope": order["scope"] + (f" · {order['quoted_count']} orgs" if order["quoted_count"] else ""),
            "Quote": ("sent " + max(e["sent_at"] for e in quotes if e["sent_at"])[:10]) if any(e["sent_at"] for e in quotes)
                     else ("drafted " + quotes[-1]["drafted_at"][:10] if quotes else "-"),
            "Paid": (order["paid_at"] or "")[:10] or "-",
            "Delivered": f"{len(ledger.sent_issues(order))}/{expected} sent" if deliveries or order["paid_at"] else "-",
            "Due": due + (" OVERDUE" if action["overdue"] else ""),
            "Status": action["status"],
            "Next step": action["next"],
        })
    return table


def totals(table: list[dict[str, str]]) -> dict[str, Any]:
    problems = [r for r in table if "payment problem" in r["Status"].lower()]
    paid = [r for r in table if r["Paid"] != "-" and r not in problems]
    revenue = sum(745 if r["Product"].startswith("Brief") else 150 for r in paid)
    return {
        "orders": len(table),
        "quoted_not_paid": sum(1 for r in table if r["Paid"] == "-"),
        "paid": len(paid),
        "complete": sum(1 for r in table if r["Status"] == "Complete"),
        "paid_awaiting_delivery": sum(1 for r in paid if r["Status"] != "Complete"),
        "revenue_gbp": revenue,
        "overdue": sum(1 for r in table if "OVERDUE" in r["Due"]),
        "payment_problems": len(problems),
    }


def actions(table: list[dict[str, str]], unmatched: list[dict[str, Any]]) -> list[str]:
    items = []
    for row in table:
        if row["Status"] == "Complete" or row["Next step"] in ("-", "Wait for payment") or row["Next step"].startswith("Wait until"):
            continue
        flag = "OVERDUE " if "OVERDUE" in row["Due"] else ""
        items.append(f"{flag}{row['Ref']} {row['Buyer']}: {row['Status']} -> {row['Next step']}")
    for payment in unmatched:
        ref_note = f" for order ref {payment['order_ref']}" if payment.get("order_ref") else ""
        items.append(
            f"PAYMENT WITH NO ORDER: £{payment['amount'] // 100} from {payment['email'] or 'unknown'}{ref_note} "
            f"on {payment['paid_at'][:10]} ({payment['session']}). Find the enquiry, then quote it "
            f"(prepare_order quote ...) so the payment attaches, or refund it in Stripe."
        )
    return items


def _print_table(table: list[dict[str, str]], columns: list[str]) -> None:
    widths = {c: min(max(len(c), *(len(r[c]) for r in table)), 72) for c in columns}
    print("  ".join(c.ljust(widths[c]) for c in columns))
    print("  ".join("-" * widths[c] for c in columns))
    for row in table:
        print("  ".join(row[c][: widths[c]].ljust(widths[c]) for c in columns))


def show(table: list[dict[str, str]], todo: list[str], notes: list[str]) -> None:
    t = totals(table)
    print(f"ORDERS {t['orders']} | quoted, not paid {t['quoted_not_paid']} | paid {t['paid']} "
          f"(£{t['revenue_gbp']}) | delivered in full {t['complete']} | paid awaiting delivery "
          f"{t['paid_awaiting_delivery']} | overdue {t['overdue']} | payment problems {t['payment_problems']}")
    print()
    print("ACTION NEEDED" if todo else "ACTION NEEDED: nothing. Every order is up to date.")
    for item in todo:
        print(f"  - {item}")
    print()
    if table:
        _print_table(table, ["Ref", "Product", "Buyer", "Scope", "Quote", "Paid", "Delivered", "Due", "Status"])
    else:
        print("No orders yet. Start one with: .venv/bin/python -m tools.prepare_order quote brief ...")
    for note in notes:
        print(f"Note: {note}")


def write_report(table: list[dict[str, str]], todo: list[str], notes: list[str], *, out_dir: Path = REPORT_DIR) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md_path = out_dir / f"orders-report-{stamp}.md"
    csv_path = out_dir / f"orders-report-{stamp}.csv"
    t = totals(table)
    bought = [r for r in table if r["Paid"] != "-"]
    not_bought = [r for r in table if r["Paid"] == "-"]
    delivered = [r for r in table if r["Status"] == "Complete"]

    def section(title: str, rows_: list[dict[str, str]]) -> list[str]:
        lines = [f"## {title} ({len(rows_)})", ""]
        if not rows_:
            return lines + ["None.", ""]
        cols = ["Ref", "Product", "Buyer", "Scope", "Quote", "Paid", "Delivered", "Status"]
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "---|" * len(cols))
        lines += ["| " + " | ".join(r[c].replace("|", "/") for c in cols) + " |" for r in rows_]
        return lines + [""]

    lines = [
        f"# CareGist orders report, {stamp}",
        "",
        f"- Orders: **{t['orders']}**",
        f"- Bought (paid): **{t['paid']}**, revenue **£{t['revenue_gbp']}** (no VAT)",
        f"- Not bought yet (quoted only): **{t['quoted_not_paid']}**",
        f"- Delivered in full: **{t['complete']}**",
        f"- Paid, delivery outstanding: **{t['paid_awaiting_delivery']}** (overdue: {t['overdue']})",
        f"- Payment problems (refunded, disputed or unverifiable; not in revenue): **{t['payment_problems']}**",
        "",
        "## Action needed",
        "",
        *([f"- {item}" for item in todo] or ["- Nothing. Every order is up to date."]),
        "",
        *section("Bought", bought),
        *section("Not bought yet", not_bought),
        *section("Delivered in full", delivered),
        *([f"_Note: {n}_" for n in notes]),
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if table:
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
    else:
        csv_path.write_text("", encoding="utf-8")
    return md_path, csv_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--no-refresh", action="store_true", help="show recorded state without checking Stripe or the mailbox")
    p.add_argument("--report", action="store_true", help="also write a Markdown and CSV report under orders/reports/")
    args = p.parse_args(argv)

    notes, unmatched = ([], []) if args.no_refresh else refresh(po.load_env())
    table = rows()
    todo = actions(table, unmatched)
    show(table, todo, notes)
    if args.report:
        md_path, csv_path = write_report(table, todo, notes)
        print(f"\nReport: {md_path}\nCSV:    {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
