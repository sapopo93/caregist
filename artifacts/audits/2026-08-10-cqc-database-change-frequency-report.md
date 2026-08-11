# CareGist CQC database change-frequency audit

**Audit time:** 2026-08-10 17:22 UTC  
**Observation window requested:** 2026-05-10 through 2026-08-10 (approximately three months)  
**Environment:** CareGist production as exposed through `https://caregist.co.uk/api/v1/health`, plus repository ingestion/query logic and public project-scoped GitHub Actions metadata  
**Method:** read-only, aggregate-only; no PII or secrets exposed; no database, deployment, workflow, or customer data modified

## Executive conclusion

The production evidence does **not** support saying that the CareGist CQC database changes every day, every three days, or every week.

The strongest supported conclusion is:

- The production database is reachable and contains 56,743 location rows, of which 56,742 are active.
- The newest tracked CQC signal was observed at **2026-06-01 01:03:07 UTC** and had an effective date of **2026-05-29**.
- At audit time, that observation was approximately **70.68 days old**.
- Production reports **zero signal polls in the last seven days**, no completed polls, no source watermark, and no successful reconciliation count.
- The newly configured signal poll started running on 2026-08-09/10, but all **13/13** runs visible in GitHub Actions failed.
- The freshness watchdog also failed on all **14/14** visible runs.
- The authoritative reconciliation workflow has **0 runs** and its recurring Sunday schedule is deliberately disabled.

Therefore the database currently behaves like a **stale snapshot with no proven recurring update cadence**, not a daily, three-day, or weekly refreshed database.

## Direct answers

| Question | Evidence-backed answer |
|---|---|
| Does it change every day? | **No evidence of daily substantive changes.** The newest tracked event is from 1 June and production records zero polls in the last seven days. |
| Does it change every three days? | **No.** There is a gap of about 70.68 days since the newest observed signal. |
| Does it change every week? | **No.** There is no successful weekly reconciliation history, and the reconciliation workflow has never run. |
| When are changes happening? | The last visible tracked ingestion activity occurred at **01:03 UTC on 1 June 2026**, for a source-effective change dated **29 May 2026**. There is insufficient authorized history to calculate the distribution of earlier event times during 10 May–1 June. |
| What is happening now? | A twice-hourly poll is configured for minute 07 and 37, but production has recorded no poll runs and every visible GitHub execution fails at the collector step. |

## Raw production evidence

From `GET https://caregist.co.uk/api/v1/health` at 2026-08-10 17:22 UTC:

- `status = degraded`
- `readiness_ok = true`
- `freshness_ok = false`
- `source_fresh = false`
- `feed_fresh = false`
- `locationRows = 56,743`
- `activeLocationRows = 56,742`
- `activeProviderOrganisations = 36,944`
- `latestObservedAt = 2026-06-01T01:03:07.192570+00:00`
- `latestEffectiveDate = 2026-05-29`
- `sourcePublishedAt = null`
- `sourceRetrievedAt = null`
- `sourceLocationCount = null`
- `countsReconciled = false`
- seven-day `totalPolls = 0`
- seven-day `completedPolls = 0`
- required seven-day poll count = 336
- measured source-to-ledger events in seven days = 0
- checkout readiness = false

`GET https://caregist.co.uk/api/v1/health/freshness` returned HTTP **503** with `status = stale`.

The production release reported by the endpoint is `b2deb57b13913d8a17f4ee00f614b3dc44fa066b`.

## Configured schedules versus actual execution

### Signal poll

Repository schedule: `.github/workflows/cqc-signal-poll.yml:10-11`

- Cron: `7,37 * * * *`
- Intended cadence: twice hourly, 48 polls/day, 336 polls/seven days.
- Actual production health: 0 polls/seven days.
- Public Actions history: 13 total runs from 2026-08-09 22:36 UTC through 2026-08-10 16:27 UTC; 13 failures, 0 successes.
- Latest job setup, checkout, Python setup, and dependency installation passed; the **“Poll approved CQC sources in shadow mode”** step failed with exit code 1.

The collector failure is also explained by release drift. The failing workflow
runs use production SHA `b2deb57b...`, where the collector was invoked as a file
and Python excluded the repository root, causing `ModuleNotFoundError` before
polling. Commit `1769f94` on the current branch changes the invocation to
`python -m tools.poll_cqc_signals` and adds a regression contract test. That fix
is not present in the production workflow SHA observed during this audit.

Important configuration caveat: both collectors default to disabled unless repository variables explicitly equal `true`:

- `CQC_LOCATION_INDEX_POLL_ENABLED`
- `CQC_REPORT_POLL_ENABLED`

The CLI exits successfully without touching the database when both are disabled (`tools/poll_cqc_signals.py:364-368`). Because the observed Actions runs fail rather than skip successfully, at least one later prerequisite or collector operation is failing; the exact log message was not exposed by the public check annotation.

