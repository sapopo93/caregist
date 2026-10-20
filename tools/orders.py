"""Show every order and where it stands: quoted, paid, delivered, sent.

  .venv/bin/python -m tools.orders              # refresh and show the table
  .venv/bin/python -m tools.orders --no-refresh # show what is recorded, offline
  .venv/bin/python -m tools.orders --csv orders.csv

Refresh is read-only. Payment comes from CareGist's sales record or Stripe
(the same check delivery uses); "sent" comes from the outreach@ Sent folder,
matched by the order reference in the subject and the buyer's address. Without
OUTREACH_IMAP_PASSWORD, sent status cannot be refreshed and the table says so.
"""

from __future__ import annotations

import argparse
import csv
import imaplib
import ssl
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from tools import order_ledger as ledger
from tools import prepare_order as po


def _sent_mailbox(conn: imaplib.IMAP4_SSL) -> str:
    status, folders = conn.list()
    if status == "OK":
        for raw in folders or []:
            line = raw.decode("utf-8", "replace")
            if "\\Sent" in line:
                return line.rsplit(' "', 1)[-1].strip('"') if ' "' in line else line.split()[-1]
    return "Sent"


def find_sent(env: dict[str, str], pending: list[dict[str, Any]]) -> dict[str, str]:
    """message_id -> sent time, for drafted emails now found in the Sent folder."""
    password = env.get("OUTREACH_IMAP_PASSWORD") or ""
    if not password or not pending:
        return {}
    conn = imaplib.IMAP4_SSL(
        env.get("OUTREACH_IMAP_HOST") or "mail.privateemail.com", 993, ssl_context=ssl.create_default_context()
    )
    found: dict[str, str] = {}
    try:
        conn.login(env.get("OUTREACH_IMAP_USER") or po.FROM_ADDRESS, password)
        conn.select(_sent_mailbox(conn), readonly=True)
        for email_row in pending:
            ref = email_row["order_ref"]
            status, data = conn.search(None, "SUBJECT", f'"{ref}"', "TO", f'"{email_row["buyer_email"]}"')
            if status != "OK" or not data or not data[0]:
                continue
            for number in data[0].split():
                status, header = conn.fetch(number, "(BODY.PEEK[HEADER.FIELDS (SUBJECT DATE)])")
                if status != "OK" or not header or not isinstance(header[0], tuple):
                    continue
                text = header[0][1].decode("utf-8", "replace")
                # Match the stage too, so a sent quote is not taken for a sent delivery.
                if email_row["subject"].split(" (ref ")[0][:40] in " ".join(text.split()):
                    date_line = next((ln for ln in text.splitlines() if ln.lower().startswith("date:")), "")
                    try:
                        sent = parsedate_to_datetime(date_line[5:].strip()).astimezone(timezone.utc).isoformat(timespec="seconds")
                    except (TypeError, ValueError):
                        sent = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    found[email_row["message_id"]] = sent
                    break
    finally:
        try:
            conn.logout()
        except Exception:
            pass
    return found


def refresh(env: dict[str, str], *, path: Path | None = None) -> list[str]:
    """Update paid and sent status in the ledger. Returns notes for the reader."""
    notes: list[str] = []
    with ledger.connect(path) as conn:
        orders = ledger.orders_with_emails(conn)
        for order in orders:
            if not order["paid_at"]:
                try:
                    payment = po.find_payment(env, order["buyer_email"], order["amount_pence"])
                except Exception as exc:  # network or DB unavailable: keep last known state
                    notes.append(f"Payment check unavailable ({type(exc).__name__}); showing last known state.")
                    break
                if payment:
                    ledger.record_payment(conn, order["order_ref"], payment)
        pending = [
            {**email_row, "buyer_email": order["buyer_email"]}
            for order in orders
            for email_row in order["emails"]
            if not email_row["sent_at"]
        ]
        if pending and not env.get("OUTREACH_IMAP_PASSWORD"):
            notes.append("Sent status not refreshed: add OUTREACH_IMAP_PASSWORD to .env.")
        else:
            try:
                for message_id, sent_at in find_sent(env, pending).items():
                    ledger.mark_sent(conn, message_id, sent_at)
            except (imaplib.IMAP4.error, OSError) as exc:
                notes.append(f"Sent folder unavailable ({type(exc).__name__}); showing last known state.")
    return notes


def rows(path: Path | None = None) -> list[dict[str, str]]:
    with ledger.connect(path) as conn:
        orders = ledger.orders_with_emails(conn)
    table = []
    for order in orders:
        emails = order["emails"]
        quotes = [e for e in emails if e["stage"] == "quote"]
        deliveries = [e for e in emails if e["stage"] == "deliver"]
        expected = 4 if order["product"] == "digest" else 1
        sent_deliveries = {e["issue"] or 1 for e in deliveries if e["sent_at"]}
        table.append({
            "Ref": order["order_ref"],
            "Product": "Brief £745" if order["product"] == "brief" else "Digest £150",
            "Buyer": order["buyer_email"] + (f" ({order['company']})" if order["company"] else ""),
            "Scope": order["scope"] + (f" · {order['quoted_count']} orgs" if order["quoted_count"] else ""),
            "Quote": ("sent " + quotes[-1]["sent_at"][:10]) if any(e["sent_at"] for e in quotes)
                     else ("drafted " + quotes[-1]["drafted_at"][:10] if quotes else "-"),
            "Paid": (order["paid_at"] or "")[:10] or "-",
            "Delivered": f"{len(sent_deliveries)}/{expected} sent" if deliveries else "-",
            "Status": ledger.order_status(order),
        })
    return table


def print_table(table: list[dict[str, str]]) -> None:
    if not table:
        print("No orders yet. Run tools.prepare_order ... quote to create one.")
        return
    columns = list(table[0])
    widths = {c: min(max(len(c), *(len(r[c]) for r in table)), 64) for c in columns}
    line = "  ".join(c.ljust(widths[c]) for c in columns)
    print(line)
    print("  ".join("-" * widths[c] for c in columns))
    for row in table:
        print("  ".join(row[c][: widths[c]].ljust(widths[c]) for c in columns))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--no-refresh", action="store_true", help="show recorded state without checking Stripe or the mailbox")
    p.add_argument("--csv", type=Path, default=None, help="also write the table to this CSV file")
    args = p.parse_args(argv)

    notes = [] if args.no_refresh else refresh(po.load_env())
    table = rows()
    print_table(table)
    for note in notes:
        print(f"Note: {note}")
    if args.csv and table:
        with args.csv.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
        print(f"Wrote {args.csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
