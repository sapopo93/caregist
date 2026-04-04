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


RATING_COLORS = {
    "Outstanding": "#4A5E45",
    "Good": "#D4943A",
    "Requires Improvement": "#C44444",
    "Inadequate": "#8B0000",
    "Not Yet Inspected": "#8a6a4a",
}


def rating_pill(rating: str) -> str:
    """Render a coloured rating pill for email."""
    color = RATING_COLORS.get(rating, "#8a6a4a")
    return (
        f'<span style="display:inline-block;background:{color};color:white;padding:3px 10px;'
        f'border-radius:12px;font-size:12px;font-weight:600">{rating}</span>'
    )


def quality_bar(score: int | float, width: int = 120) -> str:
    """Render an inline quality score bar for email."""
    pct = min(max(int(score), 0), 100)
    fill_color = "#4A5E45" if pct >= 80 else "#D4943A" if pct >= 60 else "#C44444"
    return (
        f'<div style="display:inline-block;width:{width}px;vertical-align:middle">'
        f'<div style="background:#E8E0D0;border-radius:6px;height:10px;width:100%">'
        f'<div style="background:{fill_color};border-radius:6px;height:10px;width:{pct}%"></div>'
        f'</div></div>'
        f'<span style="font-weight:700;color:#6B4C35;font-size:13px;margin-left:6px">{pct}/100</span>'
    )


def fetch_spotlight(cur, postcode_area: str | None) -> dict | None:
    """Find the highest-quality provider near subscriber's postcode."""
    if postcode_area:
        cur.execute(
            """SELECT name, slug, town, postcode, overall_rating, quality_score, service_types, number_of_beds
               FROM care_providers
               WHERE postcode ILIKE %s AND overall_rating IN ('Outstanding', 'Good')
                 AND quality_score IS NOT NULL
               ORDER BY quality_score DESC
               LIMIT 1""",
            (postcode_area + "%",),
        )
    else:
        cur.execute(
            """SELECT name, slug, town, postcode, overall_rating, quality_score, service_types, number_of_beds
               FROM care_providers
               WHERE overall_rating = 'Outstanding' AND quality_score IS NOT NULL
               ORDER BY quality_score DESC
               LIMIT 1"""
        )
    row = cur.fetchone()
    return dict(row) if row else None


def fetch_stale_providers(cur, postcode_area: str | None, limit: int = 3) -> list[dict]:
    """Find providers near subscriber that haven't been inspected in 2+ years."""
    if postcode_area:
        cur.execute(
            """SELECT name, slug, town, postcode, overall_rating, last_inspection_date,
                      EXTRACT(DAY FROM NOW() - last_inspection_date)::int as days_since
               FROM care_providers
               WHERE postcode ILIKE %s
                 AND last_inspection_date < NOW() - INTERVAL '2 years'
                 AND last_inspection_date IS NOT NULL
               ORDER BY last_inspection_date ASC
               LIMIT %s""",
            (postcode_area + "%", limit),
        )
    else:
        cur.execute(
            """SELECT name, slug, town, postcode, overall_rating, last_inspection_date,
                      EXTRACT(DAY FROM NOW() - last_inspection_date)::int as days_since
               FROM care_providers
               WHERE last_inspection_date < NOW() - INTERVAL '3 years'
                 AND last_inspection_date IS NOT NULL
               ORDER BY last_inspection_date ASC
               LIMIT %s""",
            (limit,),
        )
    return [dict(r) for r in cur.fetchall()]


