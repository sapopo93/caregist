#!/usr/bin/env python3
"""Nightly off-peak CQC-vs-database reconciliation check.

Answers one question every night: does this database still match CQC, and what
changed? Runs read-only. It never writes to the database; the only side effects
are the report and the small baseline file under --out-dir.

Design notes
------------
* The session is opened read-only, so a bug in this script cannot mutate
  production. The reconciliation *write* path lives in
  `tools/run_cqc_reconciliation.py` and stays a separate, deliberate act.
* Substantive change comes from `trusted_event_ledger` only. `care_providers.updated_at`
  is refreshed by every rolling sweep, so it is reported separately and labelled
  as churn -- see artifacts/audits/2026-08-10-cqc-database-change-frequency-report.md.
* `old_value` / `new_value` are json columns: SQL `IS NULL` is the wrong test for
  them, because a JSON null is not a SQL NULL. They are compared as `::text`.
* stdout is the delivery contract for the scheduled job: empty means "nothing to
  report". A Sunday heartbeat proves the job itself is still alive.
* A rolling 24h window almost always contains *some* ledger event, so gating
  stdout on `changes_total` alone means it fires nightly regardless of whether
  anything is wrong or unusual -- that defeats the point of an anomaly report.
  The gate instead fires on genuine `anomalies()` findings, a new CQC source
  snapshot, or nightly change volume that swings materially versus the
  previous run (see CHANGE_VOLUME_MATERIAL_PCT) -- see
  artifacts/cqc-nightly/ for the 2026-09 fix that corrected this.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2

REPO_ROOT = Path(__file__).resolve().parents[1]
FRESHNESS_SLA = timedelta(days=8)          # api/services/cqc_freshness.py
REQUIRED_WEEKLY_POLLS = 336                # 48/day x 7, per cqc-signal-poll.yml
MATCH_TOLERANCE = 25                       # active-set drift worth alerting on
CHANGE_VOLUME_MATERIAL_PCT = 0.5            # >=50% swing in nightly change volume vs previous run
CHANGE_VOLUME_MATERIAL_FLOOR = 20           # ignore swings below this absolute count (noise on quiet nights)
EVENT_TYPES = (
    "new_registration",
    "rating_changed",
    "status_changed",
    "ownership_changed",
    "group_movement",
)
NULL_JSON = "null"                         # what a json null renders as under ::text


def connect_readonly():
    """Read-only connection. Refuses to run without a usable URL."""
    sys.path.insert(0, str(REPO_ROOT))
    from incremental_update import get_database_url  # noqa: PLC0415 - repo helper

    url = get_database_url()
    if not url:
        raise RuntimeError("no DATABASE_URL in environment or .env")
    conn = psycopg2.connect(url)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def scalar(cur, sql, params=None):
    cur.execute(sql, params or ())
    row = cur.fetchone()
    return row[0] if row else None


def rows(cur, sql, params=None):
    cur.execute(sql, params or ())
    return cur.fetchall()


def gather(conn, window_hours: int) -> dict:
    """Collect every figure the report needs. Read-only throughout."""
    cur = conn.cursor()
    since = datetime.now(UTC) - timedelta(hours=window_hours)
    data: dict = {"window_hours": window_hours, "since": since.isoformat()}

    # ---- 1. does the database match CQC? -------------------------------
    status_rows = rows(cur, "SELECT status, count(*) FROM care_providers GROUP BY 1 ORDER BY 2 DESC")
    data["provider_status"] = {str(s): int(c) for s, c in status_rows}
    data["providers_total"] = sum(data["provider_status"].values())
    data["providers_active"] = int(
        scalar(cur, "SELECT count(*) FROM care_providers WHERE upper(status) = 'ACTIVE'") or 0
    )

    wm = rows(
        cur,
        """SELECT reconciled_at, source_total_count, checked_count, status
             FROM pipeline_runs
            WHERE counts_reconciled IS TRUE
            ORDER BY reconciled_at DESC LIMIT 1""",
    )
    if wm:
        reconciled_at, source_total, checked, status = wm[0]
        data["watermark"] = {
            "reconciled_at": reconciled_at.isoformat(),
            "source_total_count": source_total,
            "checked_count": checked,
            "status": status,
            "age_hours": round((datetime.now(UTC) - reconciled_at).total_seconds() / 3600, 1),
        }
        data["watermark"]["counts_match"] = source_total == checked
        # The directory snapshot is the authority for the ACTIVE set, so compare
        # it against our ACTIVE rows. Our table also retains INACTIVE rows, which
        # is why the totals are not compared directly.
        data["match"] = {
            "ours": data["providers_active"],
            "source_total": int(source_total or 0),
            "delta": data["providers_active"] - int(source_total or 0),
        }

    snaps = rows(
        cur,
        """SELECT source_type, checksum_sha256, record_count, source_checked_at
             FROM source_snapshots
            ORDER BY source_checked_at DESC LIMIT 5""",
    )
    data["snapshots"] = [
        {
            "source_type": s,
            "checksum_sha256": c,
            "record_count": int(n or 0),
            "source_checked_at": t.isoformat(),
            "age_hours": round((datetime.now(UTC) - t).total_seconds() / 3600, 1),
        }
        for s, c, n, t in snaps
    ]

    # ---- 2. what changed in the window --------------------------------
    data["changes_by_type"] = {
        str(et): int(n)
        for et, n in rows(
            cur,
            """SELECT event_type, count(*) FROM trusted_event_ledger
                WHERE observed_at >= %s GROUP BY 1 ORDER BY 2 DESC""",
            (since,),
        )
    }
    data["changes_total"] = sum(data["changes_by_type"].values())

    # Rating movement needs an ordinal, not a text compare: 'Good' < 'Outstanding'
    # alphabetically but ranks higher than 'Requires improvement'. A missing
    # destination rating is reported as such, never folded into "unchanged".
    data["rating_moves"] = {
        str(k): int(n)
        for k, n in rows(
            cur,
            """WITH r AS (
                   SELECT old_rating, new_rating,
                          CASE old_rating WHEN 'Outstanding' THEN 4 WHEN 'Good' THEN 3
                                          WHEN 'Requires improvement' THEN 2
                                          WHEN 'Inadequate' THEN 1 END AS o,
                          CASE new_rating WHEN 'Outstanding' THEN 4 WHEN 'Good' THEN 3
                                          WHEN 'Requires improvement' THEN 2
                                          WHEN 'Inadequate' THEN 1 END AS n
                     FROM rating_changes WHERE detected_at >= %s
               )
               SELECT CASE
                        WHEN new_rating IS NULL OR new_rating = '' THEN 'no destination rating'
                        WHEN o IS NULL OR n IS NULL THEN 'unrankable'
                        WHEN n > o THEN 'up'
                        WHEN n < o THEN 'down'
                        ELSE 'flat' END,
                      count(*)
                 FROM r GROUP BY 1 ORDER BY 2 DESC""",
            (since,),
        )
    }
    data["status_transitions"] = {
        f"{a}->{b}": int(n)
        for a, b, n in rows(
            cur,
            """SELECT trim(both '"' from coalesce(old_value::text, '?')),
                      trim(both '"' from coalesce(new_value::text, '?')), count(*)
                 FROM trusted_event_ledger
                WHERE observed_at >= %s AND event_type = 'status_changed'
                GROUP BY 1,2 ORDER BY 3 DESC LIMIT 6""",
            (since,),
        )
    }
    win_nulls, win_total = rows(
        cur,
        """SELECT count(*) FILTER (WHERE new_value::text = %s), count(*)
             FROM trusted_event_ledger
            WHERE event_type = 'rating_changed' AND observed_at >= %s""",
        (NULL_JSON, since),
    )[0]
    all_nulls, all_total = rows(
        cur,
        """SELECT count(*) FILTER (WHERE new_value::text = %s), count(*)
             FROM trusted_event_ledger WHERE event_type = 'rating_changed'""",
        (NULL_JSON,),
    )[0]
    data["rating_destination"] = {
        "window_no_destination": int(win_nulls),
        "window_total": int(win_total),
        "all_time_no_destination": int(all_nulls),
        "all_time_total": int(all_total),
        "window_share": round(int(win_nulls) / int(win_total), 2) if int(win_total) else 0.0,
    }
    newest = scalar(cur, "SELECT max(observed_at) FROM trusted_event_ledger")
    if newest:
        data["ledger_newest"] = newest.isoformat()
        data["ledger_newest_age_hours"] = round((datetime.now(UTC) - newest).total_seconds() / 3600, 1)

    # ---- 3. pipeline health -------------------------------------------
    polls_total, polls_done = rows(
        cur,
        """SELECT count(*), count(*) FILTER (WHERE status = 'completed')
             FROM pipeline_runs
            WHERE run_type = 'signal_poll' AND started_at > now() - interval '7 days'""",
    )[0]
    data["polls_7d"] = {"total": int(polls_total), "completed": int(polls_done), "required": REQUIRED_WEEKLY_POLLS}
    data["polls_24h"] = int(
        scalar(cur, "SELECT count(*) FROM pipeline_runs WHERE run_type = 'signal_poll'"
                   " AND status = 'completed' AND started_at > now() - interval '24 hours'") or 0
    )
    data["runs_by_type"] = {
        f"{rt}/{st}": int(n)
        for rt, st, n in rows(
            cur,
            """SELECT run_type, status, count(*) FROM pipeline_runs
                WHERE started_at > now() - interval '7 days' GROUP BY 1,2 ORDER BY 3 DESC""",
        )
    }
    data["recent_failures"] = [
        {"run_type": rt, "started_at": ts.isoformat(), "error": (err or "")[:160]}
        for rt, ts, err in rows(
            cur,
            """SELECT run_type, started_at, error_message FROM pipeline_runs
                WHERE status NOT IN ('completed','running') AND started_at > now() - interval '7 days'
                ORDER BY started_at DESC LIMIT 5""",
        )
    ]
    # Alert only on failures inside the window; the 7-day list is reported but
    # must not nag. A standing fact is not news.
    data["failures_in_window"] = [
        {"run_type": rt, "started_at": ts.isoformat()}
        for rt, ts in rows(
            cur,
            "SELECT run_type, started_at FROM pipeline_runs"
            " WHERE status NOT IN ('completed','running')"
            " AND started_at > now() - make_interval(hours => %s)"
            " ORDER BY started_at DESC LIMIT 10",
            (window_hours,),
        )
    ]

    # ---- 4. data quality ---------------------------------------------
    total = data["providers_total"] or 1
    blanks = rows(
        cur,
        """SELECT
             count(*) FILTER (WHERE postcode IS NULL OR postcode = ''),
             count(*) FILTER (WHERE region IS NULL OR region = ''),
             count(*) FILTER (WHERE local_authority IS NULL OR local_authority = ''),
             count(*) FILTER (WHERE overall_rating IS NULL OR overall_rating = ''),
             count(*) FILTER (WHERE latitude IS NULL)
           FROM care_providers""",
    )[0]
    data["quality_gaps"] = {
        name: {"count": int(n), "pct": round(100.0 * int(n) / total, 1)}
        for name, n in zip(
            ("no_postcode", "no_region", "no_local_authority", "no_overall_rating", "no_geocode"),
            blanks,
            strict=True,
        )
    }
    active_total = data["providers_active"] or 1
    active_unrated = int(
        scalar(
            cur,
            """SELECT count(*) FROM care_providers
                WHERE upper(status) = 'ACTIVE' AND (overall_rating IS NULL OR overall_rating = '')""",
        )
        or 0
    )
    data["active_unrated"] = {
        "count": active_unrated,
        "pct": round(100.0 * active_unrated / active_total, 1),
    }

    # ---- 5. refresh churn, labelled as churn, never as change ----------
    data["churn_updated_at_24h"] = int(
        scalar(
            cur,
            "SELECT count(*) FROM care_providers WHERE updated_at > now() - interval '24 hours'",
        )
        or 0
    )
    cur.close()
    return data


def live_index_diff(conn) -> dict:
    """Fetch CQC's authoritative location id set and diff it against ours."""
    sys.path.insert(0, str(REPO_ROOT))
    from incremental_update import (  # noqa: PLC0415 - repo helpers
        DEFAULT_BASE_URL,
        _fetch_all_cqc_location_stubs,
        get_api_key,
    )

    api_key = get_api_key()
    if not api_key:
        return {"status": "skipped", "reason": "no CQC API key in environment or .env"}
    started = time.time()
    try:
        stubs = _fetch_all_cqc_location_stubs(DEFAULT_BASE_URL, api_key, 0.1)
    except Exception as exc:  # noqa: BLE001 - report, never crash the nightly run
        return {"status": "failed", "reason": f"{type(exc).__name__}: {str(exc)[:140]}"}
    cqc_ids = {str(s.get("locationId")) for s in stubs if s.get("locationId")}
    cur = conn.cursor()
    ours = int(scalar(cur, "SELECT count(*) FROM care_providers") or 0)
    cur.close()
    # Informational only. This index is unfiltered: it carries locations outside
    # our scope (deregistered, service types we do not hold), so a set difference
    # against it is NOT a match signal and is deliberately not reported as one.
    return {
        "status": "ok",
        "comparable": False,
        "cqc_api_locations": len(cqc_ids),
        "our_rows": ours,
        "fetched_in_s": round(time.time() - started, 1),
        "note": "unfiltered CQC /locations index; the active directory snapshot is the comparison authority",
    }


