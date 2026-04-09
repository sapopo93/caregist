#!/usr/bin/env python3
"""
Per-user provider monitor rating-change alerts.

For each user with monitored providers (provider_monitors table), finds providers
whose rating changed since the user's last alert was sent, then queues an email
via pending_emails. Gated to Pro+ tier only.

Usage:
    python3 tools/send_monitor_alerts.py             # Send all pending alerts
    python3 tools/send_monitor_alerts.py --dry-run   # Preview without sending
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import traceback


# ── Config ──

APP_URL = os.environ.get("APP_URL", "https://caregist.co.uk")
ALERT_TIERS = {"pro", "business", "enterprise"}
WEBHOOK_TIERS = {"business", "enterprise"}

RATING_ORDER = {"Outstanding": 1, "Good": 2, "Requires Improvement": 3, "Inadequate": 4}
UPGRADE_COLOR = "#4A5E45"
DOWNGRADE_COLOR = "#C44444"
BRAND_COLOR = "#C1784F"
ALERT_EMAIL_TO = os.environ.get("MONITOR_ALERT_FAILURE_EMAIL") or os.environ.get("ENQUIRY_FROM_EMAIL") or "hello@caregist.co.uk"


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not url:
        raise RuntimeError("DATABASE_URL not set.")
    return url


def get_connection(db_url: str):
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn


def rating_direction(old_rating: str | None, new_rating: str | None) -> str:
    old_rank = RATING_ORDER.get(old_rating or "", 99)
    new_rank = RATING_ORDER.get(new_rating or "", 99)
    if new_rank < old_rank:
        return "improved"
    if new_rank > old_rank:
        return "declined"
    return "changed"


def build_email_html(user_name: str, changes: list[dict]) -> str:
    rows = ""
    for c in changes:
        direction = rating_direction(c["previous_rating"], c["new_rating"])
        color = UPGRADE_COLOR if direction == "improved" else DOWNGRADE_COLOR
        arrow = "↑" if direction == "improved" else ("↓" if direction == "declined" else "→")
        rows += f"""
        <tr>
          <td style="padding:8px 0;border-bottom:1px solid #eee;">
            <a href="{APP_URL}/provider/{c['slug']}" style="color:{BRAND_COLOR};text-decoration:none;font-weight:600;">{c['name']}</a>
            <br><small style="color:#888;">{c['town'] or ''}</small>
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;color:#888;text-decoration:line-through;">{c['previous_rating'] or '—'}</td>
          <td style="padding:8px 0;border-bottom:1px solid #eee;color:{color};font-weight:600;">{arrow} {c['new_rating'] or '—'}</td>
        </tr>"""

    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px;">
      <p style="color:#8a6a4a;font-size:12px;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">CareGist</p>
      <h2 style="color:#2C1A0E;margin-top:0;">Rating changes on your monitored providers</h2>
      <p style="color:#555;">Hi {user_name or 'there'}, the following providers you monitor have had a CQC rating change.</p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0;">
        <thead>
          <tr>
            <th style="text-align:left;padding:8px 0;border-bottom:2px solid #C1784F;color:#2C1A0E;">Provider</th>
            <th style="text-align:left;padding:8px 12px;border-bottom:2px solid #C1784F;color:#2C1A0E;">Previous</th>
            <th style="text-align:left;padding:8px 0;border-bottom:2px solid #C1784F;color:#2C1A0E;">New</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="margin-top:24px;">
        <a href="{APP_URL}/dashboard" style="background:{BRAND_COLOR};color:white;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;">View your monitors →</a>
      </p>
      <p style="color:#aaa;font-size:11px;margin-top:32px;">
        You are receiving this because you monitor these providers on CareGist.
        <a href="{APP_URL}/dashboard" style="color:#aaa;">Manage your monitors</a>
      </p>
    </div>"""


def notify_failure(exc: Exception) -> None:
    resend_api_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_api_key:
        print(f"[ALERT] send_monitor_alerts failed: {exc}", file=sys.stderr)
        return

    import json
    from urllib import request as urllib_request

    from_email = os.environ.get("ENQUIRY_FROM_EMAIL", "noreply@caregist.co.uk")
    body = (
        "send_monitor_alerts.py failed.\n\n"
        f"Error: {type(exc).__name__}: {exc}\n\n"
        f"Traceback:\n{traceback.format_exc()}"
    )
    try:
        req = urllib_request.Request(
            "https://api.resend.com/emails",
            data=json.dumps({
                "from": from_email,
                "to": [ALERT_EMAIL_TO],
                "subject": "CareGist monitor alert job failed",
                "text": body,
            }).encode(),
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=10):
            pass
    except Exception as notify_exc:
        print(f"[ALERT] Failed to send monitor alert failure email: {notify_exc}", file=sys.stderr)


