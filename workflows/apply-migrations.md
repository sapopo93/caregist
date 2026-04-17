# Workflow: Apply Database Migrations

## Overview
Applies pending SQL migrations to the PostgreSQL database in version order. Idempotent — safe to run repeatedly.

## Script Location
`db/apply_migrations.py`

## What It Does
1. Connects to PostgreSQL via `DATABASE_URL` env var
2. Checks `schema_migrations` table for applied migrations
3. Applies any missing migrations from `db/migrations/` in order (001-017)
4. Records each migration in `schema_migrations` with timestamp
5. Reports total applied, previously applied, and errors

## Prerequisites
- Python 3.12+, venv activated
- `.env` with valid `DATABASE_URL`:
  - Local: `postgresql://user:pass@localhost:5432/caregist`
  - Neon: `postgresql://...@...eu-west-2.aws.neon.tech/neondb?sslmode=require`
- PostgreSQL version 12+
- Base schema initialized (`db/init.sql` already applied)
- Superuser or role with CREATE/ALTER TABLE permissions

## Running Locally

```bash
cd /Users/user/CareGist
source .venv/bin/activate
python3 db/apply_migrations.py
```

Output:
```
Database: postgresql://caregist:***@localhost:5432/caregist
Applying migrations...
  ✓ 001_growth_features.sql (2.1s)
  ✓ 002_search_hardening.sql (0.8s)
  ...
  ✓ 017_profile_subscription_id.sql (1.2s)
Applied 17 migrations in 23.4s
```

## Running in Production (EC2)

```bash
ssh ubuntu@caregist-api.example.com
cd /home/caregist/CareGist
source .venv/bin/activate
python3 db/apply_migrations.py
```

### Pre-Flight Checklist
- [ ] Database is backed up (Neon: Neon branches, RDS: RDS snapshots)
- [ ] No ongoing deployments
- [ ] Downtime window coordinated if needed (migrations typically <1s per file)
- [ ] `.env` has correct `DATABASE_URL` for production

### Post-Flight Verification
```bash
# Check migrations applied
python3 -c "
import asyncpg
import asyncio
async def check():
    conn = await asyncpg.connect(open('.env').read().split('DATABASE_URL=')[1].split()[0])
    count = await conn.fetchval('SELECT COUNT(*) FROM schema_migrations')
    files = await conn.fetch('SELECT filename, applied_at FROM schema_migrations ORDER BY applied_at DESC LIMIT 3')
    print(f'Total migrations: {count}')
    for f in files:
        print(f'  - {f[0]} at {f[1]}')
    await conn.close()
asyncio.run(check())
"
```

## Migration Files (Current: 17)

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

## Rollback / Undo

**Important:** Migrations are designed to be forward-only. Rollback requires manual SQL or database restore.

### If a migration fails:
1. Check error output (e.g., "relation already exists")
2. Investigate the failing migration file in `db/migrations/`
3. **Do not** continue — fix the issue or restore from backup
4. Once fixed, re-run `apply_migrations.py` (it skips already-applied migrations)

### If you need to roll back entirely:
1. Restore from database backup
2. Do not attempt to `DELETE FROM schema_migrations` — it will cause sync issues

## Monitoring

Track migration status in production:

```sql
SELECT 
  filename,
  applied_at::date as applied_date,
  extract(epoch from (NOW() - applied_at))::int as seconds_ago
FROM schema_migrations
ORDER BY applied_at DESC;
```

## Troubleshooting

**"relation 'care_providers' does not exist"**
- Base schema (`db/init.sql`) was not applied before migrations
- Apply `db/init.sql` first, then run migrations

**"column 'X' already exists"**
- Migration has already been applied
- Check `schema_migrations` table
- Run script again — it will skip already-applied migrations

**"permission denied for schema 'public'"**
- Database user does not have CREATE/ALTER permissions
- Grant permissions: `GRANT CREATE, USAGE ON SCHEMA public TO role_name;`

**Script hangs**
- Database connection timeout — check `DATABASE_URL`, network connectivity
- Check if database is under heavy load
- Use Ctrl+C to cancel, investigate database, retry
