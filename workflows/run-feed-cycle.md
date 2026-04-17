# Workflow: Run New Registration Feed Cycle

## Overview
Synchronizes the trusted event ledger with the latest care provider registrations from CQC, delivers webhooks to Business+ subscribers, and queues weekly digests.

Important: this script does **not** refresh `care_providers` from the upstream CQC API. Run `incremental_update.py` on its own schedule first, then run this feed-cycle job.

## Script Location
`tools/run_new_registration_feed_cycle.py`

## What It Does
1. Syncs `trusted_event_ledger` with new/updated registrations from `care_providers` table
2. Deduplicates events via `dedupe_key` (provider_id + registration_date)
3. Delivers webhook payloads to all active Business+ webhook subscriptions (signed with HMAC-SHA256)
4. Queues weekly digest emails for subscribers with active `feed_digest_subscriptions`
5. Logs all deliveries to `webhook_delivery_log` and `feed_digest_delivery_log` for audit

## Prerequisites
- Python 3.12+, venv activated
- `.env` with valid:
  - `DATABASE_URL` (Neon or PostgreSQL)
  - `RESEND_API_KEY` (for digest emails)
  - `API_MASTER_KEY` (for internal auth if needed)
- All 17 migrations applied (`schema_migrations` table)

## Running Manually

```bash
cd /Users/user/CareGist
source .venv/bin/activate
python3 tools/run_new_registration_feed_cycle.py
```

### Expected Output
- Logs to stdout (INFO level) showing:
  - Number of new events synced
  - Number of webhooks delivered (by status: 2xx/4xx/5xx/timeout)
  - Number of digests queued
  - Summary line: "Feed cycle complete: X events, Y webhooks, Z digests"

### Verify Success
- Check `trusted_event_ledger` row count increased
- Check `webhook_delivery_log` has entries for recent timestamp
- Check `feed_digest_delivery_log` has entries (if weekly cutoff reached)
- Check `pending_emails` has new rows (digest emails waiting for drain)

## Cron Schedule

Add to `/etc/cron.d/caregist` or equivalent cron system:

```cron
# Refresh CQC changes first
*/30 * * * * www-data cd /home/caregist && /home/caregist/.venv/bin/python3 incremental_update.py >> /var/log/caregist/incremental-update.log 2>&1

# Run feed cycle hourly after the refresh window
5 * * * * www-data cd /home/caregist && /home/caregist/.venv/bin/python3 tools/run_new_registration_feed_cycle.py >> /var/log/caregist/feed-cycle.log 2>&1

# Flush the email queue on its own schedule
*/10 * * * * www-data cd /home/caregist && /home/caregist/.venv/bin/python3 tools/flush_email_queue.py >> /var/log/caregist/email-flush.log 2>&1

# Watchdog the whole pipeline and alert on stale operation
*/15 * * * * www-data cd /home/caregist && /home/caregist/.venv/bin/python3 tools/check_new_registration_pipeline.py --notify >> /var/log/caregist/pipeline-watchdog.log 2>&1
```

For systemd timer, create `/etc/systemd/system/caregist-feed-cycle.timer` and `.service` file.

## Monitoring
- **Failure signal**: Exit code non-zero, no incremental-update logs for 45+ minutes, or no feed-cycle logs for 2+ hours
- **Performance baseline**: Should complete in <30 seconds for steady state
- **Alerting**: Log to syslog/Sentry. Undelivered webhooks should retry (see `webhook_delivery_log.retry_count`)

## Rollback / Manual Cleanup
If feed sync goes sideways:

```sql
-- Check recent events
SELECT COUNT(*) FROM trusted_event_ledger WHERE observed_at > NOW() - INTERVAL '1 hour';

-- Check failed webhook deliveries
SELECT * FROM webhook_delivery_log WHERE status NOT IN (200, 201) AND created_at > NOW() - INTERVAL '1 hour';

-- Manual retry (if webhook delivery code supports it)
-- Webhook payload is idempotent per subscription and event_id
```

## Troubleshooting

**"No such table: webhook_subscriptions"**
- Migration 012 not applied. Run `python3 db/apply_migrations.py`

**Webhooks not delivering**
- Verify webhook URLs are HTTPS and responding with 2xx
- Check `webhook_delivery_log.response_text` for error details
- Verify Business+ subscriptions have `is_active = true`

**Digests queued but not sending**
- The digests are queued to `pending_emails`. The email drain runs on health check (`/api/v1/health`). If not draining, manually run `python3 tools/flush_email_queue.py` or restart API

**Performance degradation**
- Check `trusted_event_ledger` row count (`SELECT COUNT(*) ...`). If >100k rows, consider archival strategy.
- Monitor webhook delivery latency in `webhook_delivery_log.response_time_ms`

**Changes endpoint 404 / incremental update failing with ChangesFetchError**
- CQC may have deprecated or moved `/changes/location`. `incremental_update.py` will automatically fall back to a paginated location list scan and insert a `pipeline_alert_log` entry with key `changes_endpoint_unavailable`.
- Verify the CQC API subscription key is valid: check `CQC_API_KEY` / `CQC_SUBSCRIPTION_KEY` in `.env`.
- To force a recovery scan from a specific date: `python3 incremental_update.py --since 2026-02-24`
- The list scan fallback processes all ~55k locations (~56 pages). For a 2-month recovery window expect 8–10 minutes.
- If `care_providers` data is severely stale (>2 weeks) and list scan finds nothing, run the full pipeline: `./run_enriched_pipeline.sh` then `python3 db/seed.py`
- After any recovery run, propagate to the feed: `python3 tools/run_new_registration_feed_cycle.py`
