# Nightly CQC report - response to the independent review of `db513ed`

Review target: `db513ed433c5001bb5e425c75293076c40e2c4b8` (verdict **FAIL**, six findings).
Corrections land as one commit on `fix/cqc-nightly-report-20260920`. No threshold, SLA,
sweep size, grace, cap or freshness promise was changed by this round.

## Findings and fixes

| # | Site | Fix |
|---|------|-----|
| HIGH | `tools/nightly_cqc_db_check.py:1726` | `data_alignment_verdict` now refuses to read a defect count out of a missing, sampled, capped, failed or unclassified summary: those inputs return UNVERIFIED (the observed defects are still listed, labelled as observed within an incomplete population). Completeness is derived **inside the verdict path** in `build_verdicts` (`reconciliation_inputs_are_complete`) and merged with any caller-reported problems, so an empty caller list cannot manufacture a verdict. `classification_complete` is threaded to the pipeline verdict as well. |
| HIGH | `tools/nightly_cqc_db_check.py:1777` | `pipeline_health_verdict` requires coverage to **exist**, to carry `available: true`, and to contain verified schedule history before it can return MATCHED. `coverage is None` and `available: false` both short-circuit to UNVERIFIED with the reason recorded; the green path never runs on a coverage block that was not supplied. |
| MEDIUM | `tools/nightly_cqc_db_check.py:831` | GitHub workflow success is separated from completed polls. `successful.runs` is the completed-DB-poll count; partial rows are excluded (`partial_runs_excluded`), and `delivered_pct` is computed on completed DB polls with the basis recorded in `delivered_basis`. Partial rows still block a green pipeline verdict. |
| MEDIUM | `tools/nightly_cqc_db_check.py:3159` | The human report renders, beside every classification coverage line: IDs classified / population, the cap, this run's live fetches, cache reuses with the reused entries' age range, the cache TTL, and API errors. `full` is described explicitly as **population coverage, not a live refresh**. |
| MEDIUM | `tests/test_nightly_cqc_db_check.py:814` | The repository-history test now uses the committed window `2026-09-13T05:11:26Z -> 2026-09-20T05:11:26Z`, asserts the independently verified arithmetic (107 + 20 = 127 due, 25 attempted, exactly 102 missed) as hardcoded expectations, and keeps the production cron-derived numbers as a second assertion only. |
| LOW | `tools/nightly_cqc_db_check.py:617` | Schedule epochs are built oldest-first from the workflow's revision history, so a run of identical cron definitions starts at the revision that first carried it (the one-hour cron is dated 31 August, not 3 September). `history_available` also requires every epoch to be dated and requires no gaps in the revision history; a truncated history falls back to the on-disk file and is reported as unavailable. |

## Tests

`tests/test_nightly_cqc_db_check.py::test_round2_*` all drive `build_verdicts` itself -
the previous round's tests called the helper functions, which is how the green paths
survived. Cases: absent summary -> both UNVERIFIED; sampled + observed defect ->
UNVERIFIED; failed/capped -> UNVERIFIED; coverage absent -> UNVERIFIED; coverage
`available: false` -> UNVERIFIED; unreadable git history + on-disk cron fallback ->
UNVERIFIED; DB-partial window -> partials out of the completed counts and out of
`delivered_pct` while still blocking green; the committed window's exact arithmetic;
earliest-commit epoch start dates; plus the ingestion-lag disclosure and the
population/classified count-consistency guard. `test_round2_control_*` keeps MATCHED
reachable, so each negative test shows which piece of missing evidence flips it.

## Remaining fail-open paths (enumerated, as required)

| Path to a green verdict with missing/incomplete evidence | State |
|---|---|
| `summary is None` (no classification at all) | closed - UNVERIFIED |
| Summary with `coverage` other than `full` (sampled/capped/failed/absent) | closed - UNVERIFIED, and `selected`/`cap` rendered |
| Summary with API `failures > 0` | closed - UNVERIFIED |
| Summary whose class counts are not drawn from its whole population (`classified < population`) | closed - UNVERIFIED |
| Coverage block absent | closed - UNVERIFIED |
| Coverage block present with `available: false` | closed - UNVERIFIED |
| Coverage from an unreadable/undated/truncated schedule history | closed - UNVERIFIED (on-disk fallback is disclosed, never green) |
| DB rows recorded `partial` counted as successful polls | closed - excluded from `successful.runs` and `delivered_pct`, still blocks green |
| DB cross-check missing (`db_cross_checked` not `true`) | closed - UNVERIFIED: a GitHub success conclusion may not stand in for a poll the DB never confirmed |
| `unexplained` differences counted | open, unchanged: an observed difference is MISMATCHED with its classes printed, never MATCHED; the reviewer's findings did not ask for UNVERIFIED here, and the reason string discloses the classification |
| Caller passes an empty `incompleteness` list while the summary is incomplete | closed - completeness is re-derived from the summary in the verdict path |
| Ingested state lagging a publication | closed as "disclosed, not blocking": the lag appears in the verdict reasons in both the defect branch and the green branch, and blocks MATCHED on its own. It is not treated as a hole in the classification measurement, because a defect count over a lagging database is exactly the alarm the verdict exists to raise |
| Freshness/sweep evidence absent (`None`) | closed - the pipeline verdict returns UNVERIFIED rather than skipping the check |
| Run-history status other than `ok` | closed - UNVERIFIED |

## Artifacts

Regenerated by running `tools/nightly_cqc_db_check.py` against the read-only production
database (no writes to any service). The report's coverage window is rolling
(`now - 168h -> now`), so a regeneration happens in a slightly later window than the
reviewed artifact: the window end moved 41 minutes, which removes exactly one `7,37`
fire and yields due 126 / missed 101 / coverage 19.8% instead of the reviewed 127 / 102 /
19.7%. The committed window's arithmetic (107 + 20 = 127) is pinned by
`test_medium_tests_the_committed_window_has_exact_independent_arithmetic`. Everything
else is unchanged: both verdicts MISMATCHED, `published_at` ISO `2026-09-16` with
`published_at_text` preserved, the same promises (8-day freshness SLA, 192h source
freshness, 6h interval, 1,200-entity sweep, 28 runs/week, 250-ID classification cap,
168h classification cache TTL, 90-minute grace).
