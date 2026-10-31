# Independent migration review — 2026-10-31

**Latest reviewed candidate: `73613c03a8fa9bb1eb6691fb17d16094ee211138`.** The earlier candidate identities below preserve review history. See the final addendum for the dependency-only change and runner guard updates. Final candidate CI was still running when this addendum was written.

- Reviewer model: `gpt-6-astra`.
- Frozen candidate: `cf00af5422fa6ee4ad7ffab3a04fb691f7992b7f`.
- Checkout inspected: `/tmp/caregist-migrations-072-073`; HEAD matched the candidate and working tree was clean.
- Scope: read-only technical review of PR #155 migrations 072/073, migrations 060/066/071, migration runner, regression tests, and supplied preflight/staging/recovery evidence. Only this review artifact was written.

## Finding

No remaining migration-safety blocker identified for the documented production state. This is a bounded technical finding, not merge, deployment, commercial-gate, or production-application approval.

The original candidate `c940d020d77231adbdbbd37bb57bce50d1800baa` had two blocking defects: its rebuild omitted migration 066's `source_edition_id` column and foreign key, and it counted rows without first preventing concurrent inserts. Both were corrected in `5de04da9339366a18604df072c36ce5569d8e5c7` and remain corrected in the final candidate.

| Promise | Evidence checked | Finding |
| --- | --- | --- |
| Handle production tokens without `artifact_kind` | 072 conditional column guard | Supported. |
| Preserve source-edition binding | 073 required-column detector and BIGINT FK to `territory_brief_source_editions`, `ON DELETE RESTRICT`; compared with 066 and application SQL | Supported. |
| Never rebuild populated Brief tables | All five existing tables are locked `ACCESS EXCLUSIVE` before counts; any positive count raises | Previous race closed. A two-connection regression test covers a writer committing while migration waits. |
| Unexpected dependencies cannot be silently deleted | Drops omit `CASCADE`; external-view rollback regression test | Supported. |
| Rebuilt schema matches current chain | Column/default/nullability and constraint comparison against 060/066/071/072; direct SQL inspection of indexes/triggers | Supported within these checks; the test signature is not an exhaustive comparison of every PostgreSQL catalog property. |
| Behaviour assertions exercise 073 output | Final delta explicitly rolls back the temporary comparison schema before ZIP/uniqueness/trigger assertions | Previous non-blocking test weakness corrected. |
| Existing grants/policies are preserved for this production state | `production-before.json`: all five tables owned by `neondb_owner`, no explicit table ACLs, no RLS | No preservation defect evidenced, assuming migration runs as the existing owner. |

## Evidence and limits

`production-before.json` records all five Brief tables empty at 2026-10-31 17:02:11 UTC. The supplied `integration-tests.txt` reports 165 passes and one skip, including five migration tests; `staging-fulfilment.txt` reports one pass. The parent reports a final rerun of 14 targeted tests and Ruff passing after the test-only correction. I inspected the final delta, but did not independently execute tests or query live databases.

Staging already has the current schema, so its 073 rehearsal exercises the no-op path; the production-style destructive rebuild is covered by the local regression tests. The migration runner commits each migration separately: a successful 072 remains committed if 073 fails, while 073's changes and ledger insertion roll back together. Recovery evidence establishes a recovery branch; it does not establish a completed restore drill.

**Required Grok gate remains missing.** The parent reports disabled direct providers and a gateway 403. This review neither substitutes for that prescribed gate nor establishes release approval. Checkout, collectors, outbound delivery, leads, claims, and exports remain subject to their existing named gates.

## Subsequent bounded runner review

The parent subsequently relayed explicit user authorization to substitute this independent technical review plus executable evidence for the unavailable Grok gate for this bounded migration, and to merge/apply after the build/test checks pass. That authorization supersedes the earlier procedural hold for this operation; it does not turn the unavailable Grok test into a performed test or open commercial gates.

Inspected `apply_reviewed_migrations.py` and its imported `inspect_databases.py` without executing either. Runner SHA-256 at review: `707e06815c09c2fc52f39e738b000f2a32f8095554ac1d28c1ccb73b9a6b5b47`. Both embedded migration hashes matched the frozen SQL files.

No intrinsic mutation-safety blocker identified for the already verified production connection and normal, non-optimized Python execution. The runner defaults to database-read-only preflight; `--apply` is required for migration writes. It checks the frozen clean worktree, SQL hashes, staging ledger/source column, production execution owner, exactly the two pending migrations, empty Brief tables, and expected table ownership/ACL/RLS. Each migration and its ledger insertion commit together under explicit READ COMMITTED isolation, with a 10-second lock timeout and 120-second statement timeout. The SQL itself repeats the emptiness safeguard after locking all five tables. Postflight saves evidence and checks ledger entries, columns against staging, source FK/ZIP check presence, counts and access metadata.

Execution conditions and limitations:

- Run with ordinary Python, without `-O` or `PYTHONOPTIMIZE`: the runner uses `assert` for its guards, and optimized Python removes those guards.
- Bind `.env`'s `DATABASE_URL` to the independently verified production endpoint before execution. Comparing its text with the staging URL proves that credentials differ, not that they address distinct Neon branches. The runner does not independently verify branch identity.
- A 073 failure leaves a successful 072 committed. The current runner then rejects a retry because its exact pending-set precondition no longer holds. Inspect the ledger and prepare a bounded resume; do not bypass the guard or describe the pair as atomically rolled back.
- Postflight checks occur after commit. Concurrent unrelated production activity can change aggregate counts; a postflight mismatch requires investigation and does not mean the migrations rolled back. The journal can also lag a successful commit if file writing is interrupted; the database ledger is authoritative.
- Preflight/build/test/recovery approval remains an external operational prerequisite; this script does not query GitHub checks or perform recovery validation itself.

