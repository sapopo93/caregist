#!/usr/bin/env python3
"""
Weekly CQC Movers email digest.

Sends each subscriber a personalised email showing rating changes near their
postcode in the last 7 days. Falls back to national highlights if no local
changes. Includes idempotency check to prevent duplicate sends.

Usage:
    python3 tools/send_weekly_movers.py                    # Send to all subscribers
    python3 tools/send_weekly_movers.py --dry-run          # Preview without sending
    python3 tools/send_weekly_movers.py --test me@test.com # Send test to one email
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras

# ── Config ──

RATING_ORDER = {"Outstanding": 1, "Good": 2, "Requires Improvement": 3, "Inadequate": 4}
UPGRADE_COLOR = "#4A5E45"  # moss
DOWNGRADE_COLOR = "#C44444"  # alert
BRAND_COLOR = "#C1784F"  # clay
APP_URL = os.environ.get("APP_URL", "https://caregist.co.uk")


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        from pathlib import Path
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
                    break
    return url


def is_upgrade(old: str, new: str) -> bool:
    return RATING_ORDER.get(new, 5) < RATING_ORDER.get(old, 5)


def postcode_area(postcode: str | None) -> str | None:
    """Extract postcode area (first 2-4 alpha chars) for matching."""
    if not postcode:
        return None
    pc = postcode.strip().upper().replace(" ", "")
    # Extract alpha prefix: "BH12" -> "BH", "SW1A" -> "SW", "M1" -> "M"
    area = ""
    for c in pc:
        if c.isalpha():
            area += c
        else:
            break
    return area if area else None


def match_changes_to_subscriber(changes: list[dict], subscriber_postcode: str | None) -> list[dict]:
    """Find changes near a subscriber's postcode. Returns matched changes."""
    if not subscriber_postcode:
        return []  # No postcode = no local matches

    sub_area = postcode_area(subscriber_postcode)
    if not sub_area:
        return []

    matched = []
    for c in changes:
        change_area = postcode_area(c["postcode"])
        if change_area and change_area == sub_area:
            matched.append(c)

    return matched


def national_highlights(changes: list[dict], limit: int = 5) -> tuple[list[dict], list[dict]]:
    """Pick top upgrades and downgrades nationally."""
    upgrades = [c for c in changes if is_upgrade(c["old_rating"], c["new_rating"])]
    downgrades = [c for c in changes if not is_upgrade(c["old_rating"], c["new_rating"])]
    return upgrades[:limit], downgrades[:limit]


def build_change_row(c: dict) -> str:
    upgraded = is_upgrade(c["old_rating"], c["new_rating"])
    arrow_color = UPGRADE_COLOR if upgraded else DOWNGRADE_COLOR
    arrow = "&#9650;" if upgraded else "&#9660;"
    return (
        f'<tr>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #E8E0D0">'
        f'<a href="{APP_URL}/provider/{c["slug"]}" style="color:#6B4C35;text-decoration:none;font-weight:600">{c["provider_name"]}</a>'
        f'<br><span style="color:#8a6a4a;font-size:12px">{c["town"] or ""}{", " + c["postcode"] if c["postcode"] else ""}</span>'
        f'</td>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #E8E0D0;text-align:center">{c["old_rating"]}</td>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #E8E0D0;text-align:center;color:{arrow_color};font-size:16px">{arrow}</td>'
        f'<td style="padding:8px 12px;border-bottom:1px solid #E8E0D0;text-align:center;font-weight:600;color:{arrow_color}">{c["new_rating"]}</td>'
        f'</tr>'
    )


