# Independent review record — CQC rating-state changes

- Revision reviewed: `1ac082d8e12da406c711a8c9a47a8d8bbacd603e` (branch `fix/cqc-ratings-schema-20260920`, parent `629e5ff`)
- Reviewer: **gpt-5.6-sol** via `codex exec`, read-only, in `/Users/user/.hermes/worktrees/cqc-ratings-schema`
- Builder under review: subagent `sa-0-d271e555` (deepseek-flash) — different provider family from the reviewer
- Verdict: **FAIL** (3 high, 2 medium, 1 low). Correction dispatched to a new builder and re-review required on the corrected SHA.
- Reviewer's own test run: `175 passed in 3.18s` (independently reproduced by the Chief of Staff)
- Not established by this review: the production-derived counts 24,486 / 20,966 / 57,127, which are recorded with their source evidence in `2026-09-20-reconciliation-detail.md`
- Recorded: 2026-09-20T04:40:20Z

Raw reviewer log retained at `/tmp/review_1ac082d.txt` for the session; the substantive review is reproduced verbatim below.

---

FAIL. The required tests pass, but two production paths contradict the commit’s core claims.

### A. Migration

PARTIAL.

- The schema change is additive. It adds one column and does not update or delete `overall_rating`: `db/migrations/061_provider_rating_state.sql:21-38`.
- It still performs a table-wide `UPDATE` of existing rows.
- The backfill is unsafe. Its `ELSE 'rated'` classifies every unrecognised non-empty value as a real rating. Values recognised as sentinels by Python, including `Not rated`, `Unrated`, and `N/A`, become `rated` in SQL: `db/migrations/061_provider_rating_state.sql:29-36`, `api/services/rating_states.py:56-69`.
- It is not safely rerunnable after ingestion starts. A valid `unknown` row with a retained old `overall_rating` will be changed back to `rated`.
- The down migration restores the old schema, but irreversibly discards every collected `rating_state`. It is an exact schema reversal, not a data-preserving reversal: `db/migrations/down/061_provider_rating_state.down.sql:1-5`.

### B. JSONB null predicate

PASS.

The ledger predicate compares `new_value::text` with `null`, not SQL `IS NULL`: `tools/nightly_cqc_db_check.py:189-200`. A stored JSON null casts to `null`, while a real rating casts to a quoted JSON string such as `"Good"`, so the predicate does not conflate them.

The separate `new_rating IS NULL` check at `tools/nightly_cqc_db_check.py:167` applies to the text column in `rating_changes`, not the JSONB ledger column.

### C. Deactivation and finalization

FAIL.

Failures, non-object payloads, missing status, and non-string status remain active: `incremental_update.py:759-784`.

But the status classifier does not require affirmative deregistration. Every non-empty string other than one matching its loose registered check becomes `deregistered`: `incremental_update.py:726-739`. An unknown value such as `Suspended` therefore triggers deactivation. Conversely, `Not registered` contains `register` and would be retained.

The numeric thresholds remain unchanged at 5%: `incremental_update.py:74-75`, `incremental_update.py:1781-1823`.

The final equality guard is weaker. `kept_active` includes API-confirmed registered and API-unconfirmed candidates: `incremental_update.py:798-808`. All of them are added to `expected_active`: `incremental_update.py:1873-1884`. An API failure therefore becomes part of the expected count and no longer produces an unexplained mismatch.

### D. Invented or carried-forward rating

FAIL.

Sentinels are not newly written into `overall_rating`, but old published ratings are intentionally carried forward when the current source publishes no rating: `incremental_update.py:943-948`, `incremental_update.py:987-1015`.

This also breaks event generation:

1. The previous rating remains in `overall_rating`.
2. The merged current record inherits it: `incremental_update.py:1110-1117`.
3. The event classifier trusts `overall_rating` before the new non-rated `rating_state`: `api/services/provider_state_events.py:177-191`.
4. It therefore sees no status transition.

If a later payload publishes a new rating, the pipeline can emit a false movement from the carried historical value to the new rating, skipping the intervening non-rated state.

### E. Tests

The requested command ran successfully:

`175 passed in 3.18s`

The rating classifier and pure event tests cover many useful cases. They do not cover the production merge path described above. For example, `tests/test_provider_state_events.py:262-288` manually gives the current record `overall_rating=None`, while `upsert_provider()` retains the old real value.

