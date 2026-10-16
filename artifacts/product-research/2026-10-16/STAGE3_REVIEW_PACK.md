# Buyer scope storage: review pack for migration 066 and the Stripe boundary

Status: **built and tested, not deployed.** No migration has been run against production. Checkout and delivery gates are untouched and remain closed.

## 1. What changes

| Area | Change | Legacy effect |
|---|---|---|
| `db/migrations/066_territory_brief_buyer_scope.sql` | Two new tables: `territory_brief_scope_versions` (frozen rules, counts, hash, retention timestamps) and `territory_brief_scope_exclusions` (CQC identifiers only). A trigger freezes a version once written and refuses deletes. | `territory_brief_orders` and migration 060 are not altered. Orders without rules have no rows here |
| `api/services/territory_brief_scope_store.py` (new) | Insert, load (checks the reference belongs to the order), schedule purge, purge | None |
| `api/routers/billing.py` | Checkout request accepts optional `buyer_objective`, `excluded_provider_ids`, `excluded_location_ids`. Order and scope version are written in one transaction. Only `scope_ref` (an opaque UUID) is added to Stripe metadata. Response does not echo the rules | Without the new fields, behaviour and metadata are identical |
| `api/services/territory_brief_fulfilment.py` | Order query returns the bound `scope_ref`. Fulfilment refuses if Stripe's `scope_ref` and the order's differ (including one present and one absent). Rules are loaded privately and passed to generation. Retention clock starts at fulfilment | Orders with no reference behave as before |
| `api/services/territory_brief_delivery.py` | Passes loaded rules into the scope | None |
| `tools/purge_territory_brief_exclusions.py` (new) | Dry run by default, read-only session; `--apply` deletes due identifiers | Not scheduled |
| `.github/workflows/ci.yml` | One added step runs the real-Postgres scope test in its own schema | None |

Amendments: the schema supports a new version linked to the original (`version`, `supersedes_version`), and the store accepts `version=2`. **There is no amendment endpoint and fulfilment binds version 1 only.** An amendment after payment is a manual decision, not something this change automates.

Not built: uploading a client list and matching names to CQC identifiers. Exclusions are accepted as identifiers only, so a name can never silently remove a different organisation.

## 2. Evidence

| Check | Result |
|---|---|
| Real PostgreSQL 16, scratch database: apply 060 then 066; insert and load; second order cannot read the first order's scope; frozen scope rejects UPDATE and DELETE; non-CQC identifier rejected by the schema; version 2 links to version 1; purge deletes only due rows and keeps row, hash and counts; regeneration after purge refuses; legacy order untouched; down migration drops cleanly | 1 passed (`tests/test_territory_brief_scope_pg.py`) |
| Unit: Stripe metadata contains no objective or identifier; checkout response does not echo them; names rejected with a 422 that does not repeat them; fulfilment refuses a missing, extra or foreign reference; rules reach generation; retention starts; legacy order SQL unchanged | 12 passed (`tests/test_territory_brief_scope_store.py`) |
| Existing fulfilment, checkout and buyer-rules tests | 64 passed. One test fake gained a `transaction()` method because checkout now opens a transaction |
| Whole non-integration suite | 1365 passed, 1 skipped, 3 failed. The same 3 fail identically on the base commit with my changes stashed (`test_crm_ai_safety` NER model, two `test_nightly_cqc_db_check` git-history tests), so they are environmental and not from this work |
| `ruff check api tools tests`, `tools/check_migration_governance.py` | clean |
| PostGIS replay of all 66 migrations in CI | **Not yet run** for this commit. It runs on the PR |

Not verified: behaviour against a production-sized database, and Stripe Checkout itself (no Stripe access, and the gate is closed).

## 3. Rollback plan

- **Schema.** Forward-only per `db/migrations/README.md`. Before any production run, take and verify the Neon recovery point that policy requires. The down file exists for scratch verification only and discards stored scopes.
- **Why a plain app rollback is not safe once a rules order exists.** Old code ignores `scope_ref` and would generate and deliver a Brief **without** the exclusions. So the order of events matters:
  1. Deploy the migration, then the code, with checkout still closed.
  2. Only open checkout when Henry decides, and not before a rules order has been rehearsed end to end.
  3. If the code must be rolled back after a rules order was taken, close checkout first and hold fulfilment of any order whose Stripe metadata carries `scope_ref`.
- **Data.** Tables are new and additive. Dropping them loses only rules, never orders.

## 4. Exclusion retention: proposal for your decision

Based on your instruction. The period is a placeholder (30 days, `DEFAULT_CORRECTION_WINDOW_DAYS`) until you set it.

| Item | Proposal |
|---|---|
| Raw uploaded lists | Delete immediately after matching. The current build never stores one (identifiers only). When name matching is built, matching runs in memory, the buyer sees the matched and unmatched result, and the raw file is discarded |
| Identifiers | Kept from order to delivery plus the correction period, then deleted by the purge tool |
| Kept after purge | The scope row: objective text, rule version, counts, `scope_sha256`, purge timestamp. This evidences which rules applied without keeping the list |
| Never | Sent to Stripe, logged, shown in output, shared in samples, or readable from another order |

Effects to accept before this is final:

- **Reproducibility.** After purge, the same Brief cannot be regenerated. The code refuses (fails closed) rather than regenerate and re-admit excluded accounts. The delivered PDF and CSV stay as delivered, but download links expire after 30 days and I have not defined blob retention. That is a separate decision.
- **Backups.** Deleting rows does not reach backups. Identifiers remain in Neon point-in-time history until that window ends. **I have not verified the window length.** After any restore, the purge must be re-run before the system is used.
- **Ongoing monitoring.** Monitoring an agreed scope (the later Digest design) needs the exclusions for as long as it runs. Deleting them at the correction period would stop it honouring them. Proposal: monitoring is a separate agreement that creates a new scope version and extends retention to the end of its term, then deletes. Nothing of this is built, and the Digest is not restricted to Brief buyers.
- **Legal.** An exclusion list is the buyer's client list and may include sole traders' personal data. Controller or processor roles, the privacy notice and the retention wording need solicitor review. I have not assessed them.
