## Problem and resulting behavior

Production has empty Territory Brief tables that predate migration 060. The guarded 072 change tolerates a token table without `artifact_kind`; 073 rebuilds the five outdated Brief tables to the current design, preserving migration 066's source-edition binding and the package columns from 072.

The rebuild locks every existing Brief table before counting rows, refuses if any contains data, and drops without `CASCADE` so unexpected dependants abort and roll back 073. Current schemas follow the no-op path. The runner commits each migration separately: if 073 fails, a successful 072 remains recorded.

## Validation

- Final candidate: `73613c03a8fa9bb1eb6691fb17d16094ee211138` (same reviewed migration SQL; PDF dependency security update).
- Real local Postgres integration suite: 165 passed, one skipped; final migration/governance rerun: 14 passed. Ruff and migration governance pass.
- Regression checks cover old production history, source-edition FK enforcement, schema equivalence, ZIP tokens and constraints, nonempty refusal, concurrent inserts, unexpected dependency rollback, and the populated-current-schema no-op.
- Staging database fulfilment/replay test passed using synthetic Stripe/storage and transaction rollback; corrected 073 no-op rehearsal passed with rollback.
- Independent GPT-6 Astra review found the original missing source binding and count/drop race; both are fixed and the final frozen candidate was re-reviewed with no remaining technical migration-safety blocker for the documented empty-table state.

## Production gate

Founder requested completion of the review, merge, migration and verification on 31 October 2026. Recovery branch `br-floral-paper-abjaq0oa` remains retained without auto-delete; seven-day project history is visible. Read-only checks confirm the recovery database is reachable at migration 071 and production's five Brief tables are empty. This is not a completed restore drill.

The required Grok retest was unavailable (direct providers disabled; configured gateway HTTP 403). On 31 October 2026, the founder explicitly authorized substituting the independent GPT-6 Astra review and executable evidence for this migration, then merging and applying 072/073 once the build/test checks passed. This is a bounded exception for this migration.

## Production result — 31 October 2026

Merged as `0653003270175aa24aa6652933c8dfad0a5f07be` after final candidate CI [41223039921](https://github.com/sapopo93/caregist/actions/runs/41223039921) passed. Production ledger records 072 at 17:16:26 UTC and 073 at 17:16:27 UTC. Row counts, provider status counts and table access are unchanged; columns, constraints and triggers match accepted staging. Frontend and backend serve the merged SHA.

Post-migration [Schema Drift](https://github.com/sapopo93/caregist/actions/runs/41223692699) and [Production Smoke](https://github.com/sapopo93/caregist/actions/runs/41223753262) passed. Checkout and delivery remain disabled; no lead submission, authenticated export or live paid delivery was exercised. Evidence is retained locally under `artifacts/recovery/2026-10-31/`.