Material gaps:

- No tests call `classify_registration_status()` or `confirm_deactivation_candidates()`.
- No tests cover API exception, malformed payload, missing status, unfamiliar status, registered, or deregistered decisions.
- No non-dry-run finalizer test exercises the new confirmation path.
- `tests/test_incremental_update.py:532-546` inspects source text. It does not prove finalizer behaviour.
- No migration execution test checks sentinel classification, reruns, or rollback data loss.

### F. Commit message

The test-count claim is accurate. Several other claims are false or overstated:

- “Idempotent” is unsafe once ingestion has produced `unknown` plus a retained old rating.
- “No row asserts anything unobserved” conflicts with SQL `ELSE 'rated'`.
- “Single authority for rating text” conflicts with the separate, inconsistent SQL classifier.
- “Retains the historic overall rating with its date so an event … has source-supported evidence” is false in the real upsert path. The retained database value suppresses the event.
- “Ids confirmed as still registered are counted” omits that unconfirmed IDs are also counted.
- “Still refuses on any unexplained mismatch” is false because API-unconfirmed candidates are incorporated into `expected_active`.
- The production-derived counts are not independently supported by repository evidence.

REVIEWER-VERDICT: FAIL
REVIEWED-SHA: 1ac082d8e12da406c711a8c9a47a8d8bbacd603e
REVIEWER-MODEL: gpt-5.6-sol
FINDINGS: high incremental_update.py:943,987,1110 and api/services/provider_state_events.py:177 carried-forward ratings override the destination rating_state, suppress status events, and can later create false rating movements
high incremental_update.py:726-739 deactivates every unfamiliar non-empty registrationStatus instead of requiring affirmative proof of deregistration
high incremental_update.py:798-808,1873-1884 counts API-unconfirmed locations in expected_active, masking unexplained active-set mismatches
medium db/migrations/061_provider_rating_state.sql:29-38 maps every unrecognised non-empty value, including Python-recognised sentinels, to rated and is unsafe to rerun after valid unknown states exist
medium tests/test_provider_state_events.py:262-288 and tests/test_incremental_update.py:532-546 bypass the real rating merge path and use source-text assertions; no API-confirmation failure path is tested
low db/migrations/down/061_provider_rating_state.down.sql:1-5 restores the schema but irreversibly discards all rating_state observations
GUARD-STRENGTH: weaker because API-unconfirmed out-of-manifest locations are added to expected_active, so the equality check accepts an unexplained mismatch
UNVERIFIED: production-derived counts 24,486, 20,966, and 57,127/57,127, plus the external claim that no production change occurred; the required test suite was verified as 175 passed in 3.18s
tokens used
217,756
FAIL. The required tests pass, but two production paths contradict the commit’s core claims.

### A. Migration

PARTIAL.

- The schema change is additive. It adds one column and does not update or delete `overall_rating`: `db/migrations/061_provider_rating_state.sql:21-38`.
- It still performs a table-wide `UPDATE` of existing rows.
- The backfill is unsafe. Its `ELSE 'rated'` classifies every unrecognised non-empty value as a real rating. Values recognised as sentinels by Python, including `Not rated`, `Unrated`, and `N/A`, become `rated` in SQL: `db/migrations/061_provider_rating_state.sql:29-36`, `api/services/rating_states.py:56-69`.
- It is not safely rerunnable after ingestion starts. A valid `unknown` row with a retained old `overall_rating` will be changed back to `rated`.
- The down migration restores the old schema, but irreversibly discards every collected `rating_state`. It is an exact schema reversal, not a data-preserving reversal: `db/migrations/down/061_provider_rating_state.down.sql:1-5`.

### B. JSONB null predicate

PASS.

The ledger predicate compares `new_value::text` with `null`, not SQL `IS NULL`: `tools/nightly_cqc_db_check.py:189-200`. A stored JSON null casts to `null`, while a real rating casts to a quoted JSON string such as `"Good"`, so the predicate does not conflate them.

The separate `new_rating IS NULL` check at `tools/nightly_cqc_db_check.py:167` applies to the text column in `rating_changes`, not the JSONB ledger column.

### C. Deactivation and finalization

FAIL.

Failures, non-object payloads, missing status, and non-string status remain active: `incremental_update.py:759-784`.

