"""Local order ledger for human-led sales (one row per order, one per email step).

tools/prepare_order.py records every quote and delivery here; tools/orders.py
shows the table, the action list and the report, working out paid / sent status
live. The file holds buyer emails, so it lives in orders/ (git-ignored) on the
founder's machine and is never committed. Override with CAREGIST_ORDER_LEDGER.

Guarantees enforced here:
- one Stripe payment can be attached to one order only (unique index);
- a replaced draft is marked superseded and never counts as sent or pending;
- every order has exactly one next action and, once paid, a due date.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = REPO_ROOT / "orders" / "ledger.sqlite"
DELIVERY_WORKING_DAYS = 3
DIGEST_ISSUES = 4

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    order_ref       TEXT PRIMARY KEY,
    product         TEXT NOT NULL CHECK (product IN ('brief', 'digest')),
    buyer_email     TEXT NOT NULL,
    buyer_name      TEXT,
    company         TEXT,
    scope           TEXT NOT NULL,          -- human-readable scope line
    scope_json      TEXT NOT NULL,          -- exact arguments, so delivery never retypes them
    amount_pence    INTEGER NOT NULL,
    quoted_count    INTEGER,                -- Brief: organisations promised in the quote
    created_at      TEXT NOT NULL,
    paid_at         TEXT,
    payment_session TEXT,
    payment_source  TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS orders_one_order_per_payment
    ON orders(payment_session) WHERE payment_session IS NOT NULL;
CREATE TABLE IF NOT EXISTS order_emails (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_ref       TEXT NOT NULL REFERENCES orders(order_ref),
    stage           TEXT NOT NULL CHECK (stage IN ('quote', 'deliver')),
    issue           INTEGER,                -- Digest issue 1-4; NULL for a Brief
    message_id      TEXT NOT NULL UNIQUE,
    subject         TEXT NOT NULL,          -- ends with "(ref <order_ref>)"
    drafted_at      TEXT NOT NULL,
    draft_location  TEXT NOT NULL,
    folder          TEXT NOT NULL,          -- local order folder with the files
    sent_at         TEXT,
    superseded_at   TEXT                    -- replaced by a later draft; ignored
);
CREATE INDEX IF NOT EXISTS order_emails_ref ON order_emails(order_ref);
"""


class LedgerError(RuntimeError):
    """A rule that keeps orders correct would be broken; nothing was written."""


def ledger_path() -> Path:
    return Path(os.environ.get("CAREGIST_ORDER_LEDGER") or DEFAULT_PATH)


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    target = path or ledger_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(order_emails)")}
        if columns and "superseded_at" not in columns:
            conn.execute("ALTER TABLE order_emails ADD COLUMN superseded_at TEXT")
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    # Microseconds keep orders created in the same second in a stable order (payment FIFO).
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def add_working_days(start: date, days: int) -> date:
    current = start
    while days > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days -= 1
    return current


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #


def _attach_emails(conn: sqlite3.Connection, order: dict[str, Any]) -> dict[str, Any]:
    order["emails"] = [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM order_emails WHERE order_ref = ? ORDER BY drafted_at, id", (order["order_ref"],)
        )
    ]
    order["scope_args"] = json.loads(order["scope_json"])
    return order


