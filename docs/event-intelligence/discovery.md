# CareGist Event-Intelligence Discovery

Generated on 2026-06-30 from the Phase 0 requirements in the pasted execution spec.

## Assumptions

- Phase 0 is a blocker. Later phases must consume the manifest rather than invent schema names or CQC fields.
- No staging or production migration was applied.
- Local `.env` contains a live-mode Stripe secret key. Billing work must remain read-only until `APPROVED_BILLING_LIVE` is provided.
- CQC API credentials exist, but `FEATURE_CQC_API` is unset, so the MLP must stay bulk/current-table first.

## Affected Components

- `db/init.sql`, `db/migrations/`, and `db/apply_migrations.py`
- Root ETL scripts: `extract_cqc.py`, `clean_cqc.py`, `quality_audit.py`, `prepare_directory.py`, `incremental_update.py`, `run_enriched_pipeline.sh`
- Event/feed services: `api/services/new_registration_feed.py`, `tools/run_new_registration_feed_cycle.py`, webhook and digest utilities
- Existing read model: `care_providers`
- Existing event/readout tables: `trusted_event_ledger`, `rating_changes`, `provider_monitors`, `feed_digest_subscriptions`, `webhook_subscriptions`, `pipeline_runs`
- Frontend surfaces under `frontend/app/`, especially `/sample-report`, `/dashboard`, `/search`, `/provider/[slug]`, and feed-adjacent commercial pages

## Ground Truth

CareGist is not a Prisma project. It is a FastAPI backend using raw SQL through `asyncpg`/`psycopg2`, a PostgreSQL/PostGIS database, and a Next.js App Router frontend. Migrations are plain SQL files applied by `db/apply_migrations.py`; there is no ORM migration framework and no Prisma db-push path.

The live database metadata query returned PostgreSQL 17.10. The table inventory and column types are recorded in `discovery-manifest.json`.

## No-Pulse Diagnosis

The strategy diagnosis is partially confirmed:

- `rating_changes`: 0 rows
- `provider_monitors`: 0 rows
- `feed_digest_subscriptions`: 1 row
- `webhook_subscriptions`: 1 row

The current product does have a new-registration pulse:

- `trusted_event_ledger`: 56,742 rows
- `pipeline_runs`: 4,305 rows
- `care_providers`: 56,743 rows

The main gap is not absence of all events. The gap is absence of rating movement and monitor-driven delivery activity.

## Ingestion Path

The current ingestion path is CQC API/current-register oriented rather than immutable snapshot oriented:

- `run_enriched_pipeline.sh` orchestrates root ETL stages.
- `extract_cqc.py`, `clean_cqc.py`, `quality_audit.py`, and `prepare_directory.py` produce and prepare provider data.
- `incremental_update.py` updates `care_providers`, writes `rating_changes`, and records `pipeline_runs`.
- `api/services/new_registration_feed.py` projects registration events into `trusted_event_ledger`.
- `tools/run_new_registration_feed_cycle.py` syncs feed events, delivers webhooks, queues digests, and updates `pipeline_runs`.

`care_providers` is the current read model. `care_providers.id` is the CQC location id, while `provider_id` stores the linked provider id.

## Tenancy, Auth, Billing

There is no global tenant column. The only tenant-named schema field is `internal_tasks.tenant_id text`, used by support-platform tasks. Product tenancy is account scoped through `users`, `api_keys`, and `subscriptions`.

Auth consists of API-key access, master-key rotation, email/password sessions, and token-gated internal routes.

Stripe is integrated through `api/routers/billing.py`, `subscriptions`, and `stripe_processed_events`. The local environment has live-mode Stripe credentials configured, so all billing productisation must pause before mutation unless the G2 token is provided.

## Smallest Safe Change

The smallest safe next change after Phase 0 is mechanical guardrail work that does not require staging migration approval:

1. Add an evidence-grade language guard for rendered/output templates.
2. Add tests proving banned provider-label framing fails and approved movement/latency framing passes.
3. Wire the guard into CI.

This directly addresses a global invariant from the spec and reduces legal/compliance risk before broader event/report surfaces are added.

## Failure Modes To Preserve Against

- Duplicated events, digests, webhooks, or charges on re-run.
- Treating `trusted_event_ledger` as empty when only `rating_changes` is empty.
- Introducing a migration that changes `tenant_id` type or adds destructive DDL without approval.
- Applying live Stripe product changes from a local environment that already contains a live key.
- Using defamatory labels in reports, digests, webhook descriptions, or UI copy.

## Phase 0 Status

Phase 0 is complete for local discovery. Later WPs can proceed from the manifest, subject to G1 and G2 for migration apply and billing live-mode actions.