def run(dry_run: bool = False) -> None:
    import psycopg2.extras

    db_url = get_database_url()
    conn = get_connection(db_url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Find all monitors for Pro+ users that have had rating changes since last alert
    cur.execute("""
        SELECT
            pm.id          AS monitor_id,
            pm.user_id,
            pm.provider_id,
            pm.last_alert_sent_at,
            u.email,
            u.name         AS user_name,
            ak.tier,
            cp.name        AS provider_name,
            cp.town,
            cp.slug,
            cp.overall_rating AS current_rating
        FROM provider_monitors pm
        JOIN users u ON u.id = pm.user_id
        JOIN api_keys ak ON ak.user_id = pm.user_id AND ak.is_active = TRUE
        JOIN care_providers cp ON cp.id = pm.provider_id
        WHERE ak.tier = ANY(%(tiers)s)
          AND u.email IS NOT NULL
        ORDER BY pm.user_id, pm.provider_id
    """, {"tiers": list(ALERT_TIERS)})
    monitors = cur.fetchall()

    if not monitors:
        print("No eligible monitors found.")
        conn.close()
        return

    # For each monitor, find rating changes since last_alert_sent_at
    # Group by user so we send one email per user
    user_changes: dict[int, dict] = {}

    for m in monitors:
        watermark = m["last_alert_sent_at"]
        cur.execute("""
            SELECT
                prh.provider_id,
                prh.previous_rating,
                prh.new_rating,
                prh.changed_at
            FROM provider_rating_history prh
            WHERE prh.provider_id = %(provider_id)s
              AND prh.changed_at > %(watermark)s
            ORDER BY prh.changed_at DESC
            LIMIT 1
        """, {
            "provider_id": m["provider_id"],
            "watermark": watermark or m.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
        })
        changes = cur.fetchall()
        if not changes:
            continue

        latest = changes[0]
        uid = m["user_id"]
        if uid not in user_changes:
            user_changes[uid] = {
                "email": m["email"],
                "user_name": m["user_name"],
                "tier": m["tier"],
                "monitor_ids": [],
                "provider_changes": [],
            }
        user_changes[uid]["monitor_ids"].append(m["monitor_id"])
        user_changes[uid]["provider_changes"].append({
            "name": m["provider_name"],
            "town": m["town"],
            "slug": m["slug"],
            "previous_rating": latest["previous_rating"],
            "new_rating": latest["new_rating"],
        })

    if not user_changes:
        print("No new rating changes found for any monitored providers.")
        conn.close()
        return

    now = datetime.now(timezone.utc)
    sent = 0

    for uid, data in user_changes.items():
        subject = f"Rating changes on {len(data['provider_changes'])} monitored provider{'s' if len(data['provider_changes']) != 1 else ''}"
        html = build_email_html(data["user_name"], data["provider_changes"])

        if dry_run:
            print(f"[DRY RUN] Would send to {data['email']}: {subject}")
            for c in data["provider_changes"]:
                print(f"  {c['name']}: {c['previous_rating']} → {c['new_rating']}")
            if data["tier"] in WEBHOOK_TIERS:
                print(f"  [DRY RUN] Would deliver webhooks for user {uid} (tier={data['tier']})")
            continue

        # Queue the email
        cur.execute("""
            INSERT INTO pending_emails (to_email, subject, html_body, send_after)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (data["email"], subject, html, now))

        # Update watermark on all affected monitors
        if data["monitor_ids"]:
            cur.execute("""
                UPDATE provider_monitors
                SET last_alert_sent_at = %s
                WHERE id = ANY(%s)
            """, (now, data["monitor_ids"]))

        sent += 1

        # Webhook delivery for Business+ users
        if data["tier"] in WEBHOOK_TIERS:
            cur.execute("""
                SELECT id, url, secret
                FROM webhook_subscriptions
                WHERE user_id = %s AND active = TRUE AND 'provider.rating_changed' = ANY(events)
            """, (uid,))
            subs = cur.fetchall()
            if subs:
                import asyncio
                sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
                from api.utils.webhook_delivery import deliver_webhook
                now_iso = now.isoformat()
                for change in data["provider_changes"]:
                    payload = {
                        "event": "provider.rating_changed",
                        "timestamp": now_iso,
                        "provider_name": change["name"],
                        "provider_slug": change["slug"],
                        "previous_rating": change["previous_rating"],
                        "new_rating": change["new_rating"],
                    }
                    for sub in subs:
                        success = asyncio.run(deliver_webhook(sub["url"], sub["secret"], payload))
                        if success:
                            cur.execute("""
                                UPDATE webhook_subscriptions
                                SET last_delivery_at = %s, delivery_failures = 0
                                WHERE id = %s
                            """, (now, sub["id"]))
                        else:
                            cur.execute("""
                                UPDATE webhook_subscriptions
                                SET delivery_failures = delivery_failures + 1
                                WHERE id = %s
                            """, (sub["id"],))

    if not dry_run:
        conn.commit()
        print(f"Queued alerts for {sent} user(s).")
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Send per-user provider monitor rating-change alerts.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without queuing emails.")
    args = parser.parse_args()
    try:
        run(dry_run=args.dry_run)
    except Exception as exc:
        notify_failure(exc)
        raise


if __name__ == "__main__":
    main()
