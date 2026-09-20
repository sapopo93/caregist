# Independent reviews — CQC workstreams, 2026-09-20

Two independent reviews were obtained from `gpt-5.6-sol` via `codex exec` (high reasoning effort), a
different provider family from the DeepSeek builders under review. Both reviews ran read-only against
the committed revision in the worktree named, with no authorship relationship to the code.

| # | Revision | Branch | Verdict |
|---|---|---|---|
| 1 | `1ac082d8e12da406c711a8c9a47a8d8bbacd603e` | `fix/cqc-ratings-schema-20260920` | **FAIL** — recorded in `2026-09-20-independent-review-1ac082d.md` (commit `f1faab7`) |
| 2 | `5dc1759188972654f4a0b3d26a68ea57cb39d581` | `fix/cqc-nightly-report-20260920` | **FAIL** — recorded below |

Raw reviewer log for review 2: `/tmp/review_5dc1759.txt` (1,508,028 bytes, sha256 recorded in the commit
message; local-only, hence the findings are transcribed here verbatim).

## Review 2 — findings, verbatim

```
REVIEWER-VERDICT: FAIL
REVIEWED-SHA: 5dc1759188972654f4a0b3d26a68ea57cb39d581
REVIEWER-MODEL: gpt-5.6-sol
FINDINGS:
high tools/nightly_cqc_db_check.py:516 applies the current cron across a window spanning two schedules, producing 28 expected and 4 missed instead of the mixed-schedule 128 expected and 104 missed.
high tools/nightly_cqc_db_check.py:1329 and tools/nightly_cqc_db_check.py:1391 permit MATCHED verdicts when divergent-ID classification is sampled or ingested-source freshness is absent.
medium tools/nightly_cqc_db_check.py:524 counts GitHub success as poll success even when tools/poll_cqc_signals.py:619 records the database run as partial.
medium tools/nightly_cqc_db_check.py:2238 rejects the natural-language CQC publication date, leaving artifacts/cqc-nightly/2026-09-20-report.json:251 newest_available_source null.
medium artifacts/cqc-nightly/2026-09-20-report.md:70 cites an unrated-classification evidence file that is not committed in the reviewed SHA.
low artifacts/cqc-nightly/2026-09-20-report.md:93 labels the 24-hour pipeline window as ending at its own start timestamp.
low artifacts/audits/2026-08-10-cqc-database-change-frequency-report.md:69 retains a literal historical 336-polls/week statement, although active report logic derives 28/week.
FABRICATED-DATA: none found
UNVERIFIED: The 188 cached live-CQC divergent-ID classifications were not individually re-fetched; their cache-derived summaries and the uncommitted classification evidence were inspected only.
```

Reviewer's section H closes:

> Most fixed-window database figures, the snapshot checksum and the attested GitHub failure line
> independently matched their cited sources. The unrated measured total and estimated class split are
> internally arithmetically consistent. … The report does avoid claiming current freshness or
> completeness is green. Both headline verdicts are red and the ingested-source SLA breach is explicit.

## Schedule-history derivation — the high finding is CONFIRMED by independent evidence

The reviewer's first high finding was checked by the Chief of Staff against the repository's own history
rather than accepted on assertion. Command:

`git log -p -G'cron:' --format='COMMIT %h %ad %s' --date=iso -- .github/workflows/cqc-signal-poll.yml`

| Effective from | Commit | Cron | Fires/day |
|---|---|---|---|
| 2026-08-09 | `218f608` | `7,37 * * * *` | 48 |
| 2026-08-31 | `1e7d594` | `37 * * * *` | 24 |
| 2026-09-03 | `39fa9a3` | `7,37 * * * *` | 48 |
| **2026-09-15 10:38Z** | `6bc9880` | `7 18,21,0,3 * * *` | 4 |

The reported window (`2026-09-13T04:37Z → 2026-09-20T04:37Z`) therefore spans two schedules:
`7,37 * * * *` (48/day) from 09-13T04:37Z to the 09-15T10:38Z change, then `7 18,21,0,3 * * *` (4/day).
Fire count: 2/h × 54h ≈ 108, plus the 4/day tail ≈ 20 → **≈128 expected**. Against 24 completed runs that
is **≈104 missed**, reproducing the reviewer's figure. The reviewer's finding is `PASS` as a finding.

`REQUIRED_WEEKLY_POLLS = 336` was **not fabricated**: commit `629e5ff` (2026-09-19) documents it as
"48/day x 7, per cqc-signal-poll.yml", which was exactly the cadence in force from 2026-09-03 to
2026-09-15. It became stale when `6bc9880` changed the cadence to 4/day. Both earlier conclusions —
that 336/week was invented, and that the window showed only 4 missed ticks — are withdrawn: the
constant was correct for its period, and the correct expectation for a straddling window is the sum of
the schedules in force, not the current one. The error in the second came from a Chief of Staff evidence
update that supplied only the current cron to the builder; that chain is corrected here and the
corrective brief now requires a tested schedule-history derivation.

## Additional fail-open defect found while verifying finding #4

Verifying the reviewer's date-parsing finding against source exposed a second, unreported defect on the
live classification path, verified from the code and from captured API evidence:

- `classify_id()` (`tools/nightly_cqc_db_check.py:1046`) decides a timing class with
  `registration_date > snapshot_published_at`.
- `registration_date` arrives from the live CQC API in ISO form: the evidence artifacts contain 488
  `registrationDate` values, all `YYYY-MM-DD` (e.g. `2026-09-15`, `2013-04-01`).
- `snapshot_published_at` is the raw natural-language preamble string, `"16 September 2026"`.

The comparison therefore mixes formats and is lexicographic: every `YYYY-MM-DD` string sorts greater
than `"16 September 2026"` because `'2' > '1'`. So every `Registered` location that is active in
CareGist and absent from the snapshot is classified `registered_after_snapshot_publication` (benign
timing) instead of `registered_on_or_before_snapshot_but_absent`, which is the class a genuine defect
would fall into. The live path cannot currently distinguish the two, and it fails in the direction that
**understates** divergence. The reviewer named only the `newest_available_source: null` symptom.

Scope limit on this finding: the committed report's 32 / 28 split came from the **cached** classification
(`reused_from_cache: 127`, produced by a separate read-only script), not from this function, so the
committed figures are not shown to be wrong by it. What is established is that the live path is broken
and unverified against the cache; the corrected code must reproduce the cache's 60 registered-after /
4 legitimately-inactive split before either number is relied upon, which is now a stated acceptance test.


- No production change was made or verified by either review; both were read-only.
- Cached divergent-ID classifications were not re-fetched (188 entries); the 124-defect count remains
  provisional until re-classified against the live API immediately before any repair run.
- Review 2 did not establish the code-level correctness of the ratings workstream, and review 1 did not
  establish the report workstream. Neither review substitutes for the other.

## Status consequence

Both workstreams are `FAIL` at the revisions above and neither may be merged or deployed. Corrective
commits are required, and each corrective commit requires a fresh review of its exact SHA by the same
independent reviewer before either reaches Henry as ready.
