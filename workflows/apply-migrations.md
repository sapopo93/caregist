# Apply CareGist database migrations

`db/apply_migrations.py` applies each numbered SQL file in its own transaction and records its filename in `schema_migrations`. The production policy is forward-only and Neon PITR is the sole recovery mechanism.

- `db/init.sql` has been applied to a new database before numbered migrations.
- Staging and production use separate Neon projects/resources and distinct credentials.
- Staging receives the exact migration chain before production.
- Production has an evidenced seven-day Neon history window and a timestamped pre-migration recovery branch.
- The release Git SHA, current watermark/batch, counts, operator, approver, and recovery branch ID are recorded before migration.
- The exact historical `034` pair remains unchanged; every future number is unique.

## What It Does
1. Connects to PostgreSQL via `DATABASE_URL` env var
2. Checks `schema_migrations` table for applied migrations
3. Applies every missing numbered migration from `db/migrations/` in filename order
4. Records each migration in `schema_migrations` with timestamp
5. Reports total applied, previously applied, and errors

Run the repository gates first:

```bash
python3 tools/check_migration_governance.py
pytest tests/integration/test_migrations_apply_cleanly.py -v
```

Output:
```
Database: postgresql://caregist:***@localhost:5432/caregist
Applying migrations...
  ✓ 001_growth_features.sql (2.1s)
  ✓ 002_search_hardening.sql (0.8s)
  ...
  ✓ 047_expand_analytics_provider_reference.sql (0.4s)
Applied N migrations in NN.Ns
```

## Staging

Expose `STAGING_DATABASE_URL` through the approved secret channel, then run:

```bash
.venv/bin/python db/apply_migrations.py --target staging
```

Run schema, billing/webhook replay, reconciliation, and application smoke tests on staging. A passing migration command alone is not release evidence.

## Production

Follow `workflows/neon-pitr-restore-drill.md` to verify the history window and create the pre-migration recovery branch. Then expose `PROD_DATABASE_URL` through the approved secret channel and run:

```bash
.venv/bin/python db/apply_migrations.py \
  --target production \
  --confirm-production-backup
```

The confirmation flag records operator intent; it does not create or verify a recovery point. Do not use it until the provider evidence exists.

## Migration Files (Current: 50 files, through 050)

| # | File | Changes |
|---|------|---------|
| 001 | growth_features.sql | analytics_events, email_subscribers, saved_comparisons, provider_monitors, rating_history, api_applications, email_queue, postcode_cache |
| 002 | search_hardening.sql | Rebuilds FTS index to include local_authority, address_line1 |
| 003 | inspection_summaries.sql | Adds inspection_summary TEXT to care_providers |
| 004 | enhanced_profiles.sql | Adds profile_description, profile_photos, virtual_tour_url, inspection_response, profile_tier, profile_updated_at |
| 005 | care_groups.sql | Adds group_name column, creates care_groups materialized view |
| 006 | rating_changes.sql | Creates rating_changes table, weekly_digest_log table |
| 007 | provider_profile_public_fields.sql | Adds logo_url, funding_types, fee_guidance, min_visit_duration, contract_types, age_ranges, updates profile_tier comment |
| 008 | internal_tasks.sql | Creates internal_tasks table (UUID, action, idempotency) |
| 009 | internal_task_idempotency.sql | Adds idempotency_key unique index |
| 010 | profile_completeness.sql | Adds profile_completeness INT column with scoring logic |
| 011 | monitor_alerts.sql | Adds last_alert_sent_at to provider_monitors |
| 012 | webhook_subscriptions.sql | Creates webhook_subscriptions table (user_id, url, events, delivery_log) |
| 013 | subscription_seat_entitlements.sql | Adds included_users, extra_seats, max_users, seat_price_gbp to subscriptions |
| 014 | api_rate_usage_daily.sql | Creates api_rate_usage_daily table (per-day rate limit tracking) |
| 015 | trusted_event_ledger_new_registration_feed.sql | Creates trusted_event_ledger, feed_saved_filters, feed_digest_subscriptions, feed_digest_delivery_log, webhook_delivery_log |
| 016 | stripe_event_deduplication.sql | Creates stripe_processed_events table (24h event dedup) |
| 017 | profile_subscription_id.sql | Adds profile_subscription_id to care_providers |
| 018-033 | operational hardening | Email claims, pipeline logs, password resets, audit logs, idempotency, API-key hashing, sessions, and the named care-groups view |
| 035-043 | remediation hardening | Source watermarks, provider-state event integrity, claim authority/evidence controls, reconciliation batches |
| 044 | b2b_contract_acceptance.sql | Immutable B2B contract evidence and cancel-at-period-end subscription state |
| 045 | signup_purchase_intent.sql | Persists validated signup purchase intent across email verification |
| 046 | billing_operations.sql | Adds a durable, idempotent Stripe billing operations reservation ledger |
| 047 | expand_analytics_provider_reference.sql | Widens analytics_events.provider_id to hold canonical slugs |
| 048 | full_dataset_fulfilment.sql | Adds governed full-dataset artefact and order fulfilment records |
| 049 | cqc_signal_intelligence.sql | Adds canonical CQC source, signal, Radar, and delivery schema |
| 050 | source_snapshot_identity.sql | Repairs duplicate source snapshots and enforces collector upsert identity |

After migration:

1. Verify `schema_migrations` contains every expected filename.
2. Deploy the exact CI-tested SHA with all commercial/governed flags false.
3. Compare `/api/v1/version` and `/api/health/directory` with that SHA.
4. Run production smoke, `/data-status`, provider sitemap, auth/tenant, webhook replay, and database invariants.
5. Run the manual reconciliation and verify its checksum, coverage, counts, and watermark before enabling its schedule.

## Failure and rollback

If a migration file fails, its transaction is rolled back and its filename is not recorded. Stop; do not skip ahead. Fix an unreleased file before retrying, or add a new corrective migration if the faulty file has been released anywhere.

For an application defect, disable feature flags first and roll back code only while schema compatibility remains intact. For an isolated schema/data defect, use a new forward-fix migration. Use Neon PITR only for destructive or irrecoverable damage, then perform the complete restored-branch validation and reconciliation before sending traffic.

Never delete a production `schema_migrations` row to force replay, run a down migration as an ordinary production rollback, or restore over the production branch during a drill.
