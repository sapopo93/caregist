"""Local order ledger for human-led sales (one row per order, one per email step).

tools/prepare_order.py records every quote and delivery here; tools/orders.py
shows the table and works out paid / sent status live. The file holds buyer
emails, so it lives in orders/ (git-ignored) on the founder's machine and is
never committed. Override the path with CAREGIST_ORDER_LEDGER.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = REPO_ROOT / "orders" / "ledger.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    order_ref       TEXT PRIMARY KEY,
    product         TEXT NOT NULL CHECK (product IN ('brief', 'digest')),
    buyer_email     TEXT NOT NULL,
    buyer_name      TEXT,
    company         TEXT,
    scope           TEXT NOT NULL,          -- human-readable scope line
    scope_json      TEXT NOT NULL,          -- exact arguments, to re-run delivery
    amount_pence    INTEGER NOT NULL,
    quoted_count    INTEGER,                -- Brief: organisations promised in the quote
    created_at      TEXT NOT NULL,
    paid_at         TEXT,
    payment_session TEXT,
    payment_source  TEXT
);
CREATE TABLE IF NOT EXISTS order_emails (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_ref       TEXT NOT NULL REFERENCES orders(order_ref),
    stage           TEXT NOT NULL CHECK (stage IN ('quote', 'deliver')),
    issue           INTEGER,                -- Digest issue 1-4; NULL for a Brief
    message_id      TEXT NOT NULL UNIQUE,   -- matched against the Sent folder
    subject         TEXT NOT NULL,
    drafted_at      TEXT NOT NULL,
    draft_location  TEXT NOT NULL,
    folder          TEXT NOT NULL,          -- local order folder with the files
    sent_at         TEXT
);
CREATE INDEX IF NOT EXISTS order_emails_ref ON order_emails(order_ref);
"""


def ledger_path() -> Path:
    return Path(os.environ.get("CAREGIST_ORDER_LEDGER") or DEFAULT_PATH)


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    target = path or ledger_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
    path: Path | None = None,
) -> None:
    """Create the order on first sight and log this drafted email against it."""
    with connect(path) as conn:
        existing = conn.execute("SELECT order_ref FROM orders WHERE order_ref = ?", (order_ref,)).fetchone()
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
        elif stage == "quote" and quoted_count is not None:
            # A re-quote replaces the promise; the latest quote is binding.
            conn.execute(
                "UPDATE orders SET quoted_count = ?, scope = ?, scope_json = ? WHERE order_ref = ?",
                (quoted_count, scope, json.dumps(scope_args, sort_keys=True), order_ref),
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
    conn.execute(
        """
        UPDATE orders SET paid_at = ?, payment_session = ?, payment_source = ?
        WHERE order_ref = ? AND paid_at IS NULL
        """,
        (payment["paid_at"], payment.get("session"), payment.get("source"), order_ref),
    )


def mark_sent(conn: sqlite3.Connection, message_id: str, sent_at: str) -> None:
    conn.execute(
        "UPDATE order_emails SET sent_at = ? WHERE message_id = ? AND sent_at IS NULL",
        (sent_at, message_id),
    )


def orders_with_emails(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    orders = [dict(row) for row in conn.execute("SELECT * FROM orders ORDER BY created_at DESC")]
    for order in orders:
        order["emails"] = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM order_emails WHERE order_ref = ? ORDER BY drafted_at", (order["order_ref"],)
            )
        ]
    return orders


def order_status(order: dict[str, Any]) -> str:
    """One plain-language status, from the furthest step reached."""
    emails = order["emails"]
    quotes = [e for e in emails if e["stage"] == "quote"]
    deliveries = [e for e in emails if e["stage"] == "deliver"]
    expected = 4 if order["product"] == "digest" else 1
    sent_issues = {e["issue"] or 1 for e in deliveries if e["sent_at"]}
    if len(sent_issues) >= expected:
        return "Complete"
    if any(not e["sent_at"] for e in deliveries):
        return "Delivery drafted: press Send"
    if order["paid_at"]:
        if order["product"] == "digest" and sent_issues:
            return f"Paid: issue {len(sent_issues) + 1} of 4 due"
        return "Paid: prepare delivery"
    if any(e["sent_at"] for e in quotes):
        return "Quote sent: awaiting payment"
    if quotes:
        return "Quote drafted: not sent yet"
    return "No quote yet"
