# The 12-identifier classification movement — mapping, mechanism and consequence

Status: **PARTIAL EVIDENCE, NOT A VERDICT.** The review that produced the counts below (gpt-5.6-sol, review 6)
died on a provider usage limit before writing its findings or verdict. Its computed rows are preserved here
because they are primary evidence; the class and verdict statements were re-checked by the Chief of Staff
against the frozen tree at `72b391c`. Nothing here substitutes for a completed review verdict.

Reviewed revision: `72b391c` (branch `fix/cqc-nightly-report-20260920`). Compared against the earlier
committed classification in `933fa63:artifacts/cqc-nightly/2026-09-20-reconciliation-detail.json`.

## 1. Counts before and after

| Class (normalised across the two class-naming revisions) | `933fa63` | `72b391c` | Change |
|---|---|---|---|
| `confirmed_deregistered_*_active_in_db` — **CONFIRMED DEFECT** | 67 | 67 | **0** |
| `registered_after_snapshot[_publication]` — legitimate | 32 | 20 | **−12** |
| `registered_on_or_before_snapshot_but_absent` — legitimate | 28 | 40 | **+12** |
| total `only_in_db_active` | 127 | 127 | 0 |

**The movement is defect-neutral.** The confirmed-defect bucket is 67 in both revisions. All 12 moved
identifiers moved *between two classes that are both declared legitimate* — `LEGITIMATE_CLASSES` at
`tools/nightly_cqc_db_check.py:143-149` contains both `registered_after_snapshot_publication` and
`registered_on_or_before_snapshot_but_absent`. The class names were also renamed between revisions, which is
why a naive string diff of the two artifacts reports four classes changing rather than one boundary.

## 2. Mechanism — the equality case was re-folded

`tools/nightly_cqc_db_check.py:1482-1488` classifies a Registered location absent from the snapshot by ordering
its registration date against the snapshot publication date, and `timing_order` at `:317-328` is:

```python
return 1 if registered > published else -1
```

Equality therefore returns `-1`, i.e. "on or before", and the identifier lands in
`registered_on_or_before_snapshot_but_absent`. The earlier classification treated the equality case as
"after the snapshot" (`registrationDate >= publication`), which is the class its own artifact text still
describes. Every one of the 12 moved identifiers has `registrationDate == 2026-09-16`, exactly the snapshot's
publication date, so all 12 are the equality case and nothing else.

This is the off-by-one boundary, and it is the whole of the movement: 12 identifiers whose registration date
equals the publication date.

## 3. Mapping table — every moved identifier

Committed cache: `artifacts/cqc-nightly/cache/divergent-db-active.json`, `cache_revision: 2`,
`cache_fetched_at: 2026-09-20T04:35:56Z` (one batch fetch, all 12 rows identical in every field):

| # | id | class before | class after | cache_registration_date | earlier_api_registration_date | status | deregistration |
|---|---|---|---|---|---|---|---|
| 1 | `1-28138615416` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 2 | `1-28917429449` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 3 | `1-29373628725` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 4 | `1-29427375295` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 5 | `1-29462611441` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 6 | `1-29465725101` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 7 | `1-29660435872` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 8 | `1-29663922808` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 9 | `1-29700801899` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 10 | `1-29701615377` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 11 | `1-29716951095` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |
| 12 | `1-29730443298` | `registered_after_snapshot` | `registered_on_or_before_snapshot_but_absent` | 2026-09-16 | 2026-09-16 | Registered | null |

Every move is justified by committed data in the narrow sense that the field values above are what the cache and
the earlier API read actually recorded, and `registrationDate == publication date` is a real, non-fabricated
boundary case. No move depends on an unrecorded value.

## 4. Why this matters even though no defect count changed

The destination class carries a different *claim* from the origin class. `registered_after_snapshot_publication`
excuses absence because the location registered after the directory was published. `registered_after_snapshot`
→ `registered_on_or_before_snapshot_but_absent` substitutes the explanation "snapshot publication lag" — and
that class's own definition text (committed in the `933fa63` artifact) reads:

> `registrationStatus == 'Registered' AND registrationDate < 2026-09-16` while absent from the snapshot

which does **not** cover `== 2026-09-16`. So 12 identifiers are now excused as publication lag by a class whose
stated condition excludes them, and 40 identifiers in total sit in the bucket that excuses absence without
proving lag rather than a directory gap.

**Consequence to decide (not decided here):** either the equality case becomes its own ambiguity class — the
fail-closed reading, consistent with `parse_publication_date` returning `None` rather than guessing when a date
is undecidable — or it stays legitimate and the class definition text is corrected to `<=` and stops asserting
unproven lag. Leaving code and definition text disagreeing is not acceptable in either case.

## 5. Cache provenance (part of the owner's Q4)

All 12 rows come from cache revision 2, fetched `2026-09-20T04:35:56Z`. The run fetched **0** records live and
reused **127** from a 168-hour cache. Classification, including the equality-case boundary above, therefore
rests on cached directory data, and the `coverage: full` sentence printed next to `fetched: 0` must be read as
"all 127 candidates received a class", not "all data freshly retrieved".

VERDICT: **NOT VERIFIED** for the report's classification semantics. This document is evidence, not a review.