Read `recovery-database-check.json`: it records a successful read-only snapshot with 072/073 absent and all five Brief tables empty. This improves recovery evidence beyond console branch creation, but is still not a restore drill. The supplied `recovery-recheck.txt` identifies the expected branch URL; its visible excerpt does not itself show retention or expiry settings. Current retention/expiry verification is therefore attributed to the parent report, not independently established from that text excerpt.

## Final dependency-only candidate addendum

Independently verified clean worktree HEAD `73613c03a8fa9bb1eb6691fb17d16094ee211138`. Its complete delta from `cf00af5422fa6ee4ad7ffab3a04fb691f7992b7f` consists of matching `pypdf==6.21.2` to `pypdf==6.21.4` updates in `requirements.txt` and `requirements-api.txt`. No migration or application source changed. Both migration SHA-256 values remain exactly as previously reviewed. Therefore the migration-safety finding carries forward unchanged.

No new code-review blocker identified in the dependency delta. The application uses `PdfReader(..., strict=True)` for customer-package validation, so final candidate CI must establish dependency installation, package validation and workflow compatibility. The parent attributes the bump to seven newly reported advisories; I did not independently verify those advisory fixes, and do not substitute the version change for a passing security audit. Earlier tests run on the previous candidate must not be relabelled as final-candidate execution evidence.

Re-inspected the runner, now bound to candidate `73613c03a8fa9bb1eb6691fb17d16094ee211138`, SHA-256 `5fa92b45d79aeaf075a6642b56626681182b1fe33b9953bfc382af42fe1316fe`. It explicitly raises when Python optimization is enabled before any connection or mutation, closing the assert-removal concern. It also checks the production hostname against the established endpoint; the endpoint identifier matches the source identifier used by the 27 October recovery runner. Transaction and timeout logic remains unchanged. No additional runner blocker identified. All previous limits concerning per-migration commits, postflight investigation and external CI/recovery prerequisites still apply.

No scripts, database operations or external messages were executed in this review. The user-authorized bounded substitution remains as recorded above; final merge/application still depends on the requested final-candidate build/test checks passing.

## Post-execution independent evidence review

Reviewed the actual saved outcome artifacts read-only after application. No production operation was performed by this reviewer. The earlier pending-CI and pre-execution statements above are historical; the final statuses below supersede them.

| Completion claim | Independently inspected evidence | Finding |
| --- | --- | --- |
| Released source is the reviewed candidate's source | Local `git rev-parse` for candidate `73613c03a8fa9bb1eb6691fb17d16094ee211138` and merge `0653003270175aa24aa6652933c8dfad0a5f07be` | Both tree IDs equal `34ed51d9ccda23b1afd2f93640a35555b9971cab`. Merge commit identifies PR #155 and is dated 17:16:05 UTC. |
| Final candidate build/test/security checks passed | `github-ci-final.json`, run `41223039921`, head `73613c03a8fa9bb1eb6691fb17d16094ee211138` | Completed successfully; all five recorded jobs successful, including backend audit, frontend build/audit, container scans and real-Postgres migration replay. |
| 072 and 073 were applied | `application-journal.json`, `production-application.txt`, database ledger in `production-after.json` | Reviewed SQL hashes match journal; ledger records 072 at 17:16:26.797055 and 073 at 17:16:27.002699 on 31 October. |
| Counts/access preserved and intended schema obtained | Compared `production-immediate-preflight.json` with `production-after.json`; compared postflight with `staging-before.json` | All recorded table counts, provider status counts and table-access records unchanged. All five Brief tables remain empty. Postflight column, constraint and trigger arrays exactly equal the staging arrays. |
| Production schema current | `production-schema-check.txt`; `schema-drift-after.json`, run `41223692699` | Stock runner reports no pending migrations; GitHub schema drift check succeeded on merge SHA. |
| Live frontend/backend serve merged release | `directory-health-after.json`, `health-after.json`, `version-after.json` | All identify `0653003270175aa24aa6652933c8dfad0a5f07be`; recorded health status is OK/healthy. |
| Bounded production smoke passes | `production-smoke-after.txt`; `production-smoke-github.json`, run `41223753262` | Read-only directory/search/provider checks pass and anonymous export returns 401. GitHub smoke is completed successfully on merge SHA, superseding the parent's initial in-progress status. Full lead/export smoke is explicitly skipped. |
| Commercial gates stayed closed | `health-after.json` | `checkoutReady=false`, `delivery.enabled=false`, `deliveryEnabled=false`. No paid/live-delivery activation can be inferred from this migration. |

No critical defect or unsupported bounded migration-completion claim identified in these outcome records. Recovery evidence remains a branch snapshot plus read-only validation, not a restore drill. GitHub run statuses are verified from saved tool-result artifacts, not freshly queried by this reviewer. Any duplicate main-push CI must be described using its actual status, although source-tree equivalence with the successful candidate is independently established.

Documentation correction requested: at the time of this review, `README.md` still labelled final CI, production application and live verification as pending. The parent was notified to reconcile those rows with the final evidence before handoff. Claims that all export/lead/payment journeys were exercised, or that source quality/commercial readiness was comprehensively approved, would exceed this review and the recorded smoke coverage.

### Final handoff correction verified

Re-read the final `README.md`. Its stale pending rows have been replaced with the observed candidate CI, migration-ledger, schema-drift and production-smoke results; it correctly identifies the merged release and preserves the unexercised authenticated-export/lead and closed-commercial-gate limits. The documentation defect is closed. The bounded five-step migration completion claim is supported by the reviewed evidence. A pending automatic main-push CI is separate from the successful exact-candidate CI; the candidate and merge source trees were independently confirmed identical. No additional tests were performed for this documentation recheck.
