# Independent review 5 — `72b391c` — review INCOMPLETE, verdict not established (2026-09-20)

Reviewer: `codex exec`, high reasoning effort, model requested `gpt-5.6-sol`. Log: `/tmp/review_72b391c.txt`
(448,995 bytes, 8,159 lines), terminated by SIGKILL (`exit=137`) **before it wrote its verdict block** — the
only verdict-block text in the log is the echoed prompt at lines 78-83. There is therefore no formal verdict
for this revision, and none may be inferred from its absence.

## What the reviewer had already established before it was killed

Its own narration at log line 5404, verbatim:

> The parent falsification reproduces the Chief of Staff result exactly: 13 failed, 45 passed. The reviewed
> code still has new fail-open paths. I reproduced green verdicts for absent classification fields, absent
> ingestion evidence, contradictory class totals, schedule-history gaps, DB-failed polls, fully cancelled
> schedules, incomplete freshness verdicts, and an unevaluated sweep. I will now determine which are
> reachable from the production report path and verify the committed artifacts and arithmetic.

So **eight shapes of green-under-missing-evidence** were reproduced against this revision, and the reviewer
was killed before completing the reachability analysis and before producing the verdict. It also verified,
with primary evidence, all of the following:

* the parent falsification is real: running the new test file against `db513ed` gives 13 failed / 45 passed;
* `REVIEWED_FILES_MATCH_SHA_EXIT=0` — the reviewed files match the SHA, tree clean, its temporary
  `/tmp/rev-parent` worktree removed;
* GitHub in the regenerated 168h window: 25 scheduled runs, all `conclusion=success`, all `completed`;
  database `pipeline_runs` for the same window: 25 `completed` — the `+0` reconciliation holds;
* cache structure: `divergent-db-active.json` holds 127 entries carrying both `class` and
  `class_at_cache_write` plus `class_revision`; `source-inactive-vs-db.json` holds 61;
* the `25,755` unrated count is live-database movement: two `rating_changed` events set the rating to null at
  `04:59:22Z` and `05:00:59Z`, with no reverse events, no new registrations and no status changes in that
  interval. This independently agrees with the database probe recorded in
  `2026-09-20-report-numbers-independent-check.md`.

## The two shapes the reviewer printed at the end, reproduced again here

Both were re-run against the same revision via the test module's own helpers
(`/tmp/repro_failopen.py`), and both reproduce exactly:

| Case | Input | Observed | Required |
|---|---|---|---|
| A | a classification summary whose per-class breakdown has 5 defects while the aggregate `confirmed_defect` is 0 | `classification_evidence_complete: true`, `DATA ALIGNMENT: MATCHED`, `PIPELINE HEALTH: MATCHED` | a contradictory summary is not complete evidence; the verdict must be `UNVERIFIED` |
| B | 128 attempted runs against 128 due fires, none of which corresponds to a fire (`fires_without_a_matching_run: 127`, `missed: 0`) | `PIPELINE HEALTH: MATCHED` — "expected cadence met: no missed, failed, or in-flight ticks in the window" | 127 of 128 fires had no matching run; the verdict must not be green |

## Assessment

The acceptance criterion set for this re-review was: *no remaining route to a green verdict under missing
evidence*. That criterion is **not met** — the reviewer reproduced eight such routes and the Chief of Staff
independently reproduced two of them verbatim. The stream is therefore `NOT READY` on substance as well as
on the missing formal verdict.

The pattern across three rounds is now diagnosable: each round closes the named cases while leaving the
*class* open, because the fix is implemented per input shape rather than as one enforced invariant. A fourth
instance-by-instance round is unlikely to converge, which is why the Chief of Staff has stopped the automated
loop and raised the decision packet
`company-os/reviews/2026-09-20-decision-packet-cqc-nightly-fail-open-verdicts.md`.

Not established: whether the reviewer would have graded any of these as high or medium severity, whether
further shapes existed beyond the eight it named, and whether any of them is unreachable from the production
report path (its own stated remaining step).

Raw log hash recorded in the commit message.
