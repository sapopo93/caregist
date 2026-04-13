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
2. Refresh `care_providers` from the CQC changes API (every 30 minutes):
   - `python incremental_update.py`
3. Run the recurring feed cycle on a schedule (hourly, after the refresh job):
   - `python tools/run_new_registration_feed_cycle.py`
4. Send provider monitor alerts (daily at 08:00):
   - `python tools/send_monitor_alerts.py`
5. Send weekly movers digest (Mondays at 07:00):
   - `python tools/send_weekly_movers.py`
6. Flush queued emails on a dedicated schedule:
   - `python tools/flush_email_queue.py`
7. Run the pipeline watchdog and alert on stale or degraded operation:
   - `python tools/check_new_registration_pipeline.py --notify`
8. Run a smoke check after deploys or cron changes:
   - `python tools/smoke_new_registration_pipeline.py --base-url https://caregist.co.uk --api-key "$API_MASTER_KEY" --internal-token "$SUPPORT_INTERNAL_TOKEN"`

See `workflows/deploy-ec2.md` for the full cron configuration block.

Required environment variables:

- `DATABASE_URL`
- `CQC_API_KEY`
- `API_MASTER_KEY`
- `SUPPORT_INTERNAL_TOKEN`
- `APP_URL`
- `RESEND_API_KEY`
- `ENQUIRY_FROM_EMAIL`
- `PIPELINE_ALERT_EMAIL`
- Stripe and Sentry keys as already required by billing/runtime

Deployment guardrails:

- Restart the API process with updated environment after deploy:
  - `pm2 restart caregist-api --update-env`
- Keep `db/migrations/005_care_groups.sql` and `db/migrations/006_rating_changes.sql` defensive around legacy object ownership.
  Those migrations must not fail on EC2 hosts where historical objects are owned by `postgres` rather than the application role.

## Scope discipline

Do not expand launch scope beyond this wedge unless the change clearly strengthens the trusted event ledger or the recurring workflow around it.
