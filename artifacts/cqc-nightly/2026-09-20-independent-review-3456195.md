# Independent review — ratings corrective `3456195` (2026-09-20)

Second review of the ratings workstream. Reviewer: `codex exec` with high reasoning effort, model
requested `gpt-5.6-sol`, self-reported `gpt-6-astra`; read-only, no production access, worktree left
clean (HEAD unchanged, `git status` empty). Raw log: `/tmp/review_3456195.txt`.

## Verdict

```
REVIEWER-VERDICT: FAIL
REVIEWED-SHA: 3456195736e38ce7f3b6b96116bfb100e2093056
REVIEWER-MODEL: gpt-6-astra
FABRICATED-DATA: absent or blank current rating payloads retain a stale current overall_rating; newly
published ratings without their own date inherit or reuse an older rating date
FINDINGS: 2 high / 2 medium / 2 low
UNVERIFIED: production ingestion, production migrations, production database state, and the live CQC
API were not touched; the full 1,100-test suite was not rerun under the temporary non-superuser role
```

## Findings

| Sev | Location | Defect | Required fix |
|---|---|---|---|
| high | `incremental_update.py:1137` | a successfully read payload with `currentRatings.overall.rating` **absent or blank** yields `rating_state='unknown'` and leaves the previous `overall_rating` untouched, so the row keeps asserting `Good` although the source publishes nothing. Reproduced through `clean_location -> upsert_provider` against PostgreSQL: absent → `["Good","unknown","Good"]`, blank → `["Good","unknown","Good"]` (sentinels DO clear it: `Not rated`/`Unrated` → NULL, `N/A` → NULL) | treat absent and blank current-rating fields from a successfully read payload as no-current-rating and clear `overall_rating`; reserve `unknown` for unreadable/incomplete payloads outside this merge path; real-upsert tests for both shapes |
| high | `incremental_update.py:2061` | the finalize guard compares only the total ACTIVE **count**, so equal-and-opposite identity drift satisfies it. Reviewer changed one manifest location to INACTIVE and added one unexplained ACTIVE; the finalizer returned 0 and marked the batch completed because the count stayed 101 | compare the exact ACTIVE ID set against the expected ID set after all writes, under locking/isolation preventing concurrent identity substitution; record and reject missing and extra IDs separately |
| medium | `api/services/rating_states.py:140` | the payload classifier treats every non-empty non-sentinel string as `rated` while `classify_stored_rating` and migration 061 accept only `PUBLISHED_RATING_VALUES`: `Excellent`, `Suspended`, `Under review` → `rated` on ingestion, `unknown` in migration classification. **SQL and Python still have two authorities** | make payload classification use the published-rating allow-list and return `unknown` for unfamiliar strings; test the production payload classifier against the same corpus as migration 061 |
| medium | `incremental_update.py:1130` | a new rating published without a new report date overwrites `last_published_rating` but leaves the previous date in place, and a historic rating date is associated with a different current rating (reproduced: `Requires improvement` paired with the old `Good` date; `Outstanding` paired with a historic `Good` date) | clear `last_published_rating_date` when the new rating has no matching date; never pair a historic rating's date with a different current rating |
| low | `tests/test_rating_states.py:275` | coverage blesses blank rating text as `unknown` without testing the resulting database write, so it passes while the stale rating remains; the arbitrary-string corpus is absent; the balanced-drift finalizer case is missing; source-text assertions remain at `tests/test_migration_governance.py:65` and `tests/test_incremental_update.py:1288` | add real-upsert absent/blank tests, payload-classifier corpus tests, exact-set balanced-drift finalizer test; prefer behavioural migration checks |
| low | `COMMIT_MSG:9` | the message correctly retracts the predecessor's four false claims (lines 81-85) but its own new claims are too broad: lines 9-12 (every no-current-rating payload clears the column), 39-40 (every residual mismatch refuses), 47-48 (SQL and Python cannot drift), 63 (source-text assertions replaced) — each contradicted by the findings above | fix the defects, then amend or narrow the claims to what is proven |

## Verified closed

* **FIX 2 (registration status fail-closed): genuinely closed.** Exact, casefolded, whitespace-normalised
  membership; no substring matching survives. All seven decisions covered through
  `confirm_deactivation_candidates`: Registered → KEEP/confirmed; Deregistered → DEACTIVATE; Suspended,
  missing, non-string, malformed payload, API exception → KEEP/unconfirmed. Vocabulary re-counted from
  `/Users/user/CareGist/artifacts/cqc-nightly/*.json`: 416 `Registered`, 72 `Deregistered`, and nothing else.
* **FIX 4, migration half: `ELSE 'rated'` is gone** (only comments/test descriptions match) and
  `test_backfill_is_a_no_op_on_the_second_run` genuinely executes migration 061 against PostgreSQL,
  snapshots, re-executes, and asserts exact equality. The two-authority problem survives only in the
  payload classifier (medium finding above).
* Focused suite `222 passed in 8.33s`; wider suite `2 failed, 1096 passed, 2 skipped`, both failures in
  the CRM security file.

## Correction to our own record: the CRM failures were environmental, but not for the stated reason

The reviewer created a temporary non-superuser, non-bypass role and reran the full CRM security file:
**9 passed in 1.85s**; a second standalone non-superuser schema probe also passed. PostgreSQL reported
PostGIS unavailable, so the fixture used its documented test shim. The claimed
`permission denied for language c` failure was **not** reproduced in this environment.

Consequence: `2026-09-20-known-failing-tests-pre-existing.md` is corrected. The failures are still
pre-existing and unrelated to the CQC commits (they reproduce at the parent commit), but a fully green
local `pytest tests` **is** achievable — with a non-superuser role, as the reviewer demonstrated. The
earlier "not achievable locally" statement was wrong and has been removed.

## Not established

* No production migration, ingestion, database write, merge, push or deployment was performed.
* The live CQC API vocabulary was not queried; only the local artifacts were counted.
* The full suite was not rerun under the temporary non-superuser role.
* HEAD is not fit to merge because FIX 1, FIX 3 and FIX 4 remain incomplete.