But the status classifier does not require affirmative deregistration. Every non-empty string other than one matching its loose registered check becomes `deregistered`: `incremental_update.py:726-739`. An unknown value such as `Suspended` therefore triggers deactivation. Conversely, `Not registered` contains `register` and would be retained.

The numeric thresholds remain unchanged at 5%: `incremental_update.py:74-75`, `incremental_update.py:1781-1823`.

The final equality guard is weaker. `kept_active` includes API-confirmed registered and API-unconfirmed candidates: `incremental_update.py:798-808`. All of them are added to `expected_active`: `incremental_update.py:1873-1884`. An API failure therefore becomes part of the expected count and no longer produces an unexplained mismatch.

### D. Invented or carried-forward rating

FAIL.

Sentinels are not newly written into `overall_rating`, but old published ratings are intentionally carried forward when the current source publishes no rating: `incremental_update.py:943-948`, `incremental_update.py:987-1015`.

This also breaks event generation:

1. The previous rating remains in `overall_rating`.
2. The merged current record inherits it: `incremental_update.py:1110-1117`.
3. The event classifier trusts `overall_rating` before the new non-rated `rating_state`: `api/services/provider_state_events.py:177-191`.
4. It therefore sees no status transition.

If a later payload publishes a new rating, the pipeline can emit a false movement from the carried historical value to the new rating, skipping the intervening non-rated state.

### E. Tests

The requested command ran successfully:

`175 passed in 3.18s`

The rating classifier and pure event tests cover many useful cases. They do not cover the production merge path described above. For example, `tests/test_provider_state_events.py:262-288` manually gives the current record `overall_rating=None`, while `upsert_provider()` retains the old real value.

Material gaps:

- No tests call `classify_registration_status()` or `confirm_deactivation_candidates()`.
- No tests cover API exception, malformed payload, missing status, unfamiliar status, registered, or deregistered decisions.
- No non-dry-run finalizer test exercises the new confirmation path.
- `tests/test_incremental_update.py:532-546` inspects source text. It does not prove finalizer behaviour.
- No migration execution test checks sentinel classification, reruns, or rollback data loss.

### F. Commit message

The test-count claim is accurate. Several other claims are false or overstated:

- “Idempotent” is unsafe once ingestion has produced `unknown` plus a retained old rating.
- “No row asserts anything unobserved” conflicts with SQL `ELSE 'rated'`.
- “Single authority for rating text” conflicts with the separate, inconsistent SQL classifier.
- “Retains the historic overall rating with its date so an event … has source-supported evidence” is false in the real upsert path. The retained database value suppresses the event.
- “Ids confirmed as still registered are counted” omits that unconfirmed IDs are also counted.
- “Still refuses on any unexplained mismatch” is false because API-unconfirmed candidates are incorporated into `expected_active`.
- The production-derived counts are not independently supported by repository evidence.

REVIEWER-VERDICT: FAIL
REVIEWED-SHA: 1ac082d8e12da406c711a8c9a47a8d8bbacd603e
REVIEWER-MODEL: gpt-5.6-sol
FINDINGS: high incremental_update.py:943,987,1110 and api/services/provider_state_events.py:177 carried-forward ratings override the destination rating_state, suppress status events, and can later create false rating movements
high incremental_update.py:726-739 deactivates every unfamiliar non-empty registrationStatus instead of requiring affirmative proof of deregistration
high incremental_update.py:798-808,1873-1884 counts API-unconfirmed locations in expected_active, masking unexplained active-set mismatches
medium db/migrations/061_provider_rating_state.sql:29-38 maps every unrecognised non-empty value, including Python-recognised sentinels, to rated and is unsafe to rerun after valid unknown states exist
medium tests/test_provider_state_events.py:262-288 and tests/test_incremental_update.py:532-546 bypass the real rating merge path and use source-text assertions; no API-confirmation failure path is tested
low db/migrations/down/061_provider_rating_state.down.sql:1-5 restores the schema but irreversibly discards all rating_state observations
GUARD-STRENGTH: weaker because API-unconfirmed out-of-manifest locations are added to expected_active, so the equality check accepts an unexplained mismatch
UNVERIFIED: production-derived counts 24,486, 20,966, and 57,127/57,127, plus the external claim that no production change occurred; the required test suite was verified as 175 passed in 3.18s
