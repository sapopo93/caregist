# Runbook: Webhook Delivery Debugging

**Applies to:** Business-tier webhook subscriptions on `caregist.co.uk`

---

## Overview

Caregist delivers provider-change events to Business-tier subscriber endpoints via HTTP POST. Each delivery includes an `X-Caregist-Signature` HMAC-SHA256 header. This runbook covers how to diagnose and resolve delivery failures.

---

## Quick Triage

Start here when a subscriber reports missed events or when you spot delivery anomalies in monitoring.

```bash
# 1. Check webhook audit log — last 50 delivery attempts
psql "$DATABASE_URL" << 'SQL'
SELECT
  d.id,
  s.endpoint_url,
  d.event_type,
  d.delivered_at,
  d.status_code,
  d.signature_valid,
  d.retry_count,
  d.error_message
FROM webhook_delivery_log d
JOIN webhook_subscriptions s ON d.subscription_id = s.id
ORDER BY d.delivered_at DESC
LIMIT 50;
SQL

# 2. Check pipeline alert log for feed-level issues
psql "$DATABASE_URL" << 'SQL'
SELECT event, detail, created_at
FROM pipeline_alert_log
ORDER BY created_at DESC
LIMIT 20;
SQL

# 3. Check recent webhook-related API logs
sudo journalctl -u caregist-api --since "1 hour ago" | grep -i webhook | tail -50
```

---

## Common Failure Categories

### 1. Subscriber endpoint unreachable (connection refused / timeout)

**Symptoms:** `status_code` is null or 0; `error_message` contains `ConnectionError`, `TimeoutError`, or `ECONNREFUSED`.

**Checks:**

```bash
# From EC2, test reachability of the subscriber endpoint
curl -sv --max-time 10 -X POST "<subscriber_endpoint_url>" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

**Common causes:**
- Subscriber firewall blocking Caregist's EC2 egress IP. Ask subscriber to allowlist the EC2 IP.
- Subscriber endpoint is down or misconfigured.
- DNS resolution failure for the subscriber's domain.

**Resolution:** Contact the subscriber. The Caregist delivery system will retry automatically with exponential backoff (see retry logic below). If retries are exhausted, events are lost — you will need to replay them manually after the subscriber fixes their endpoint.

---

### 2. Subscriber returns 4xx

**Symptoms:** `status_code` in 400–499 range.

| Code | Likely cause |
|---|---|
| 400 | Subscriber is rejecting the payload format — check if their schema changed |
| 401 / 403 | Subscriber is enforcing auth that Caregist does not send — check their docs |
| 404 | Subscriber endpoint URL has changed — update subscription record |
| 422 | Payload validation failure on the subscriber side |

**Resolution:** Check `error_message` for any response body from the subscriber. Update the subscription `endpoint_url` if needed:

```sql
UPDATE webhook_subscriptions
SET endpoint_url = '<new_url>'
WHERE id = '<subscription_id>';
```

Reload the service or trigger a retry after fixing:

```bash
# Trigger manual retry for a specific failed delivery (if retry endpoint exists)
curl -X POST "http://localhost:8000/api/v1/internal/webhooks/retry/<delivery_id>" \
  -H "Authorization: Bearer $API_MASTER_KEY"
```

---

### 3. Signature verification failure (subscriber reports invalid signatures)

**Symptoms:** Subscriber's endpoint returns 400 or 403 with a message like "invalid signature"; `signature_valid = false` in `webhook_delivery_log`.

**Checks:**

1. Confirm the subscriber is using the correct key (`WEBHOOK_SECRET_KEY` from the most recent rotation).
2. Confirm the subscriber is computing HMAC-SHA256 over the raw request body (not a parsed/re-serialised version).
3. Confirm the subscriber is reading the full `X-Caregist-Signature` header value (format: `sha256=<hex_digest>`).

**Debug signature locally:**

```bash
# On EC2
source /home/caregist/CareGist/.venv/bin/activate
python3 << 'EOF'
import hmac, hashlib

secret = b"<WEBHOOK_SECRET_KEY>"
body = b'<exact_raw_payload_body>'
expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
print(expected)
EOF
```

Compare the output with the `X-Caregist-Signature` header logged for the delivery. If they match, the issue is on the subscriber side.

If they do not match, the key used at delivery time differs from `WEBHOOK_SECRET_KEY`. Check whether a key rotation occurred and whether the re-encryption migration ran correctly (see [`secret-rotation-webhook-key.md`](secret-rotation-webhook-key.md)).

---

### 4. TLS / certificate errors

**Symptoms:** `error_message` contains `SSL`, `certificate`, or `handshake`.

**Checks:**

```bash
# Test TLS from EC2
openssl s_client -connect <subscriber_host>:443 -servername <subscriber_host> < /dev/null
```

**Common causes:**
- Subscriber has an expired or self-signed TLS certificate.
- SNI mismatch.
- Subscriber's TLS version is below what the EC2 Python runtime accepts.

**Resolution:** The subscriber must fix their TLS configuration. Caregist does not disable certificate verification.

---

### 5. Retry logic exhausted

The delivery system retries failed deliveries with exponential backoff. Check the retry configuration:

```sql
-- Find deliveries that have exhausted retries
SELECT id, subscription_id, event_type, retry_count, status_code, error_message, delivered_at
FROM webhook_delivery_log
WHERE retry_count >= <MAX_RETRIES>
  AND status_code NOT BETWEEN 200 AND 299
ORDER BY delivered_at DESC;
```

After the subscriber fixes their endpoint, manually replay exhausted deliveries:

```bash
# Replay all exhausted deliveries for a subscription (adjust the script path as needed)
cd /home/caregist/CareGist
source .venv/bin/activate
python tools/replay_webhooks.py --subscription-id <id> --since "2026-05-01T00:00:00Z"
```

If no replay tool exists, manually re-trigger the events from `pipeline_alert_log` by querying for the relevant provider changes and dispatching them.

---

### 6. Feed pipeline not producing events

**Symptoms:** No new webhook deliveries despite new CQC changes being published; `pipeline_alert_log` shows no recent feed completion.

**Resolution:** See [`workflows/run-feed-cycle.md`](run-feed-cycle.md) and [`workflows/cqc-fallback-activation.md`](cqc-fallback-activation.md).

---

## Viewing the Full Audit Trail for a Subscription

```sql
SELECT
  d.*,
  s.endpoint_url,
  s.organisation_name
FROM webhook_delivery_log d
JOIN webhook_subscriptions s ON d.subscription_id = s.id
WHERE s.id = '<subscription_id>'
ORDER BY d.delivered_at DESC
LIMIT 100;
```

---

## Disabling a Subscription Temporarily

If a subscriber endpoint is causing repeated errors and impacting queue performance:

```sql
UPDATE webhook_subscriptions
SET active = FALSE, disabled_reason = 'Repeated delivery failures — contact subscriber', disabled_at = NOW()
WHERE id = '<subscription_id>';
```

Notify the subscriber. Re-enable once they confirm the endpoint is fixed:

```sql
UPDATE webhook_subscriptions
SET active = TRUE, disabled_reason = NULL, disabled_at = NULL
WHERE id = '<subscription_id>';
```

---

## Escalation

If you cannot identify the root cause within 30 minutes:

- Check Sentry for any unhandled exceptions in the webhook dispatch code.
- Review the most recent deploy for any changes to the webhook signing or delivery logic.
- Escalate to the technical lead with the output of the triage queries above.
