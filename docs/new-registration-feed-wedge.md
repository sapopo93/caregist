# CareGist Phase 1 Wedge

## Product truth

CareGist launch v1 is not a broad directory or generic intelligence suite.

The launch wedge is:

`Newly registered UK care providers, delivered as a filtered recurring intelligence feed.`

Primary buyers:

- VP Sales
- Growth Lead
- RevOps
- founder-led commercial teams
- CareTech vendors selling into newly opened care providers

## Trusted event ledger

The trusted event ledger is the architectural spine for this wedge.

Implemented source of truth:

- table: `trusted_event_ledger`
- canonical launch event type: `new_registration`
- deterministic dedupe key: `new_registration:{location_id}:{registration_date}`
- required fields stored:
  - `entity_type`
  - `entity_id`
  - `provider_id`
  - `location_id`
  - `event_type`
  - `effective_date`
  - `observed_at`
  - `old_value`
  - `new_value`
  - `source`
  - `confidence_score`
  - `dedupe_key`
  - `metadata`

Operational rules:

- event generation is idempotent through a unique `dedupe_key`
- webhook delivery is replay-safe through `webhook_delivery_log`
- digest delivery is replay-safe through `feed_digest_delivery_log`
- saved filters, exports, API access, and digests all read from the same feed query path

## Phase 1 capabilities shipped

- ledger-backed new registration event generation
- filterable feed endpoint and dashboard surface
- CSV and XLSX export from the feed path
- saved filters with plan limits
- weekly digest subscriptions with idempotent queueing
- signed Business-tier webhooks for `feed.new_registration`
- pricing and dashboard copy aligned to the wedge

## EC2 runtime notes

CareGist production is assumed to run on AWS EC2, not Render or Vercel.

Repo-managed EC2 assets:

- PM2 process file: `ecosystem.config.cjs`
- Nginx reverse-proxy reference: `deploy/nginx/api.caregist.co.uk.conf`

Recommended scheduled jobs:

1. Apply migrations during deploy:
   - `python db/apply_migrations.py`
2. Run the recurring feed cycle on a schedule:
   - `python tools/run_new_registration_feed_cycle.py`
3. Process queued emails on a schedule:
   - call `api.utils.email_queue.process_email_queue()` from an existing job runner or management command

Required environment variables:

- `DATABASE_URL`
- `API_MASTER_KEY`
- `APP_URL`
- `RESEND_API_KEY`
- `ENQUIRY_FROM_EMAIL`
- Stripe and Sentry keys as already required by billing/runtime

Deployment guardrails:

- Restart the API process with updated environment after deploy:
  - `pm2 restart caregist-api --update-env`
- Keep `db/migrations/005_care_groups.sql` and `db/migrations/006_rating_changes.sql` defensive around legacy object ownership.
  Those migrations must not fail on EC2 hosts where historical objects are owned by `postgres` rather than the application role.

## Scope discipline

Do not expand launch scope beyond this wedge unless the change clearly strengthens the trusted event ledger or the recurring workflow around it.
