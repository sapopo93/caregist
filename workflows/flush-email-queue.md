# Workflow: Flush Email Queue

## Overview
Manually drains the `pending_emails` table and sends outstanding emails via Resend. Use when the automatic health-check drain isn't keeping up, or after a Resend outage clears.

## Script Location
`tools/flush_email_queue.py`

## How the Email Queue Works
Emails are queued to the `pending_emails` table by any part of the system (enquiries, verification, alerts, digests). The API still performs a small opportunistic drain on `/api/v1/health`, but production should also run this script on a dedicated schedule so digests and alerts do not depend on incidental health traffic.

## Prerequisites
- Python 3.12+, venv activated
- `.env` with:
  - `DATABASE_URL` (Neon or PostgreSQL)
  - `RESEND_API_KEY`
  - `ENQUIRY_FROM_EMAIL` — the From address (`noreply@caregist.co.uk`)

## Running Manually

```bash
cd /Users/user/CareGist
source .venv/bin/activate
python3 tools/flush_email_queue.py
```

### Expected Output
```
Processing email queue...
  Sent: welcome@example.com — "Verify your CareGist email"
  Sent: user@agency.co.uk — "New registrations in your area"
  Failed: bad@addr — status 422 (attempt 1/3)
Queue flush complete: 47 sent, 1 failed (will retry)
```

### Verify Success
```sql
-- Check how many are still pending
SELECT status, COUNT(*) FROM pending_emails GROUP BY status;

-- Check for failed emails that won't retry (3 attempts exhausted)
SELECT to_email, subject, attempts, status, created_at 
FROM pending_emails 
WHERE attempts >= 3 AND status = 'pending';
```

## When to Use

| Situation | Action |
|-----------|--------|
| Digest emails are backed up | Run flush — the health-check drain is only a small safety net |
| Resend was down and has recovered | Run flush to clear backlog |
| New user verification emails are delayed | Run flush + check Resend API status |
| Testing email delivery locally | Run flush after queuing a test email |

## Batch Size
Default behavior runs larger batches and multiple passes so backlog can be drained quickly. Keep a cron or systemd timer in place even if the health endpoint is polled regularly.

## Resend API Limits
Resend free tier: 100 emails/day. Production (pro+): 50,000/day. If you hit rate limits, emails fail and increment `attempts`. They will retry on the next flush (up to 3 total attempts).

```sql
-- Check Resend-facing failures
SELECT to_email, subject, attempts, created_at 
FROM pending_emails 
WHERE status = 'pending' AND attempts > 0
ORDER BY created_at;
```

## Troubleshooting

**"RESEND_API_KEY not set"**
- Add `RESEND_API_KEY=re_...` to your `.env` file

**Emails queued but not sending in production**
- Check the dedicated cron or timer is still running
- Check the API is receiving health check traffic (the opportunistic drain still runs on `/api/v1/health`)
- Run flush script manually
- Check `RESEND_API_KEY` is set in the server's `.env`

**"status 422" from Resend**
- Invalid email address in `to_email` field
- Check the email address in `pending_emails` table
- Update or delete the stuck record manually

**Same email sent multiple times**
- Check `pending_emails.status` — rows aren't marked `sent` until Resend returns 200/201
- If Resend timed out mid-send, the row stays `pending` and retries (Resend handles dedup on their side with message IDs)