### Reconciliation

Repository state: `.github/workflows/cqc-reconciliation.yml:1-5`

- Intended weekly timing was Sunday 02:15 UTC.
- That recurring schedule is explicitly disabled until manual production gates pass.
- Public Actions history reports **0 runs**.

Therefore there is no weekly authoritative full reconciliation.

### Freshness watchdog

Repository schedule: `.github/workflows/freshness-watchdog.yml:3-6`

- Configured every 15 minutes.
- This job checks freshness; it does not refresh the provider database.
- Public Actions history: 14 runs, 14 failures, 0 successes.

## Query and data-model review

### Correct source of truth for substantive changes

The canonical history is `trusted_event_ledger`, not `care_providers.updated_at` and not `rating_changes` alone.

The event builder records only these substantive transitions (`api/services/provider_state_events.py:135-160`):

- `new_registration`
- `rating_changed`
- `status_changed`
- `ownership_changed`
- `group_movement`

Events are replay-safe through a deterministic `dedupe_key`; the insert uses `ON CONFLICT (dedupe_key) DO NOTHING` (`incremental_update.py:737-783`).

### Important counting defect / interpretation risk

`upsert_provider()` updates every existing provider fetched by the sweep and sets `updated_at` to the ingestion time, even when none of the substantive fields changed (`incremental_update.py:705-723`). It then returns `updated` for every existing row.

Consequences:

1. `care_providers.updated_at` measures **when CareGist rewrote/refreshed a row**, not necessarily when CQC data changed.
2. `pipeline_runs.records_updated` can count refreshed rows whose values were unchanged.
3. A query such as `COUNT(*) GROUP BY DATE(updated_at)` would overstate real-world change frequency.
4. The twice-hourly rolling sweep could make the database appear to “change” constantly even if CQC published no substantive changes.

The correct frequency report must use `trusted_event_ledger.observed_at` for ingestion timing and `effective_date`/`source_published_at` for source timing.

### Monitoring query gap

The internal pipeline endpoint fetches recent runs only for `incremental` and `feed_cycle` (`api/routers/internal.py:492-499`). It excludes both `signal_poll` and `reconciliation`, even though pipeline health separately checks `signal_poll` and the source watermark depends on reconciliation/incremental runs.

This means the endpoint’s `recentRuns` output cannot fully explain the collector that now matters most. The health endpoint correctly reveals zero poll coverage, but the detailed recent-run list omits those poll failures.

## Exact aggregate SQL required for a complete three-month cadence report

The following should be executed through an authorized read-only production connection. It intentionally returns aggregate counts only.

```sql
WITH days AS (
  SELECT generate_series(
    DATE '2026-05-10', DATE '2026-08-10', INTERVAL '1 day'
  )::date AS day
), event_days AS (
  SELECT observed_at::date AS day,
         COUNT(*) AS events,
         COUNT(*) FILTER (WHERE event_type = 'new_registration') AS new_registrations,
         COUNT(*) FILTER (WHERE event_type = 'rating_changed') AS rating_changes,
         COUNT(*) FILTER (WHERE event_type = 'status_changed') AS status_changes,
         COUNT(*) FILTER (WHERE event_type = 'ownership_changed') AS ownership_changes,
         COUNT(*) FILTER (WHERE event_type = 'group_movement') AS group_movements
  FROM trusted_event_ledger
  WHERE observed_at >= TIMESTAMPTZ '2026-05-10 00:00:00+00'
    AND observed_at <  TIMESTAMPTZ '2026-08-11 00:00:00+00'
  GROUP BY observed_at::date
)
SELECT d.day,
       COALESCE(e.events, 0) AS events,
       COALESCE(e.new_registrations, 0) AS new_registrations,
       COALESCE(e.rating_changes, 0) AS rating_changes,
       COALESCE(e.status_changes, 0) AS status_changes,
       COALESCE(e.ownership_changes, 0) AS ownership_changes,
       COALESCE(e.group_movements, 0) AS group_movements
FROM days d
LEFT JOIN event_days e USING (day)
ORDER BY d.day;
```

Additional cadence diagnostics:

```sql
WITH event_dates AS (
  SELECT DISTINCT observed_at::date AS day
  FROM trusted_event_ledger
  WHERE observed_at >= TIMESTAMPTZ '2026-05-10 00:00:00+00'
    AND observed_at <  TIMESTAMPTZ '2026-08-11 00:00:00+00'
), gaps AS (
  SELECT day, day - LAG(day) OVER (ORDER BY day) AS gap_days
  FROM event_dates
)
SELECT COUNT(*) AS active_change_days,
       MIN(day) AS first_change_day,
       MAX(day) AS last_change_day,
       AVG(gap_days) FILTER (WHERE gap_days IS NOT NULL) AS average_gap_days,
       MAX(gap_days) AS maximum_gap_days
FROM gaps;
```