def build_email_html(
    subscriber_email: str,
    local_changes: list[dict],
    national_upgrades: list[dict],
    national_downgrades: list[dict],
    postcode: str | None,
    total_changes: int,
) -> str:
    """Build the HTML email body."""

    # Header
    if local_changes:
        headline = f"{len(local_changes)} rating change{'s' if len(local_changes) != 1 else ''} near {postcode or 'you'} this week"
    else:
        headline = f"{total_changes} CQC rating changes across England this week"

    sections = []

    # Local changes
    if local_changes:
        rows = "".join(build_change_row(c) for c in local_changes)
        sections.append(
            f'<h2 style="color:#6B4C35;font-size:18px;margin:24px 0 12px">Near {postcode}</h2>'
            f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
            f'<tr style="background:#F5EFE4"><th style="padding:8px 12px;text-align:left">Provider</th>'
            f'<th style="padding:8px 12px;text-align:center">Was</th><th></th>'
            f'<th style="padding:8px 12px;text-align:center">Now</th></tr>'
            f'{rows}</table>'
        )

    # National highlights (always included)
    if national_upgrades:
        rows = "".join(build_change_row(c) for c in national_upgrades)
        sections.append(
            f'<h2 style="color:#6B4C35;font-size:18px;margin:24px 0 12px">{"Other upgrades" if local_changes else "Upgrades"} this week</h2>'
            f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
            f'<tr style="background:#F5EFE4"><th style="padding:8px 12px;text-align:left">Provider</th>'
            f'<th style="padding:8px 12px;text-align:center">Was</th><th></th>'
            f'<th style="padding:8px 12px;text-align:center">Now</th></tr>'
            f'{rows}</table>'
        )

    if national_downgrades:
        rows = "".join(build_change_row(c) for c in national_downgrades)
        sections.append(
            f'<h2 style="color:#6B4C35;font-size:18px;margin:24px 0 12px">{"Other downgrades" if local_changes else "Downgrades"} this week</h2>'
            f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
            f'<tr style="background:#F5EFE4"><th style="padding:8px 12px;text-align:left">Provider</th>'
            f'<th style="padding:8px 12px;text-align:center">Was</th><th></th>'
            f'<th style="padding:8px 12px;text-align:center">Now</th></tr>'
            f'{rows}</table>'
        )

    # No postcode prompt
    postcode_prompt = ""
    if not postcode:
        postcode_prompt = (
            f'<div style="background:#F5EFE4;border-radius:8px;padding:16px;margin:20px 0;text-align:center">'
            f'<p style="margin:0;font-size:14px;color:#6B4C35"><strong>Want local alerts?</strong> '
            f'<a href="{APP_URL}/find-care" style="color:{BRAND_COLOR}">Search by postcode</a> '
            f'to get changes near you.</p></div>'
        )

    # CTA
    cta = (
        f'<div style="background:#6B4C35;border-radius:8px;padding:20px;margin:24px 0;text-align:center">'
        f'<p style="color:#F5EFE4;margin:0 0 12px;font-size:14px">'
        f'Want instant alerts for specific providers? Monitor up to 25 care homes with Starter.</p>'
        f'<a href="{APP_URL}/pricing" style="display:inline-block;background:{BRAND_COLOR};color:white;'
        f'padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">'
        f'Upgrade to Starter — £39/mo</a></div>'
    )

    unsubscribe_url = f"{APP_URL}/api/v1/unsubscribe?email={subscriber_email}&source=weekly_movers"

    body = (
        f'<div style="max-width:600px;margin:0 auto;font-family:system-ui,sans-serif;color:#2B2520">'
        f'<div style="background:#6B4C35;padding:20px;text-align:center">'
        f'<a href="{APP_URL}" style="color:#D4943A;font-size:24px;font-weight:700;text-decoration:none">'
        f'CareGist</a></div>'
        f'<div style="padding:24px">'
        f'<h1 style="color:#6B4C35;font-size:22px;margin:0 0 8px">{headline}</h1>'
        f'<p style="color:#8a6a4a;font-size:13px;margin:0 0 20px">CQC rating changes for the week ending '
        f'{datetime.now().strftime("%d %B %Y")}</p>'
        f'{"".join(sections)}'
        f'{postcode_prompt}'
        f'{cta}'
        f'<p style="color:#8a6a4a;font-size:11px;margin:24px 0 0;border-top:1px solid #E8E0D0;padding-top:16px">'
        f'Contains CQC data. Crown copyright and database right.<br>'
        f'You received this because you subscribed on CareGist.<br>'
        f'<a href="{unsubscribe_url}" style="color:#8a6a4a">Unsubscribe</a></p>'
        f'</div></div>'
    )
    return body


