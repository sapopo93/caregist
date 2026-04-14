#!/usr/bin/env python3
"""Check the operational health of the new-registration pipeline and optionally alert."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib import request as urllib_request

import asyncpg

from api.services.pipeline_health import get_pipeline_health

ALERT_SUPPRESSION_HOURS = 6


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key and key not in os.environ:
            os.environ[key.strip()] = value.strip()


def _alert_email_to() -> str:
    return (
        os.environ.get("PIPELINE_ALERT_EMAIL")
        or os.environ.get("MONITOR_ALERT_FAILURE_EMAIL")
        or os.environ.get("ENQUIRY_FROM_EMAIL")
        or "hello@caregist.co.uk"
    )


async def _should_send_alert(conn, alert_key: str) -> bool:
    existing = await conn.fetchval(
        """
        SELECT id
        FROM pipeline_alert_log
        WHERE alert_key = $1
          AND created_at >= NOW() - make_interval(hours => $2)
        ORDER BY created_at DESC
        LIMIT 1
        """,
        alert_key,
        ALERT_SUPPRESSION_HOURS,
    )
    return existing is None


async def _log_alert(conn, alert_key: str, severity: str, details: dict) -> None:
    await conn.execute(
        """
        INSERT INTO pipeline_alert_log (alert_key, severity, details)
        VALUES ($1, $2, $3::jsonb)
        """,
        alert_key,
        severity,
        json.dumps(details),
    )


def _send_email(subject: str, body: str) -> None:
    resend_api_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_api_key:
        raise RuntimeError("RESEND_API_KEY not set.")

    from_email = os.environ.get("ENQUIRY_FROM_EMAIL", "noreply@caregist.co.uk")
    req = urllib_request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(
            {
                "from": from_email,
                "to": [_alert_email_to()],
                "subject": subject,
                "text": body,
            }
        ).encode(),
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=10):
        pass


def _build_alert_body(snapshot: dict) -> str:
    checks = snapshot["checks"]
    return (
        "CareGist new-registration pipeline degraded.\n\n"
        f"Overall status: {snapshot['status']}\n"
        f"Readiness OK: {snapshot['readiness_ok']}\n"
        f"Feed fresh: {snapshot['feed_fresh']}\n"
        f"Last incremental: {checks['last_incremental_completed_at']}\n"
        f"Last feed cycle: {checks['last_feed_cycle_completed_at']}\n"
        f"Latest feed observed_at: {checks['latest_new_registration_observed_at']}\n"
        f"New registration events last 24h: {checks['new_registration_events_last_24h']}\n"
        f"Pending emails: {checks['pending_email_count']}\n"
        f"Stuck processing emails: {checks['stuck_processing_email_count']}\n"
    )


def _derive_alert_keys(snapshot: dict) -> list[str]:
    checks = snapshot["checks"]
    keys: list[str] = []
    if not checks["incremental_fresh"]:
        keys.append("incremental_stale")
    if not checks["feed_cycle_fresh"]:
        keys.append("feed_cycle_stale")
    if not checks["email_backlog_healthy"]:
        keys.append("email_backlog")
    if not checks["email_processing_healthy"]:
        keys.append("email_processing_stuck")
    if not keys:
        keys.append("pipeline_degraded")
    return keys


async def check_pipeline(database_url: str, *, notify: bool) -> int:
    conn = await asyncpg.connect(database_url)
    try:
        snapshot = await get_pipeline_health(conn)
        print(json.dumps(snapshot, indent=2))
        if snapshot["readiness_ok"] and snapshot["status"] == "healthy":
            return 0

        if notify:
            body = _build_alert_body(snapshot)
            for alert_key in _derive_alert_keys(snapshot):
                if await _should_send_alert(conn, alert_key):
                    _send_email(f"CareGist pipeline alert: {alert_key}", body)
                    await _log_alert(conn, alert_key, "error", snapshot)
        return 1
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check CareGist new-registration pipeline health")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--notify", action="store_true", help="Send deduplicated alert emails on failure")
    return parser.parse_args()


def main() -> int:
    _load_env_file()
    args = parse_args()
    if not args.database_url:
        print("ERROR: DATABASE_URL not set.", file=sys.stderr)
        return 1
    return asyncio.run(check_pipeline(args.database_url, notify=args.notify))


if __name__ == "__main__":
    raise SystemExit(main())
