# Migration 072/073 execution evidence — 31 October 2026

Operator: Codex. Approver: Henry Mlalazi, explicit instruction to complete the five migration steps and explicit bounded substitution for unavailable Grok retest; see `authorization.md`.

## Frozen candidate and defects corrected

PR155 candidate: `73613c03a8fa9bb1eb6691fb17d16094ee211138`. Initial `c940d020` failed independent review: 073 dropped the source-edition binding and allowed an insert between its row-count check and DROP. Both are fixed, covered by real-Postgres regressions and independently re-reviewed. The final candidate adds a PDF dependency security patch; migration hashes are unchanged.

| Claim | Source and observable evidence | Current result |
| --- | --- | --- |
| Recovery branch is retained and pre-072 | `recovery-recheck.txt`, `recovery-database-check.json`, `recovery-invariants.json` | PASS: `br-floral-paper-abjaq0oa`, production parent, no auto-delete, seven-day project history; read-only database invariants pass. This is not a full isolated deployment restore drill. |
| Production rebuild is safe for documented state | `production-before.json`, `production-immediate-preflight.json`, final SQL, `independent-review.md` | PASS preflight: five Brief tables empty; owner/ACL/RLS match reviewed assumptions; exactly 072/073 pending. Rechecked by runner immediately before execution. |
| Rebuild preserves current schema and refuses unsafe cases | `integration-tests.txt`; final targeted rerun | PASS: 165 local integration tests, one skip; 14 final targeted migration/governance passes. Tests cover column/default/nullability/constraint parity, source FK, concurrent insert refusal, unexpected dependency rollback, tokens and immutable scope evidence. |
| Staging supports package fulfilment/replay | `staging-fulfilment-final.txt` | PASS on final PDF dependency, with synthetic Stripe/storage and transaction rollback; no outbound delivery. Corrected 073 no-op rehearsal also rolled back. Production-style rebuild is covered locally because staging already has the current shape. |
| Final candidate CI | `github-ci-final.json`, run `41223039921` | PASS before merge: backend/tests/audit, frontend, container/security scan, secret scan, real-Postgres replay. Candidate and merge have identical Git tree `34ed51d9ccda23b1afd2f93640a35555b9971cab`. |
| Production migrations applied | `application-journal.json`, `production-after.json`, `production-application.txt` | PASS: 072 recorded at 17:16:26.797055 UTC, 073 at 17:16:27.002699 UTC. Counts/status/access unchanged against immediate preflight; columns, constraints and triggers match staging. |
| Production schema drift | `production-schema-check.txt`, `schema-drift-after.json`, run `41223692699` | PASS on merged main: no pending migrations. |
| Live verification and commercial gates | `health-after.json`, `directory-health-after.json`, `version-after.json`, `production-smoke-after.txt`, `production-smoke-github.json`, run `41223753262` | PASS: frontend/backend serve merged SHA `0653003270175aa24aa6652933c8dfad0a5f07be`; local and GitHub smoke pass. Checkout/delivery flags remain false. Anonymous export is denied with 401; authenticated export and lead submission were deliberately not exercised or activated. |

## Outcome

DONE for the five requested migration steps. PR155 merged at 17:16:05 UTC as `0653003270175aa24aa6652933c8dfad0a5f07be`; both production migrations are applied and verified. Independent final evidence review is recorded in `independent-review.md`. The automatic main-push CI is a duplicate run against the identical already-tested tree; its status is separate from the successful candidate CI and final schema-drift/production-smoke results above.

## Execution boundaries

The prepared runner defaults to read-only preflight. It verifies the reviewed checkout and SQL hashes, production hostname, distinct staging credentials, owner/ACL/RLS, pending set and empty Brief tables. Explicit `--apply` executes only 072 and 073 in per-file READ COMMITTED transactions with 10-second lock and 120-second statement timeouts, each with its migration-ledger insert. A failed 073 leaves successful 072 applied; do not assume both rolled back or rerun blindly. Postflight verifies ledger, schema parity, source FK, ZIP constraint, counts and access state. Postflight failure is an investigation gate, not a rollback claim.

No old Mac migration script, down migration, ledger deletion, collector, source import, live payment, external blob upload, outbound message or commercial-gate activation is authorized by this execution record.

Uncommitted primary-workspace changes were preserved in `local-work-preserved.patch` and left in place; PR work uses `/tmp/caregist-migrations-072-073`.