def main():
    parser = argparse.ArgumentParser(description="Send weekly CQC movers digest")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    parser.add_argument("--test", metavar="EMAIL", help="Send a test email to this address only")
    parser.add_argument("--database-url", help="PostgreSQL connection URL")
    args = parser.parse_args()

    db_url = args.database_url or get_database_url()
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return 1

    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Idempotency: check if we already sent this week
    week_key = datetime.now(timezone.utc).strftime("%Y-W%W")
    cur.execute("SELECT id FROM weekly_digest_log WHERE week_key = %s", (week_key,))
    if cur.fetchone() and not args.dry_run and not args.test:
        print(f"Already sent digest for {week_key}. Skipping.")
        conn.close()
        return 0

    # Get rating changes from last 7 days
    since = datetime.now(timezone.utc) - timedelta(days=7)
    cur.execute(
        "SELECT * FROM rating_changes WHERE detected_at >= %s ORDER BY detected_at DESC",
        (since,),
    )
    changes = [dict(r) for r in cur.fetchall()]
    print(f"Found {len(changes)} rating changes in the last 7 days")

    if not changes and not args.test:
        print("No rating changes this week. Skipping digest.")
        # Log that we checked
        if not args.dry_run:
            cur.execute(
                "INSERT INTO weekly_digest_log (week_key, changes_count) VALUES (%s, 0) ON CONFLICT DO NOTHING",
                (week_key,),
            )
            conn.commit()
        conn.close()
        return 0

    # National highlights
    nat_upgrades, nat_downgrades = national_highlights(changes)

    # Get active subscribers
    if args.test:
        subscribers = [{"email": args.test, "postcode": "BH1", "source": "test"}]
    else:
        cur.execute(
            "SELECT email, postcode, source FROM email_subscribers WHERE unsubscribed_at IS NULL"
        )
        subscribers = [dict(r) for r in cur.fetchall()]

    # Deduplicate by email (a user might have multiple source entries)
    seen_emails = set()
    unique_subs = []
    for s in subscribers:
        if s["email"] not in seen_emails:
            seen_emails.add(s["email"])
            unique_subs.append(s)
    subscribers = unique_subs

    print(f"Sending to {len(subscribers)} subscribers")

    emails_queued = 0
    stagger_seconds = 0

    for sub in subscribers:
        local = match_changes_to_subscriber(changes, sub.get("postcode"))

        # Build email
        html = build_email_html(
            subscriber_email=sub["email"],
            local_changes=local,
            national_upgrades=nat_upgrades if not local else nat_upgrades[:3],
            national_downgrades=nat_downgrades if not local else nat_downgrades[:3],
            postcode=sub.get("postcode"),
            total_changes=len(changes),
        )

        subject = (
            f"{len(local)} rating change{'s' if len(local) != 1 else ''} near {sub.get('postcode', 'you')}"
            if local
            else f"{len(changes)} CQC rating changes this week"
        )

        if args.dry_run:
            print(f"  [DRY RUN] Would send to {sub['email']} — {subject}")
            if sub == subscribers[0]:
                # Write first email to file for preview
                with open("/tmp/movers_preview.html", "w") as f:
                    f.write(html)
                print(f"  Preview saved to /tmp/movers_preview.html")
        else:
            # Stagger sends by 2 seconds each to avoid Resend rate limits
            send_after = datetime.now(timezone.utc) + timedelta(seconds=stagger_seconds)
            cur.execute(
                """INSERT INTO pending_emails (to_email, subject, html_body, send_after)
                   VALUES (%s, %s, %s, %s)""",
                (sub["email"], subject, html, send_after),
            )
            stagger_seconds += 2
            emails_queued += 1

    if not args.dry_run:
        # Log this week's send
        cur.execute(
            """INSERT INTO weekly_digest_log (week_key, subscriber_count, emails_queued, changes_count)
               VALUES (%s, %s, %s, %s) ON CONFLICT (week_key) DO NOTHING""",
            (week_key, len(subscribers), emails_queued, len(changes)),
        )
        conn.commit()

    print(f"Done. Queued {emails_queued} emails for {week_key}.")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