def get_order(conn: sqlite3.Connection, order_ref: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM orders WHERE order_ref = ?", (order_ref.strip(),)).fetchone()
    return _attach_emails(conn, dict(row)) if row else None


def orders_with_emails(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [_attach_emails(conn, dict(row)) for row in conn.execute("SELECT * FROM orders ORDER BY created_at DESC, rowid DESC")]


def claimed_sessions(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT payment_session FROM orders WHERE payment_session IS NOT NULL")}


def live(emails: list[dict[str, Any]], stage: str) -> list[dict[str, Any]]:
    """Emails of a stage that have not been replaced by a later draft."""
    return [e for e in emails if e["stage"] == stage and not e.get("superseded_at")]


def sent_issues(order: dict[str, Any]) -> set[int]:
    return {e["issue"] or 1 for e in live(order["emails"], "deliver") if e["sent_at"]}


def is_complete(order: dict[str, Any]) -> bool:
    expected = DIGEST_ISSUES if order["product"] == "digest" else 1
    return len(sent_issues(order)) >= expected


def open_orders_for(conn: sqlite3.Connection, buyer_email: str, product: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM orders WHERE lower(buyer_email) = lower(?) AND product = ?",
        (buyer_email.strip(), product),
    )
    return [o for o in (_attach_emails(conn, dict(r)) for r in rows) if not is_complete(o)]


# --------------------------------------------------------------------------- #
# Writes
# --------------------------------------------------------------------------- #


def record_email(
    *,
    order_ref: str,
    product: str,
    stage: str,
    buyer_email: str,
    buyer_name: str,
    company: str,
    scope: str,
    scope_args: dict[str, Any],
    amount_pence: int,
    quoted_count: int | None,
    message_id: str,
    subject: str,
    draft_location: str,
    folder: str,
    issue: int | None = None,
    payment: dict[str, Any] | None = None,
    supersede_email_id: int | None = None,
    path: Path | None = None,
) -> None:
    """Create the order on first sight and log this drafted email against it."""
    with connect(path) as conn:
        existing = get_order(conn, order_ref)
        if existing is None:
            conn.execute(
                """
                INSERT INTO orders (order_ref, product, buyer_email, buyer_name, company, scope,
                                    scope_json, amount_pence, quoted_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (order_ref, product, buyer_email.strip(), buyer_name, company, scope,
                 json.dumps(scope_args, sort_keys=True), amount_pence, quoted_count, _now()),
            )
        else:
            if existing["product"] != product or existing["buyer_email"].lower() != buyer_email.strip().lower():
                raise LedgerError(f"{order_ref} belongs to {existing['buyer_email']} ({existing['product']}); not changed.")
            if stage == "quote":
                # A re-quote replaces the scope and promise; the latest quote is binding
                # (Digest quotes carry no count, so the scope must still be replaced).
                conn.execute(
                    "UPDATE orders SET quoted_count = ?, scope = ?, scope_json = ? WHERE order_ref = ?",
                    (quoted_count, scope, json.dumps(scope_args, sort_keys=True), order_ref),
                )
        if supersede_email_id is not None:
            conn.execute(
                "UPDATE order_emails SET superseded_at = ? WHERE id = ? AND order_ref = ? AND sent_at IS NULL",
                (_now(), supersede_email_id, order_ref),
            )
        if payment:
            record_payment(conn, order_ref, payment)
        conn.execute(
            """
            INSERT INTO order_emails (order_ref, stage, issue, message_id, subject, drafted_at,
                                      draft_location, folder)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (order_ref, stage, issue, message_id, subject, _now(), draft_location, folder),
        )


def record_payment(conn: sqlite3.Connection, order_ref: str, payment: dict[str, Any]) -> None:
    session = payment.get("session")
    if session:
        other = conn.execute(
            "SELECT order_ref FROM orders WHERE payment_session = ? AND order_ref != ?", (session, order_ref)
        ).fetchone()
        if other:
            raise LedgerError(f"payment {session} already belongs to order {other[0]}")
    conn.execute(
        """
        UPDATE orders SET paid_at = ?, payment_session = ?, payment_source = ?
        WHERE order_ref = ? AND paid_at IS NULL
        """,
        (payment["paid_at"], session, payment.get("source"), order_ref),
    )


def mark_sent(conn: sqlite3.Connection, message_id: str, sent_at: str) -> None:
    conn.execute(
        "UPDATE order_emails SET sent_at = ? WHERE message_id = ? AND sent_at IS NULL",
        (sent_at, message_id),
    )


# --------------------------------------------------------------------------- #
# Status and next action
# --------------------------------------------------------------------------- #


def digest_issue_due(order: dict[str, Any], issue: int) -> date | None:
    start = order["scope_args"].get("start_date")
    return date.fromisoformat(start) + timedelta(weeks=issue - 1) if start else None


def next_action(order: dict[str, Any], today: date) -> dict[str, Any]:
    """The single next thing to do for this order, with the exact command."""
    ref = order["order_ref"]
    deliver_cmd = f".venv/bin/python -m tools.prepare_order deliver --order-ref {ref}"
    quotes = live(order["emails"], "quote")
    deliveries = live(order["emails"], "deliver")
    pending_delivery = [e for e in deliveries if not e["sent_at"]]

    if is_complete(order):
        return {"status": "Complete", "next": "-", "due": None, "overdue": False, "action": False}
    if pending_delivery:
        return {"status": "Delivery drafted: press Send", "next": f"Send the draft in outreach@ Drafts (ref {ref})",
                "due": None, "overdue": False, "action": True}
    if order["paid_at"]:
        paid = date.fromisoformat(order["paid_at"][:10])
        if order["product"] == "brief":
            due = add_working_days(paid, DELIVERY_WORKING_DAYS)
            return {"status": "Paid: prepare delivery", "next": deliver_cmd, "due": due,
                    "overdue": today > due, "action": True}
        issue = len(sent_issues(order)) + 1
        due = digest_issue_due(order, issue) or paid
        if today < due:
            return {"status": f"Paid: issue {issue} of 4 due {due.isoformat()}", "next": f"Wait until {due.isoformat()}",
                    "due": due, "overdue": False, "action": False}
        return {"status": f"Paid: issue {issue} of 4 due", "next": deliver_cmd, "due": due,
                "overdue": today > due, "action": True}
    if any(e["sent_at"] for e in quotes):
        sent = date.fromisoformat(max(e["sent_at"] for e in quotes if e["sent_at"])[:10])
        follow_up = (today - sent).days >= 7
        return {"status": "Quote sent: awaiting payment", "next": "Follow up with the buyer" if follow_up else "Wait for payment",
                "due": None, "overdue": False, "action": follow_up}
    if quotes:
        return {"status": "Quote drafted: not sent yet", "next": f"Send the quote draft in outreach@ Drafts (ref {ref})",
                "due": None, "overdue": False, "action": True}
    return {"status": "No quote yet", "next": "Run prepare_order quote", "due": None, "overdue": False, "action": True}


def order_status(order: dict[str, Any], today: date | None = None) -> str:
    return next_action(order, today or datetime.now(timezone.utc).date())["status"]
