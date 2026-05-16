# Runbook: Stuck Email Recovery

**Applies to:** Transactional email sent via Resend from `caregist.co.uk`
**Related runbooks:** [`workflows/flush-email-queue.md`](flush-email-queue.md), [`workflows/secret-rotation-resend.md`](secret-rotation-resend.md)

---

## Overview

Caregist sends transactional email (monitor alerts, weekly movers digest, account notifications) via the Resend API. This runbook covers how to diagnose and recover from stuck or failed email sends, including manual queue unstick, requeue of failed sends, DLQ extraction, and force-resend after fixing the root cause.

---

## Quick Triage

```bash
# 1. Check email log for recent failures
tail -100 /var/log/caregist/email.log | grep -E "(ERROR|FAIL|ResendError|status_code)"

# 2. Check API service health
sudo systemctl status caregist-api
curl -s http://localhost:8000/api/v1/health

# 3. Check Resend API key validity
# If RESEND_API_KEY is invalid, all sends will fail with 401.
# See secret-rotation-resend.md for rotation procedure.

# 4. Check outbound queue size (if a queue table exists)
psql "$DATABASE_URL" << 'SQL'
SELECT status, COUNT(*) as count
FROM email_queue
GROUP BY status
ORDER BY status;
SQL
```

---

## Common Failure Scenarios

### Scenario 1: RESEND_API_KEY invalid or expired

**Symptoms:** All email sends failing with `401 Unauthorized` or `ResendError: Invalid API key`.

**Resolution:**

1. Verify the key in `.env`:
   ```bash
   grep RESEND_API_KEY /home/caregist/CareGist/.env
   ```
2. Test the key manually:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" \
     -H "Authorization: Bearer <RESEND_API_KEY>" \
     "https://api.resend.com/emails"
   # Expected: 200 (empty list) or 405 (method not allowed — key is valid but endpoint is POST-only)
   ```
3. If invalid, rotate the key: see [`workflows/secret-rotation-resend.md`](secret-rotation-resend.md).
4. After key update and service restart, re-run any failed sends (see below).

---

### Scenario 2: Queue stuck — emails in `pending` state not progressing

**Symptoms:** `email_queue` shows many rows with `status = 'pending'` or `status = 'processing'` that are not moving; no recent send attempts in `email.log`.

**Steps to unstick:**

1. Check if the worker/task that processes the queue is still running:
   ```bash
   sudo systemctl status caregist-api
   # Look for the email queue processor in process list
   ps aux | grep -E "(send_email|email_worker|queue)"
   ```
2. If the API is healthy but the queue is stalled, restart it to reset in-memory queue state:
   ```bash
   sudo systemctl restart caregist-api
   ```
3. After restart, watch `email.log` for 2–3 minutes:
   ```bash
   tail -f /var/log/caregist/email.log
   ```
4. If sends resume, monitor until the queue drains. Check queue size periodically:
   ```sql
   SELECT status, COUNT(*) FROM email_queue GROUP BY status;
   ```

---

### Scenario 3: Failed sends — stuck in `failed` or `error` state

**Symptoms:** `email_queue` shows rows with `status = 'failed'` and `retry_count >= MAX_RETRIES`; the root cause has been fixed.

**Steps to requeue:**

1. Identify failed records:
   ```sql
   SELECT id, recipient_email, template, retry_count, last_error, created_at
   FROM email_queue
   WHERE status = 'failed'
   ORDER BY created_at DESC
   LIMIT 50;
   ```
2. After fixing the root cause (key rotation, service restart, etc.), reset failed records to `pending`:
   ```sql
   UPDATE email_queue
   SET status = 'pending', retry_count = 0, last_error = NULL, next_retry_at = NOW()
   WHERE status = 'failed'
     AND created_at > NOW() - INTERVAL '24 hours';
   -- Adjust the time window as appropriate.
   -- Do NOT blindly requeue very old failures — verify they are still relevant.
   ```
3. The queue processor will pick them up on its next cycle. Monitor `email.log`.

---

### Scenario 4: DLQ extraction

If the email system uses a dead-letter queue (DLQ) for permanently failed sends (e.g. `status = 'dead'` or a separate `email_dlq` table):

1. Extract DLQ records:
   ```sql
   SELECT id, recipient_email, template, payload, last_error, created_at
   FROM email_dlq
   ORDER BY created_at DESC;
   ```
   or
   ```sql
   SELECT id, recipient_email, template, payload, last_error, created_at
   FROM email_queue
   WHERE status = 'dead'
   ORDER BY created_at DESC;
   ```
2. For each record, assess whether the send is still needed (e.g. time-sensitive monitor alerts may no longer be relevant; account notifications may still be needed).
3. To force-resend a specific record after fixing the root cause:
   ```sql
   UPDATE email_queue
   SET status = 'pending', retry_count = 0, last_error = NULL, next_retry_at = NOW()
   WHERE id = '<record_id>';
   ```
   Or, if there is a tool script:
   ```bash
   cd /home/caregist/CareGist
   source .venv/bin/activate
   python tools/resend_email.py --queue-id <record_id>
   ```

---

### Scenario 5: Resend API rate limit hit

**Symptoms:** `email.log` shows `429 Too Many Requests`; sends are queuing faster than they are draining.

**Resolution:**

1. Check Resend dashboard → **Usage** to confirm the rate limit and current usage.
2. If a large batch (weekly digest, bulk alert) caused the spike, the queue will drain naturally once the rate limit window resets — do not force-resend.
3. If individual transactional sends are consistently hitting rate limits, the send concurrency in the application may need tuning. Raise as a code-level issue.

---

## Force-Resend After Root Cause Fix

After fixing whatever caused the failures (key rotation, service restart, DNS issue, etc.):

1. Confirm the service is healthy: `curl -s http://localhost:8000/api/v1/health`
2. Send a test email to yourself to confirm the fix works end-to-end before requeuing bulk failures.
3. Requeue failed records as described in Scenario 3 above.
4. Monitor `email.log` for at least 10 minutes to confirm sends are succeeding.
5. Check Resend dashboard → **Emails** to confirm delivery.

---

## Monitoring After Recovery

```bash
# Watch email log in real time
tail -f /var/log/caregist/email.log

# Queue drain progress (run every few minutes)
psql "$DATABASE_URL" -c "SELECT status, COUNT(*) FROM email_queue GROUP BY status;"

# Resend dashboard
# https://resend.com/emails — check Delivered / Bounced / Failed counts
```

---

## Escalation

If the queue is not draining after 30 minutes and the service appears healthy:

- Check Sentry for unhandled exceptions in the email dispatch path.
- Check Resend status page at [status.resend.com](https://status.resend.com) for platform-level incidents.
- Escalate to the technical lead with the triage query outputs and the last 100 lines of `email.log`.