```sql
SELECT run_type,
       status,
       COUNT(*) AS runs,
       MIN(started_at) AS first_run,
       MAX(started_at) AS last_run,
       SUM(COALESCE(records_added, 0)) AS reported_added,
       SUM(COALESCE(records_updated, 0)) AS reported_refreshed_not_necessarily_changed
FROM pipeline_runs
WHERE started_at >= TIMESTAMPTZ '2026-05-10 00:00:00+00'
  AND started_at <  TIMESTAMPTZ '2026-08-11 00:00:00+00'
GROUP BY run_type, status
ORDER BY run_type, status;
```

## Findings by severity

### Critical

1. **Production CQC freshness is stale.** No source watermark, no reconciled source count, no successful poll coverage, and the newest event observation is about 70.68 days old.
2. **The active collector is failing.** All 13 visible signal-poll executions failed at the poll step.

### High

1. **No authoritative recurring reconciliation exists.** The weekly workflow is disabled and has never run.
2. **Operational alerts are not healthy.** All 14 visible freshness-watchdog runs failed.
3. **Naive change-frequency queries are misleading.** Provider `updated_at` and `records_updated` count refresh writes, not just substantive CQC changes.
4. **Internal run diagnostics omit `signal_poll` and `reconciliation`.** This blocks complete root-cause visibility through the supported control plane.

## Customer and cash effect

- Directory users may see provider records that have not been reconciled against a current authoritative CQC snapshot.
- Radar/change-alert claims cannot currently be supported by production evidence.
- Checkout correctly remains disabled; enabling paid signal products while freshness is false would create a sell-versus-ship mismatch.
- No customer data, payment state, or live configuration was changed during this audit.

## Deployment state and rollback

- **Implementation:** schema and collectors exist in production release `b2deb57b...`.
- **Deployment:** API is live and database connectivity works.
- **Operational readiness:** degraded/stale; not customer-ready for freshness-dependent products.
- **Launch:** not approved; checkout is false.
- **Changes made by this audit:** report file only. No production rollback is required. Delete this report file to roll back the local documentation change.

## Limits and exact next gate

A direct production SQL session was not used because this CareGist operator session did not receive a governed task brief authorizing production database access, an approved read-only credential/control-plane token, named reviewer, or evidence path. The public health endpoint provides current aggregate database evidence but not the full daily event series from 10 May through 1 June.

To finish the exact day-by-day three-month histogram, the next gate is:

1. A governed CareGist task brief naming the project/offering, H-Kay entity, UK scope, aggregate-only acceptance criteria, approved production read-only access limit, evidence path, and independent reviewer.
2. An authorized read-only production route: preferably a restricted reporting role or a new aggregate internal diagnostics endpoint. Do not share the database URL or token in chat.
3. Run the aggregate SQL above, preserve only aggregate output, and obtain independent review before using the result in customer claims.

**Reviewer:** not assigned in the supplied authority.  
**Next human gate:** ai-company-governed task brief plus named independent reviewer and approved read-only production access route.

## Local remediation added after audit

Following founder feedback that this must be answerable for customers, a local,
aggregate-only API capability was implemented but **not deployed**:

- `GET /api/v1/tools/cqc-change-frequency?days=90`
- Accepted window: 1–365 inclusive UTC days.
- Source of substantive changes: `trusted_event_ledger` only.
- Excludes provider refresh writes from change counts.
- Returns daily counts and totals for registrations, ratings, status, ownership,
  and group movement.
- Returns longest quiet streak and observed daily/three-day/weekly cadence flags.
- Separately returns collection coverage, completed/failed run totals, and an
  `interpretationReliable` flag. A quiet market is not presented as conclusive
  when collectors did not run throughout the period.
- Public route uses the existing 30-request/minute IP rate limit and exposes no
  provider-level records or PII.
- Internal `/internal/pipeline` recent-run diagnostics now include
  `signal_poll` and `reconciliation`.

Validation evidence:

- RED: endpoint tests returned 404 and internal run-filter assertion failed.
- GREEN: 13 targeted tests passed.
- Ruff: all changed Python files passed.
- Python compile check: passed.
- Full repository suite: **555 passed, 2 skipped**.
- Disposable PostgreSQL execution: full 49-migration schema applied; both new
  SQL queries executed successfully; 90 daily rows returned; test database was
  dropped afterward.
- Independent review: blocked because the profile's configured DeepSeek reviewer
  had no usable credential. This remains a release gate.

Deployment remains blocked until the production collector is repaired, the
endpoint receives independent code/security review, and the change is released
through the governed production process. The endpoint alone makes the question
answerable; it does not make stale production data reliable.
