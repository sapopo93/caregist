# Workflow: Send Provider Monitor Alerts

## Overview
Sends per-user email alerts when a watched care provider's CQC rating changes. Gated to Pro+ subscribers only.

## Script Location
`tools/send_monitor_alerts.py`

## What It Does
1. Queries all active `provider_monitors` (users watching specific providers)
2. Compares current provider rating with last `last_rating` stored
3. On change, creates a `rating_changes` event record
4. Queues alert email via `pending_emails` table
5. Updates `last_alert_sent_at` watermark to throttle duplicate emails

## Prerequisites
- Python 3.12+, venv activated
- `.env` with valid:
  - `DATABASE_URL` (Neon or PostgreSQL)
  - `RESEND_API_KEY` (for alert emails)
  - `ENQUIRY_FROM_EMAIL` (sender address)
- All 17 migrations applied, including:
  - Migration 001 (`provider_monitors` table)
  - Migration 006 (`rating_changes` table)
  - Migration 011 (`last_alert_sent_at` column)

## Running Manually

```bash
cd /Users/user/CareGist
source .venv/bin/activate
python3 tools/send_monitor_alerts.py
```

### Expected Output
- Logs showing:
  - Number of monitors checked
  - Number of rating changes detected
  - Number of emails queued
  - Example: "Checked 1,243 monitors. Found 17 rating changes. Queued 17 emails."

### Verify Success
- Check `rating_changes` table for new rows: `SELECT * FROM rating_changes WHERE created_at > NOW() - INTERVAL '1 hour';`
- Check `pending_emails` table for new alert emails: `SELECT COUNT(*) FROM pending_emails WHERE subject LIKE '%rating%' AND created_at > NOW() - INTERVAL '1 hour';`

## Cron Schedule

Add to `/etc/cron.d/caregist`:

```cron
# Run monitor alerts daily at 08:00
0 8 * * * www-data cd /home/caregist && /home/caregist/.venv/bin/python3 tools/send_monitor_alerts.py >> /var/log/caregist/monitor-alerts.log 2>&1
```

Or more frequently (e.g., every 6 hours) if you want faster alert delivery:

```cron
0 0,6,12,18 * * * www-data ...
```

## Access Control
- Only Pro+ users (tier in api_keys) can create monitors
- Script only checks monitors owned by Pro+ users
- If a user downgrades to Free, their monitors become inactive (not checked)

## Monitoring
- **Failure signal**: No emails queued for 24+ hours despite active monitors
- **Performance baseline**: Should process 10,000+ monitors per minute
- **Alerting**: Log to syslog. Failures are logged to Sentry via error handler.

## Manual Inspection

```sql
-- See all active monitors
SELECT user_id, provider_id, provider_name, last_rating, last_alert_sent_at
FROM provider_monitors WHERE is_active = true
ORDER BY last_alert_sent_at DESC;

-- See recent rating changes
SELECT * FROM rating_changes ORDER BY created_at DESC LIMIT 20;

-- See pending alert emails
SELECT to_email, subject, created_at FROM pending_emails 
WHERE subject LIKE '%rating%' AND status = 'pending'
ORDER BY created_at DESC;
```

## Throttling
Each monitor respects `last_alert_sent_at` watermark. Default behavior:
- First rating change: email sent immediately
- Subsequent changes within 24 hours: no email (prevents spam)
- After 24 hours: next change triggers new email

To override, manually update the watermark:

```sql
UPDATE provider_monitors 
SET last_alert_sent_at = NOW() - INTERVAL '25 hours'
WHERE id = 123;
```

## Troubleshooting

**"No such table: provider_monitors"**
- Migration 001 not applied. Run `python3 db/apply_migrations.py`

**Emails queued but not sending**
- Emails are queued to `pending_emails`. The drain runs on health check. If stuck, run `python3 tools/flush_email_queue.py`

**User not receiving alerts**
- Check user tier: must be Pro+ (`SELECT tier FROM api_keys WHERE user_id = X`)
- Check monitor is active: `SELECT is_active FROM provider_monitors WHERE user_id = X`
- Check last_alert_sent_at is not blocking: `SELECT last_alert_sent_at FROM provider_monitors WHERE user_id = X`
- Check user has verified email: `SELECT is_verified FROM users WHERE id = X`

**Too many alerts**
- Increase `last_alert_sent_at` throttle window in the script, or manually update monitors
