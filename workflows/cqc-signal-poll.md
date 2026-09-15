# Workflow: CQC Signal Poll

## Overview
Polls CQC's location index and weekly report index for new-registration and rating-change signals, writes them into `trusted_event_ledger`, and records a `pipeline_runs` row (`run_type = 'signal_poll'`) for every attempt. This is the freshness backbone behind the New Registration Feed and Monitor Alerts — `tools/nightly_cqc_db_check.py` alerts if fewer than 336 polls (48/day) complete in a rolling 7-day window.

## Script Location
`tools/poll_cqc_signals.py`, invoked by `.github/workflows/cqc-signal-poll.yml`.

## Schedule
GitHub Actions cron `7,37 * * * *` — every 30 minutes, 48 runs/day, 336/week.

## Known constraint: runtime must stay well under the 30-min cadence

The workflow uses `concurrency: {group: cqc-signal-poll-production, cancel-in-progress: false}`, so at most one run is in flight and at most one more is queued behind it — any additional scheduled trigger that arrives while both slots are occupied is dropped, not retried.

**Incident (found 2026-09-15):** with `--sweep-size 1200`, runs took 15–32 minutes — close to or over the 30-minute interval. Across the 100 most recent scheduled runs (2026-08-31 → 2026-09-15) the mean gap between runs was **219 minutes** (min 89, max 455) against a 30-minute cadence, i.e. ~6.6 runs/day instead of 48 — matching the shortfall `tools/nightly_cqc_db_check.py` reports (`polls_7d`, ~46 completed of 336 required). 96 of those runs succeeded, 1 failed and 3 were cancelled, so this was scheduling starvation, not a poller bug.

**Fix applied:** `DEFAULT_SWEEP_SIZE` in `tools/poll_cqc_signals.py` and the workflow's `sweep_size` input default were both dropped from `1200` to `500`, which keeps runs comfortably inside the 30-minute window and restores the intended cadence.

**If you need to change `--sweep-size` or `--sleep` again:** check the actual run duration in GitHub Actions (`gh run list --workflow=cqc-signal-poll.yml`) before and after. If a run regularly exceeds ~20 minutes, either lower `sweep_size` further or widen the cron interval — and if the interval changes, update `REQUIRED_WEEKLY_POLLS` in `tools/nightly_cqc_db_check.py` to match, or the nightly check will alert on a shortfall that is no longer a bug.

## Verifying the fix took effect
```bash
gh run list --workflow=cqc-signal-poll.yml --limit 20 --json createdAt,conclusion,status
```
Gaps between consecutive `createdAt` timestamps should cluster around 30 minutes. Also check the nightly report's `polls_7d` figure climbs back toward 336 over the following week (`artifacts/cqc-nightly/*-report.json` → `data.polls_7d`).

## Manual run
```bash
cd /Users/user/CareGist
source .venv/bin/activate
python3 -m tools.poll_cqc_signals --sweep-size 500 --checkpoint-size 100 --sleep 0.05
```
Requires `DATABASE_URL` and `CQC_API_KEY` in `.env`.

## Troubleshooting

**`polls_7d.completed` well below 336 again**
- Check run durations via `gh run list` as above — if they've crept back up near 30 min, the sweep size or cadence needs revisiting (see constraint above).
- Check `pipeline_runs` for `signal_poll/failed` or `signal_poll/partial` rows and their `error_message` — a real API failure looks different from starvation (starvation shows all-success runs with wide gaps).

**Report-index scrape returns zero candidates**
- CQC's search page markup may have changed; `LOCATION_ID_PATTERN` in `tools/poll_cqc_signals.py` regex-matches `/location/<id>` links and is brittle to markup changes.