def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def save_state(path: Path, state: dict) -> None:
    """Atomic write, 0600: this holds operational counts, not secrets."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.chmod(0o600)
    tmp.replace(path)


def anomalies(data: dict, diff: dict | None, previous: dict | None = None) -> list[str]:
    """Reasons this night deserves a message, even if nothing changed.

    Promise failures alert nightly. Standing facts are reported but alerted
    only when they move, because nagging about a known state gets ignored.
    """
    out = []
    prev = previous or {}
    wm = data.get("watermark")
    if not wm:
        out.append("no reconciliation watermark: the database has never been reconciled against CQC")
    elif wm["age_hours"] > FRESHNESS_SLA.total_seconds() / 3600:
        out.append(f"reconciliation is stale: {wm['age_hours']}h old (SLA 192h)")
    elif not wm["counts_match"]:
        out.append(f"reconciliation counts disagree: source {wm['source_total_count']} vs checked {wm['checked_count']}")
    if not data.get("polls_24h"):
        out.append("no CQC signal poll completed in the last 24h")
    if data.get("ledger_newest_age_hours", 0) > FRESHNESS_SLA.total_seconds() / 3600:
        out.append(f"no new CQC signal observed for {data.get('ledger_newest_age_hours')}h")
    for failure in data["failures_in_window"]:
        out.append(f"pipeline failure: {failure['run_type']} at {failure['started_at'][:16]}Z")
    dest = data["rating_destination"]
    if dest["window_share"] > 0.5 and prev.get("rating_no_destination_share") != dest["window_share"]:
        share = round(100.0 * dest["all_time_no_destination"] / max(dest["all_time_total"], 1), 1)
        out.append(
            f"rating_changed events carry no destination rating: "
            f"{dest['window_no_destination']}/{dest['window_total']} in this window, {share}% all time - "
            "the event records that a rating moved but not what it moved to"
        )
    if diff and diff.get("status") == "failed":
        out.append(f"CQC API inventory probe failed: {diff['reason']}")
    match = data.get("match")
    if match and abs(match["delta"]) > MATCH_TOLERANCE and prev.get("match_delta") != match["delta"]:
        out.append(
            f"active-set mismatch: {match['ours']:,} ACTIVE rows vs {match['source_total']:,} "
            f"in the CQC directory snapshot ({match['delta']:+,})"
        )
    prev_changes = prev.get("changes_total")
    cur_changes = data["changes_total"]
    if prev_changes is not None:
        swing = abs(cur_changes - prev_changes)
        if swing >= CHANGE_VOLUME_MATERIAL_FLOOR and swing >= CHANGE_VOLUME_MATERIAL_PCT * max(prev_changes, 1):
            out.append(
                f"nightly change volume swung materially: {cur_changes:,} events vs "
                f"{prev_changes:,} in the previous run ({cur_changes - prev_changes:+,})"
            )
    return out


def render(data: dict, diff: dict | None, previous: dict) -> str:
    now = datetime.now(UTC)
    lines = [
        f"# CareGist nightly CQC check - {now:%Y-%m-%d %H:%M} UTC",
        "",
        f"Window: last {data['window_hours']}h. Read-only. "
        f"All change counts come from `trusted_event_ledger`.",
        "",
        "## Does the database match CQC?",
        "",
        f"- `care_providers` rows: **{data['providers_total']:,}** ("
        + ", ".join(f"{k} {v:,}" for k, v in data["provider_status"].items())
        + ")",
    ]
    wm = data.get("watermark")
    if wm:
        lines.append(
            f"- Last reconciled: **{wm['reconciled_at'][:16]}Z** ({wm['age_hours']}h ago, SLA 192h) - "
            f"source {wm['source_total_count']:,} vs checked {wm['checked_count']:,}"
            + (" - counts agree" if wm["counts_match"] else " - **MISMATCH**")
        )
    else:
        lines.append("- Last reconciled: **never** - no `counts_reconciled` run exists")
    if previous.get("providers_total") is not None:
        delta = data["providers_total"] - previous["providers_total"]
        lines.append(f"- Since previous run: {delta:+,} rows")
    match = data.get("match")
    if match:
        lines.append(
            f"- ACTIVE rows vs CQC directory snapshot: {match['ours']:,} vs {match['source_total']:,} "
            f"({match['delta']:+,})"
        )
    if data.get("snapshot_changed"):
        lines.append("- **CQC published a new source snapshot** since the previous run (checksum changed)")
    if diff:
        if diff["status"] == "ok":
            lines.append(
                f"- CQC API inventory probe (informational, not a match signal): "
                f"{diff['cqc_api_locations']:,} locations in the unfiltered /locations index vs our "
                f"{diff['our_rows']:,} rows (fetched in {diff['fetched_in_s']}s)"
            )
        else:
            lines.append(f"- CQC API inventory probe: not run ({diff['status']}: {diff.get('reason', '')})")
    lines += ["", f"## What changed ({data['changes_total']:,} events)", ""]
    if data["changes_total"]:
        for etype in EVENT_TYPES:
            if data["changes_by_type"].get(etype):
                lines.append(f"- {etype.replace('_', ' ')}: **{data['changes_by_type'][etype]:,}**")
    else:
        lines.append("- No substantive CQC changes observed in this window.")
    if data["rating_moves"]:
        moves = ", ".join(f"{k} {v:,}" for k, v in data["rating_moves"].items())
        dest = data["rating_destination"]
        share = round(100.0 * dest["all_time_no_destination"] / max(dest["all_time_total"], 1), 1)
        lines.append(f"- rating movement: {moves} ({share}% of all rating_changed events lack a destination rating)")
    if data["status_transitions"]:
        trans = ", ".join(f"{k} {v:,}" for k, v in data["status_transitions"].items())
        lines.append(f"- status transitions: {trans}")

    lines += [
        "",
        "## Freshness and pipeline health",
        "",
        f"- Newest CQC signal observed: {data.get('ledger_newest', 'n/a')[:16]}Z "
        f"({data.get('ledger_newest_age_hours', 'n/a')}h ago, SLA 192h)",
        f"- Signal polls last 7 days: {data['polls_7d']['completed']:,} completed of "
        f"{data['polls_7d']['total']:,} runs (required {data['polls_7d']['required']:,})",
    ]
    for run, count in list(data["runs_by_type"].items())[:8]:
        lines.append(f"- {run}: {count:,}")

    lines += ["", "## Data quality gaps", ""]
    lines.append(
        f"- ACTIVE providers with no overall rating: {data['active_unrated']['count']:,} "
        f"({data['active_unrated']['pct']}% of active)"
    )
    for name, gap in data["quality_gaps"].items():
        if gap["count"] and name != "no_overall_rating":
            lines.append(f"- {name.replace('_', ' ')}: {gap['count']:,} ({gap['pct']}%)")

    lines += [
        "",
        "## Refresh churn - not substantive change",
        "",
        f"- Rows rewritten in the last 24h: {data['churn_updated_at_24h']:,}. "
        "`updated_at` moves on every rolling sweep, so this is refresh activity, "
        "not evidence that CQC published anything.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "artifacts" / "cqc-nightly"))
    parser.add_argument(
        "--live-index",
        action="store_true",
        help="also probe the unfiltered CQC /locations index (slow, informational only)",
    )
    parser.add_argument("--force-report", action="store_true", help="print even when nothing changed")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = out_dir / "state.json"

    try:
        conn = connect_readonly()
    except Exception as exc:  # noqa: BLE001 - a clear message beats a traceback at 02:00
        print(f"CQC nightly check could not run: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    try:
        data = gather(conn, args.window_hours)
        diff = live_index_diff(conn) if args.live_index else None
    finally:
        conn.close()

    previous = load_state(state_path)
    checksum = data["snapshots"][0]["checksum_sha256"] if data["snapshots"] else None
    data["snapshot_changed"] = bool(previous.get("snapshot_checksum")) and previous["snapshot_checksum"] != checksum
    findings = anomalies(data, diff, previous)
    report = render(data, diff, previous)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    (out_dir / f"{stamp}-report.md").write_text(report)
    (out_dir / f"{stamp}-report.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "data": data,
                "live_index": diff,
                "anomalies": findings,
            },
            indent=2,
        )
    )
    save_state(
        state_path,
        {
            "providers_total": data["providers_total"],
            "providers_active": data["providers_active"],
            "match_delta": (data.get("match") or {}).get("delta"),
            "rating_no_destination_share": data["rating_destination"]["window_share"],
            "changes_total": data["changes_total"],
            "watermark_reconciled_at": (data.get("watermark") or {}).get("reconciled_at"),
            "snapshot_checksum": data["snapshots"][0]["checksum_sha256"] if data["snapshots"] else None,
            "checked_at": datetime.now(UTC).isoformat(),
        },
    )

    # stdout is the contract: silence means nothing worth surfacing. A 24h window
    # almost always has *some* ledger event, so `changes_total` alone is not a
    # signal -- only genuine anomalies, a new source snapshot, or a material
    # swing in volume (folded into `findings` by anomalies()) trigger the send.
    heartbeat = datetime.now(UTC).weekday() == 6
    if findings or data["snapshot_changed"] or args.force_report or heartbeat:
        print(report, end="")
        if findings:
            print("\n**Needs attention:**")
            for item in findings:
                print(f"- {item}")
        if heartbeat and not findings:
            print("\nWeekly heartbeat: no anomalies this week.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
