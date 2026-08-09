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

SLO_BREACH_ALERT_KEY = "new_registration_ingestion_slo_breach"
WATCHDOG_ALERT_PREFIX = "freshness_watchdog:"


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
        or "ops@caregist.co.uk"
    )


def _watchdog_alert_key(alert_key: str) -> str:
    return f"{WATCHDOG_ALERT_PREFIX}{alert_key}"


async def _is_new_or_resolved_alert(conn, alert_key: str) -> bool:
    existing = await conn.fetchrow(
        """
        SELECT resolved_at
        FROM pipeline_alert_state
        WHERE alert_key = $1
        """,
        _watchdog_alert_key(alert_key),
    )
    return existing is None or existing["resolved_at"] is not None


async def _record_alert(conn, alert_key: str, severity: str, details: dict) -> None:
    await conn.execute(
        """
        INSERT INTO pipeline_alert_state (
          alert_key, severity, details, first_seen_at, last_seen_at,
          occurrence_count, resolved_at
        )
        VALUES ($1, $2, $3::jsonb, NOW(), NOW(), 1, NULL)
        ON CONFLICT (alert_key) DO UPDATE
        SET severity = EXCLUDED.severity,
            details = EXCLUDED.details,
            last_seen_at = NOW(),
            occurrence_count = pipeline_alert_state.occurrence_count + 1,
            resolved_at = NULL
        """,
        _watchdog_alert_key(alert_key),
        severity,
        json.dumps({**details, "source": "freshness_watchdog"}),
    )


async def _resolve_watchdog_alerts(conn) -> None:
    await conn.execute(
        """
        UPDATE pipeline_alert_state
        SET resolved_at = NOW(), last_seen_at = NOW()
        WHERE alert_key LIKE $1
          AND resolved_at IS NULL
        """,
        f"{WATCHDOG_ALERT_PREFIX}%",
    )


async def _notify_and_record(conn, alert_key: str, subject: str, body: str, details: dict) -> None:
    should_notify = await _is_new_or_resolved_alert(conn, alert_key)
    if should_notify:
        # Record only after successful delivery so a transient Resend failure is
        # retried by the next watchdog invocation rather than silently suppressed.
        _send_email(subject, body)
    await _record_alert(conn, alert_key, "error", details)


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


def _check_entries(snapshot: dict) -> list[dict]:
    checks = snapshot.get("checks", [])
    if isinstance(checks, list):
        return [check for check in checks if isinstance(check, dict)]
    if isinstance(checks, dict):
        return [
            {"name": name, "ok": ok, "details": {}}
            for name, ok in checks.items()
            if isinstance(ok, bool)
        ]
    return []


def _build_alert_body(snapshot: dict) -> str:
    check_lines: list[str] = []
    for check in _check_entries(snapshot):
        name = str(check.get("name") or "unnamed_check")
        state = "OK" if check.get("ok") is True else "FAILED"
        raw_details = check.get("details")
        details = raw_details if isinstance(raw_details, dict) else {}
        detail_text = ", ".join(f"{key}={value}" for key, value in details.items())
        check_lines.append(f"- {name}: {state}" + (f" ({detail_text})" if detail_text else ""))

    return (
        "CareGist new-registration pipeline degraded.\n\n"
        f"Overall status: {snapshot.get('status', 'unknown')}\n"
        f"Readiness OK: {snapshot.get('readiness_ok', False)}\n"
        f"Feed fresh: {snapshot.get('feed_fresh', False)}\n"
        "Checks:\n"
        + ("\n".join(check_lines) if check_lines else "- pipeline_health_contract: FAILED (no checks returned)")
        + "\n"
    )


def _derive_alert_keys(snapshot: dict) -> list[str]:
    keys = [
        str(check["name"])
        for check in _check_entries(snapshot)
        if check.get("name") and check.get("ok") is False
    ]
    if not keys:
        keys.append("pipeline_degraded")
    return keys


async def _fetch_ingestion_slo_breach(conn) -> dict | None:
    row = await conn.fetchrow(
        """
        WITH recent_incremental AS (
            SELECT COALESCE(records_added, 0) AS records_added
            FROM pipeline_runs
            WHERE run_type = 'incremental'
              AND status = 'completed'
            ORDER BY completed_at DESC NULLS LAST
            LIMIT 5
        ),
        alert_window AS (
            SELECT COALESCE(SUM(occurrence_count), 0) AS unavailable_alerts
            FROM pipeline_alert_state
            WHERE alert_key = 'changes_endpoint_unavailable'
              AND last_seen_at >= NOW() - INTERVAL '7 days'
        )
        SELECT
            MAX(cp.registration_date) AS latest_registration_date,
            COALESCE(MAX(cp.registration_date) < NOW() - INTERVAL '7 days', TRUE) AS registration_stale,
            (SELECT unavailable_alerts FROM alert_window) AS unavailable_alerts,
            (
                SELECT COUNT(*) = 5 AND BOOL_AND(records_added = 0)
                FROM recent_incremental
            ) AS last_five_incrementals_zero
        FROM care_providers cp
        """
    )
    if row is None or int(row["unavailable_alerts"] or 0) == 0:
        return None

    registration_stale = bool(row["registration_stale"])
    last_five_incrementals_zero = bool(row["last_five_incrementals_zero"])
    if not registration_stale and not last_five_incrementals_zero:
        return None

    return {
        "alert_key": SLO_BREACH_ALERT_KEY,
        "latest_registration_date": (
            row["latest_registration_date"].isoformat()
            if row["latest_registration_date"] is not None
            else None
        ),
        "registration_stale": registration_stale,
        "changes_endpoint_unavailable_alerts_last_7d": int(row["unavailable_alerts"] or 0),
        "last_five_incrementals_zero": last_five_incrementals_zero,
    }


async def check_pipeline(database_url: str, *, notify: bool) -> int:
    conn = await asyncpg.connect(database_url)
    try:
        slo_breach = await _fetch_ingestion_slo_breach(conn)
        if slo_breach is not None:
            message = (
                "SLO BREACH: new CQC registration ingestion is stale while "
                "/changes/location is unavailable.\n"
                f"{json.dumps(slo_breach, indent=2)}"
            )
            print(message, file=sys.stderr)
            if notify:
                await _notify_and_record(
                    conn,
                    SLO_BREACH_ALERT_KEY,
                    "CareGist pipeline alert: new registration ingestion SLO breach",
                    message,
                    slo_breach,
                )
            return 1

        snapshot = await get_pipeline_health(conn)
        print(json.dumps(snapshot, indent=2))
        if snapshot["readiness_ok"] and snapshot["status"] == "healthy":
            if notify:
                await _resolve_watchdog_alerts(conn)
            return 0

        if notify:
            body = _build_alert_body(snapshot)
            for alert_key in _derive_alert_keys(snapshot):
                await _notify_and_record(
                    conn,
                    alert_key,
                    f"CareGist pipeline alert: {alert_key}",
                    body,
                    snapshot,
                )
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