def build_change_row(c: dict) -> str:
    upgraded = is_upgrade(c["old_rating"], c["new_rating"])
    arrow_color = UPGRADE_COLOR if upgraded else DOWNGRADE_COLOR
    arrow = "&#9650;" if upgraded else "&#9660;"
    return (
        f'<tr>'
        f'<td style="padding:10px 12px;border-bottom:1px solid #E8E0D0">'
        f'<a href="{APP_URL}/provider/{c["slug"]}" style="color:#6B4C35;text-decoration:none;font-weight:600">{c["provider_name"]}</a>'
        f'<br><span style="color:#8a6a4a;font-size:11px">{c["town"] or ""}{", " + c["postcode"] if c["postcode"] else ""}</span>'
        f'</td>'
        f'<td style="padding:10px 8px;border-bottom:1px solid #E8E0D0;text-align:center">{rating_pill(c["old_rating"])}</td>'
        f'<td style="padding:10px 4px;border-bottom:1px solid #E8E0D0;text-align:center;color:{arrow_color};font-size:18px">{arrow}</td>'
        f'<td style="padding:10px 8px;border-bottom:1px solid #E8E0D0;text-align:center">{rating_pill(c["new_rating"])}</td>'
        f'</tr>'
    )


def build_email_html(
    subscriber_email: str,
    local_changes: list[dict],
    national_upgrades: list[dict],
    national_downgrades: list[dict],
    postcode: str | None,
    total_changes: int,
    spotlight: dict | None = None,
    stale_providers: list[dict] | None = None,
) -> str:
    """Build the HTML email body with visual rating pills, spotlight, and stale alerts."""

    # Header
    if local_changes:
        headline = f"{len(local_changes)} rating change{'s' if len(local_changes) != 1 else ''} near {postcode or 'you'} this week"
    else:
        headline = f"{total_changes} CQC rating changes across England this week"

    sections = []

    # ── Local changes ──
    if local_changes:
        rows = "".join(build_change_row(c) for c in local_changes)
        sections.append(
            f'<h2 style="color:#6B4C35;font-size:18px;margin:24px 0 12px">'
            f'<span style="display:inline-block;width:8px;height:8px;background:#D4943A;border-radius:50%;margin-right:8px"></span>'
            f'Near {postcode}</h2>'
            f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
            f'<tr style="background:#F5EFE4"><th style="padding:8px 12px;text-align:left">Provider</th>'
            f'<th style="padding:8px 12px;text-align:center">Was</th><th></th>'
            f'<th style="padding:8px 12px;text-align:center">Now</th></tr>'
            f'{rows}</table>'
        )

    # ── National highlights ──
    if national_upgrades:
        rows = "".join(build_change_row(c) for c in national_upgrades)
        sections.append(
            f'<h2 style="color:#4A5E45;font-size:18px;margin:24px 0 12px">'
            f'<span style="display:inline-block;width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;'
            f'border-bottom:10px solid #4A5E45;margin-right:8px;vertical-align:middle"></span>'
            f'{"Other upgrades" if local_changes else "Upgrades"} this week</h2>'
            f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
            f'<tr style="background:#F5EFE4"><th style="padding:8px 12px;text-align:left">Provider</th>'
            f'<th style="padding:8px 12px;text-align:center">Was</th><th></th>'
            f'<th style="padding:8px 12px;text-align:center">Now</th></tr>'
            f'{rows}</table>'
        )

    if national_downgrades:
        rows = "".join(build_change_row(c) for c in national_downgrades)
        sections.append(
            f'<h2 style="color:#C44444;font-size:18px;margin:24px 0 12px">'
            f'<span style="display:inline-block;width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;'
            f'border-top:10px solid #C44444;margin-right:8px;vertical-align:middle"></span>'
            f'{"Other downgrades" if local_changes else "Downgrades"} this week</h2>'
            f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
            f'<tr style="background:#F5EFE4"><th style="padding:8px 12px;text-align:left">Provider</th>'
            f'<th style="padding:8px 12px;text-align:center">Was</th><th></th>'
            f'<th style="padding:8px 12px;text-align:center">Now</th></tr>'
            f'{rows}</table>'
        )

    # ── Provider Spotlight ──
    spotlight_html = ""
    if spotlight:
        svc = (spotlight.get("service_types") or "").split("|")[0] or "Care provider"
        beds_text = f" &middot; {spotlight['number_of_beds']} beds" if spotlight.get("number_of_beds") else ""
        spotlight_html = (
            f'<div style="background:linear-gradient(135deg,#F5EFE4 0%,#FDFAF5 100%);border:2px solid #D4943A;border-radius:12px;padding:20px;margin:24px 0">'
            f'<table style="width:100%"><tr>'
            f'<td style="vertical-align:top">'
            f'<p style="color:#D4943A;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin:0 0 6px">&#9733; Provider Spotlight</p>'
            f'<a href="{APP_URL}/provider/{spotlight["slug"]}" style="color:#6B4C35;font-size:18px;font-weight:700;text-decoration:none">{spotlight["name"]}</a>'
            f'<p style="color:#8a6a4a;font-size:13px;margin:4px 0">{spotlight.get("town", "")}{", " + spotlight["postcode"] if spotlight.get("postcode") else ""}'
            f' &middot; {svc}{beds_text}</p>'
            f'<div style="margin-top:8px">{rating_pill(spotlight.get("overall_rating", ""))}'
            f'<span style="margin-left:12px">{quality_bar(spotlight.get("quality_score", 0))}</span></div>'
            f'</td></tr></table>'
            f'<a href="{APP_URL}/provider/{spotlight["slug"]}" style="display:inline-block;margin-top:12px;'
            f'color:{BRAND_COLOR};font-size:13px;font-weight:600;text-decoration:none">View full profile &rarr;</a>'
            f'</div>'
        )

    # ── Longest Without Inspection ──
    stale_html = ""
    if stale_providers:
        stale_rows = ""
        for s in stale_providers:
            years = round(s["days_since"] / 365, 1)
            bar_color = "#C44444" if years >= 3 else "#D4943A"
            bar_width = min(int(years / 5 * 100), 100)
            stale_rows += (
                f'<tr>'
                f'<td style="padding:8px 12px;border-bottom:1px solid #E8E0D0">'
                f'<a href="{APP_URL}/provider/{s["slug"]}" style="color:#6B4C35;text-decoration:none;font-weight:600">{s["name"]}</a>'
                f'<br><span style="color:#8a6a4a;font-size:11px">{s.get("town", "")}</span>'
                f'</td>'
                f'<td style="padding:8px 12px;border-bottom:1px solid #E8E0D0;text-align:center">{rating_pill(s.get("overall_rating", ""))}</td>'
                f'<td style="padding:8px 12px;border-bottom:1px solid #E8E0D0">'
                f'<div style="background:#E8E0D0;border-radius:4px;height:8px;width:80px;display:inline-block;vertical-align:middle">'
                f'<div style="background:{bar_color};border-radius:4px;height:8px;width:{bar_width}%"></div></div>'
                f'<span style="font-size:12px;color:{bar_color};font-weight:600;margin-left:6px">{years} yrs</span>'
                f'</td></tr>'
            )
        stale_html = (
            f'<div style="margin:24px 0">'
            f'<h2 style="color:#C44444;font-size:18px;margin:0 0 12px">'
            f'<span style="font-size:16px;margin-right:6px">&#9888;</span>'
            f'Longest without inspection{" near " + postcode if postcode else ""}</h2>'
            f'<p style="color:#8a6a4a;font-size:13px;margin:0 0 12px">These providers haven\'t been inspected in over 2 years. '
            f'Their rating may not reflect current performance.</p>'
            f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
            f'<tr style="background:#F5EFE4">'
            f'<th style="padding:8px 12px;text-align:left">Provider</th>'
            f'<th style="padding:8px 12px;text-align:center">Rating</th>'
            f'<th style="padding:8px 12px;text-align:left">Since inspection</th></tr>'
            f'{stale_rows}</table></div>'
        )

    # ── No postcode prompt ──
    postcode_prompt = ""
    if not postcode:
        postcode_prompt = (
            f'<div style="background:#F5EFE4;border-radius:8px;padding:16px;margin:20px 0;text-align:center">'
            f'<p style="margin:0;font-size:14px;color:#6B4C35"><strong>Want local alerts?</strong> '
            f'<a href="{APP_URL}/find-care" style="color:{BRAND_COLOR}">Search by postcode</a> '
            f'to get changes near you.</p></div>'
        )

    # ── CTA ──
    cta = (
        f'<div style="background:#6B4C35;border-radius:12px;padding:24px;margin:24px 0;text-align:center">'
        f'<p style="color:#F5EFE4;margin:0 0 4px;font-size:16px;font-weight:700">'
        f'Monitor specific providers</p>'
        f'<p style="color:#D6CFC4;margin:0 0 16px;font-size:13px">'
        f'Get instant alerts when your watched providers change rating. Track up to 25 care homes.</p>'
        f'<a href="{APP_URL}/pricing" style="display:inline-block;background:{BRAND_COLOR};color:white;'
        f'padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">'
        f'Upgrade to Starter &mdash; &pound;39/mo</a></div>'
    )

    unsubscribe_url = f"{APP_URL}/api/v1/unsubscribe?email={subscriber_email}&source=weekly_movers"

    body = (
        f'<div style="max-width:600px;margin:0 auto;font-family:system-ui,-apple-system,sans-serif;color:#2B2520;background:#FDFAF5">'
        # Header
        f'<div style="background:#6B4C35;padding:24px;text-align:center">'
        f'<a href="{APP_URL}" style="color:#D4943A;font-size:26px;font-weight:700;text-decoration:none;letter-spacing:-0.5px">'
        f'CareGist</a>'
        f'<p style="color:#D6CFC4;font-size:12px;margin:4px 0 0">Weekly CQC Intelligence</p>'
        f'</div>'
        # Body
        f'<div style="padding:24px">'
        f'<h1 style="color:#6B4C35;font-size:22px;margin:0 0 4px">{headline}</h1>'
        f'<p style="color:#8a6a4a;font-size:13px;margin:0 0 20px">Week ending '
        f'{datetime.now().strftime("%d %B %Y")}</p>'
        # Rating changes
        f'{"".join(sections)}'
        # Spotlight
        f'{spotlight_html}'
        # Stale providers
        f'{stale_html}'
        # Postcode prompt
        f'{postcode_prompt}'
        # CTA
        f'{cta}'
        # Footer
        f'<div style="margin:24px 0 0;border-top:1px solid #E8E0D0;padding-top:16px">'
        f'<p style="color:#8a6a4a;font-size:11px;margin:0">'
        f'Contains CQC data &copy; Crown copyright and database right.<br>'
        f'You received this because you subscribed to weekly CQC alerts on CareGist.<br>'
        f'<a href="{unsubscribe_url}" style="color:#8a6a4a">Unsubscribe</a> &middot; '
        f'<a href="{APP_URL}/cookies" style="color:#8a6a4a">Privacy</a></p>'
        f'</div></div></div>'
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

    # Even with zero changes, we still send spotlight + stale content
    # Only skip if truly nothing to show (no changes AND test mode wasn't requested)
    if not changes:
        print("No rating changes this week — will send spotlight + stale content only.")

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
        sub_area = postcode_area(sub.get("postcode"))

        # Fetch spotlight and stale providers for this subscriber's area
        spotlight = fetch_spotlight(cur, sub_area)
        stale = fetch_stale_providers(cur, sub_area)

        # Build email
        html = build_email_html(
            subscriber_email=sub["email"],
            local_changes=local,
            national_upgrades=nat_upgrades if not local else nat_upgrades[:3],
            national_downgrades=nat_downgrades if not local else nat_downgrades[:3],
            postcode=sub.get("postcode"),
            total_changes=len(changes),
            spotlight=spotlight,
            stale_providers=stale,
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
