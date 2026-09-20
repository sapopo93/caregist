# Response to the independent review of `5dc1759188972654f4a0b3d26a68ea57cb39d581`

Reviewer: `gpt-5.6-sol` (verdict **FAIL**, 2 high / 3 medium / 2 low / no fabricated data),
recorded in `2026-09-20-independent-review-5dc1759.md`. This file maps each finding to the fix in
**this commit**, the test that holds the fix in place, and the evidence visible in the regenerated
artifacts. This commit is on the same branch (`fix/cqc-nightly-report-20260920`) as the reviewed SHA.

Regenerated artifacts in this commit: `artifacts/cqc-nightly/2026-09-20-report.md` and
`2026-09-20-report.json` (the report's own evidence index pins every file it cites).

## high — the current cron is applied to a window spanning two schedules

*Reviewer:* `28 expected and 4 missed instead of the mixed-schedule 128 expected and 104 missed`.

Fixed by deriving the expectation from the schedule history instead of the workflow file on disk.
`ScheduleEpoch` now carries the cron lines plus the commit that introduced them, read via
`git log --format=%H%x09%cI -- .github/workflows/cqc-signal-poll.yml` and `git show` per revision
(`_crons_in_workflow_text`, `_git_workflow_text`; the path is converted to repository-relative because
`git show` silently fails on absolute paths). `poll_coverage` sums the fires of each schedule over the
segment it was in force and reports the change point in `expected.epochs` / `cadence_change`.

- Artifact: expected **127** (`127 due, 0 not yet due`), missed **102**, with the per-epoch breakdown
  and `Cadence change at 2026-09-15T10:38:36Z`. The reviewed report claimed `28 expected / 4 missed`;
  127/102 reproduce the reviewer's ≈128/≈104 for the same window.
- The on-disk fallback is now labelled, not passed off as history: `expected.schedule_history_available`
  is `true` only when a commit-dated epoch was read, `false` when the history could not be read, and
  `null` when the caller supplied the schedules. A `false` value is rendered as
  "not backed by the schedules in force" and makes pipeline health `UNVERIFIED`.
- Tests: `test_high1_a_window_spanning_a_cadence_change_sums_every_schedule_in_force`,
  `test_high1_one_epoch_matches_the_reviewed_reports_28_expected`,
  `test_high1_an_unreadable_schedule_history_is_loud_and_unverified`,
  `test_high1_repository_history_reproduces_the_reviewers_expected_count`.

## high — MATCHED is reachable while classification is sampled or freshness is absent

*Reviewer:* `tools/nightly_cqc_db_check.py:1329` and `:1391 permit MATCHED verdicts when divergent-ID
classification is sampled or ingested-source freshness is absent`.

`build_verdicts` now takes `incompleteness` (the positive problems returned by
`reconciliation_inputs_are_complete`: sampled classification, a classification cap that dropped IDs,
classification failures, unexplained classes) and `freshness_unavailable_reason`. `data_alignment_verdict`
returns `UNVERIFIED` with those reasons; `pipeline_health_verdict` marks an unevaluated or absent
freshness block `UNVERIFIED` and cites it in `unverified_reasons`. `matched_reasons` is now built only
from promises that were actually evaluated (`_promise_evaluated`), so a sweep that was never estimated
and an SLA that was never measured can no longer appear as promises that held.

- Tests: `test_high2_a_sampled_classification_cannot_produce_matched`,
  `test_high2_freshness_promises_must_be_evaluated_to_be_claimed`,
  `test_high2_a_sweep_that_was_never_estimated_is_not_a_promise_that_held`, plus the updated
  `test_pipeline_health_matched_only_when_every_documented_promise_holds`, which now asserts
  unevaluated → `UNVERIFIED` and evaluated-and-violated → `MISMATCHED`.

## medium — GitHub success counted as poll success while the database records `partial`

*Reviewer:* `tools/nightly_cqc_db_check.py:524 counts GitHub success as poll success even when
tools/poll_cqc_signals.py:619 records the database run as partial`.

The `pipeline_runs` cross-check now counts `partial` alongside `completed`/`failed` and the report line
prints all three (`25 completed, 0 partial, 0 failed / 25 rows`). A partial database run is no longer
absorbed into the successful bucket: it makes the pipeline-health verdict `MISMATCHED` with the partial
count in the reasons.

- Test: `test_medium3_a_partial_database_run_is_not_a_complete_poll`.

## medium — the natural-language publication date is rejected

*Reviewer:* `tools/nightly_cqc_db_check.py:2238 rejects the natural-language CQC publication date,
leaving artifacts/cqc-nightly/2026-09-20-report.json:251 newest_available_source null`.

`parse_publication_date` reads the CQC printed forms (`16 September 2026`, `September 16, 2026`, and
day-first numeric `16/09/2026`) and every read path stores the normalised value: the snapshot cache, the
network fetch, `DirectorySnapshot.to_dict` and `newest_snapshot_covered`. The raw printed string is kept
as `published_at_text` for provenance.

- Artifact: `freshness.newest_available_source` is now evaluated - `published_at: 2026-09-16`,
  `age_hours: 101.1`, `sla_hours: 192.0`, `within_sla: true` - where the reviewed report had `null`.
- The same class of defect was found on the live classification path and fixed with it: `classify_id`
  compared the API's ISO `registrationDate` against the natural-language preamble, which is a
  lexicographic comparison in which every `YYYY-MM-DD` string sorts after `"16 September 2026"` and
  therefore understated divergence by classifying every such location as
  `registered_after_snapshot_publication`. Classification now derives from normalised dates and cached
  entries are re-derived from their raw fields (`CLASS_REVISION`, `_reclassify_cached_entry`), so a
  cached class produced by an older revision cannot be reused silently.
- Tests: `test_medium4_the_publication_date_is_read_as_a_date_not_a_string`,
  `test_medium4_the_mixed_format_comparison_can_no_longer_classify_an_id`,
  `test_medium4_cached_classifications_are_re_derived_before_they_are_reused`.
- Reproduced split: 124 confirmed defects (67 + 57) and 64 legitimate (60 + 4) - the bucket totals the
  reviewed report states. The intra-bucket classes now read 20 registered-after / 40 on-or-before /
  4 db-inactive-matches-deregistration, the 40 being the class the lexicographic comparison could never
  reach.

## medium — the report cites evidence the commit does not carry

*Reviewer:* `artifacts/cqc-nightly/2026-09-20-report.md:70 cites an unrated-classification evidence file
that is not committed in the reviewed SHA`.

This commit carries `2026-09-20-unrated-classification.json`, `state.json`, and the classification
caches (`cache/divergent-db-active.json`, `cache/source-inactive-vs-db.json`,
`cache/attested-causes.json`). The report's new **Evidence index** section lists every cited artifact
with size, truncated sha256, and whether the commit carries it, so a reader can tell tracked from
untracked without opening the tree. The one file deliberately not committed is the 1.1 MiB raw CQC
snapshot, which the index marks "not tracked by git - too large to commit: the checksum above is what
pins it to the CQC URI", and which `.gitignore` now excludes explicitly.

- Test: `test_medium5_cited_evidence_is_flagged_when_the_commit_does_not_carry_it`.
- The checksum itself had to be a live one: `state.json` is rewritten by every run, so the report
  now hashes it *after* the run has written it (`finalize_outputs`). Otherwise the report would
  cite the previous run's file and every cited checksum would be stale on arrival.
  Test: `test_medium5_a_cited_checksum_must_match_the_file_the_run_leaves_behind`.

## low — the 24-hour window was labelled with its own start timestamp

*Reviewer:* `artifacts/cqc-nightly/2026-09-20-report.md:93 labels the 24-hour pipeline window as ending
at its own start timestamp`.

The heading now names the change window's own start and end from the run's `window_start` and
`generated_at`: `## Pipeline runs in the change window (24h, 2026-09-19T05:08:58Z to 2026-09-20T05:08:58Z)`.
The 7-day polling-coverage window in the section above is unchanged and the two windows are still
stated as never being added together.

- Test: `test_low6_the_change_window_heading_names_both_ends`.

## low — the historical 336-polls/week statement

*Reviewer:* `artifacts/audits/2026-08-10-cqc-database-change-frequency-report.md:69 retains a literal
historical 336-polls/week statement, although active report logic derives 28/week`.

The historical sentence is preserved (it was true for the cadence in force when it was written) and
annotated in place with the schedule history that superseded it: `7,37 * * * *` (48/day) →
`37 * * * *` (2026-08-31, `1e7d594`) → `7,37 * * * *` (2026-09-03, `39fa9a3`) → `7 18,21,0,3 * * *`
(2026-09-15 10:38Z, `6bc9880`), under a "Historical figures — do not read as current (annotated
2026-09-20)" label. The current cadence is 4/day = 28/week.

- Test: `test_low7_the_historical_336_polls_per_week_figure_is_marked_historical`.

## Boundaries of what this commit claims

- The 188 cached divergent-ID classifications were **not** re-fetched from the live CQC API, matching the
  limitation the reviewer recorded. What is established is that the corrected derivation reproduces the
  report's own bucket totals from the cache; the 124-defect count stays provisional until it is
  re-fetched immediately before any repair run.
- The report regenerates against the live `pipeline_runs` table and GitHub Actions; the DB cross-check
  read 25 of 25 rows for the window with 0 partial. The environment was read-only: no database rows were
  written and no production change was made.
- No finding was closed by weakening a threshold: every promise, SLA and class definition in the report
  is unchanged, and the arithmetic that changed (127 expected, 102 missed) moved against the report's
  own interest.
