# Independent recomputation — nightly report numbers (2026-09-20)

Method: fresh read-only SQL against the production database, written by the Chief of Staff and run
against the committed report JSON authored by a different agent. Neither the SQL nor the comparison
reuses the report's own code. Command: `./.venv/bin/python /tmp/verify_report_numbers.py`.

- Report under check: `artifacts/cqc-nightly/2026-09-20-report.json` (commit `5dc1759`, branch `fix/cqc-nightly-report-20260920`)
- Database: Neon `neondb` (host/port recorded in the session log; credentials never reproduced)
- Tables used: `care_providers`, `pipeline_runs`, `trusted_event_ledger`, `reconciliation_batches`

| Fact | Report claims | Independent recomputation | Result |
|---|---|---|---|
| `providers_total` | 59,030 | 59,030 | MATCH |
| ACTIVE / INACTIVE | 57,193 / 1,837 | 57,193 / 1,837 | MATCH |
| ACTIVE with no overall rating | 25,753 | 25,753 empty-string (0 NULL) | MATCH |
| `signal_poll` runs, reported window | 24 completed | 24 completed | MATCH |
| `signal_poll` all time | 552 | 552 | MATCH |
| Newest ledger event | 2026-09-19T23:09:40Z | 2026-09-19 23:09:40.839+00:00 | MATCH |
| `rating_changed` all time | 34,296 | 34,296 | MATCH |
| `new_value::text = 'null'` | 24,486 | 24,486 | MATCH |
| Divergence split | 124 defect / 64 legitimate / 0 unexplained | 67 confirmed-deregistered-still-ACTIVE + 57 Registered-but-INACTIVE = 124; 60 registered-after-publication + 4 legitimately inactive = 64 | MATCH |
| `only_in_source` | 0 | 0 (no snapshot row missing from CareGist) | MATCH |
| Count-vs-count delta | +42 | 57,193 − 57,151 (stale 09-09 validated snapshot) = +42; +66 against the 09-16 source | MATCH, and the report labels it "not a match signal" |

The divergence classification was derived independently by the Chief of Staff from the live CQC API
before the report existed, and reproduces the same 67 / 57 split and the same 60 / 4 legitimate split.

## Caveats carried forward

1. **The classification is cache-reused, not fresh.** `alignment.classifications.*` records
   `reused_from_cache = 127` and `61` with `fetched = 0` (TTL 168h). The 124 confirmed defects are
   therefore as old as the cache entry. Re-classify against the live API immediately before the repair
   run, and treat the count as provisional until then.
2. **The unrated breakdown is explicitly estimated, not measured.** `unrated.classification.basis`
   states the classes are estimated from a sample and cross-checked against measured population
   totals. That labelling is honest. The Chief of Staff's own uniform-random 300-row live check found
   0 with a currently published rating (Wilson 95% upper bound ≈ 1.26%), so no ingestion omission is
   evidenced — but the per-class counts must not be read as measured.
3. **Freshness must be read on the source data, not the run.** The report now does this: it reports the
   validated source publication as 268.6h old against the 192h promise = BREACH, alongside the 5.5h
   signal age against the 16h SLA. Only the first of those is the ingestion promise.
4. **Sweep arithmetic is a genuine breach, not a threshold to loosen.** 57,127 ÷ (28 × 1,200) = 11.9
   days per full sweep against a documented 8-day promise; ≥42 runs/week is required. The report
   states this as BREACH and does not adjust the threshold to obtain a green result.

## Verdict

`PASS` for the numeric claims and the divergence split: every database-side figure in the committed
report is reproducible from the raw tables by an independent query, and the report's own verdicts
(`DATA ALIGNMENT: MISMATCHED`, `PIPELINE HEALTH: MISMATCHED`) are consistent with its numbers rather
than with the earlier report's overstatement.

Not established here: the code-level correctness of the report tool (separate independent review), and
the freshness of the cached classification (caveat 1).

## Addendum — the unrated count moved, and it was not a defect (2026-09-20, later the same day)

The regenerated report at `72b391c` states `quality_gaps.no_overall_rating = 25755`, whereas this check
measured **25753**. Re-queried directly against the live database:

| predicate (ACTIVE rows) | count |
|---|---|
| `overall_rating IS NULL` | 0 |
| `btrim(overall_rating) = ''` | **25755** |
| `IS NULL OR btrim(...) = ''` | 25755 |
| `IS NULL OR overall_rating ~ '^[[:space:]]*$'` | 25755 |
| whitespace-only, non-empty | 0 |

`active_total` was 57,193 at both measurements, so no status changed. The count moved by two because two
rows' ratings became empty between the two readings, from live production ingestion — not from anything in
these commits, which contain no database write path and are unmerged. This addendum supersedes the
25,753 figure above; neither reading was wrong, and the tool's current figure is the correct one.

