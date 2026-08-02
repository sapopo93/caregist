# Runbook: Stripe Key Rotation

**Estimated total time:** ~35 min (API secret 15 min + webhook 10 min + checks 10 min)
**Applies to:** All live Stripe credentials in `/home/caregist/CareGist/.env`

---

## When to Rotate

Rotate Stripe credentials in any of these situations:

- **Suspected compromise** — a key may have been exposed (logs, error messages, Slack, git history). Treat as an incident; rotate immediately before post-mortem.
- **Six-monthly standing schedule** — every 6 months regardless of any incident. See [Standing Schedule](#standing-schedule).
- **Developer departure** — whenever a team member with Stripe dashboard access leaves.
- **Untrusted environment** — if a key was copied to a laptop, staging server, or CI environment that is no longer trusted or has been decommissioned.

---

## Pre-flight (5 min)

Complete all checks before touching any key.

1. **Stripe dashboard access** — confirm you can log in and have Developer or Owner role at [dashboard.stripe.com](https://dashboard.stripe.com). If you need elevated access, arrange it before starting.
2. **EC2 SSH access** — confirm you can SSH to the production host and edit `/home/caregist/CareGist/.env`. See `workflows/deploy-ec2.md` for the canonical deploy path.
3. **No in-flight operations** — confirm no deploy, database migration, or feed cycle is running. Check:
   ```bash
   # On EC2
   sudo systemctl status caregist-api
   tail -20 /var/log/caregist/api.log
   tail -20 /var/log/caregist/feed-cycle.log
   ```
4. **Open a notepad** — record: rotation start timestamp (UTC), your name, reason for rotation. You will fill in end timestamp at the end.

---

## Live API Secret Key Rotation (15 min)

> **Grace period note:** Stripe gives a **12-hour grace period** after rolling the live secret key. During this window the OLD key remains valid, giving you a safe rollback path. After 12 hours, the old key is permanently gone.

1. Go to [Stripe Dashboard → Developers → API keys](https://dashboard.stripe.com/apikeys).
2. Next to the live secret key, click **Roll**. Stripe will prompt you to confirm. Confirm.
3. **Copy the new key** (`sk_live_xxxxx`). Do NOT close or navigate away from the dashboard page until you have verified the new key is working — you may need to roll back.
4. SSH to EC2:
   ```bash
   ssh ubuntu@<EC2_IP>
   ```
5. Open the production env file:
   ```bash
   sudo nano /home/caregist/CareGist/.env
   ```
6. Find the line starting with `STRIPE_SECRET_KEY=` and replace the value with the new key. Save and close.
7. Reload the API service:
   ```bash
   # Systemd (primary)
   sudo systemctl restart caregist-api

   # Supervisor (if used instead)
   supervisorctl restart caregist-api
   ```
   Wait ~5 seconds, then verify the service is running:
   ```bash
   sudo systemctl status caregist-api
   curl -s http://localhost:8000/api/v1/health
   # Expected: {"status":"healthy",...}
   ```
8. **Verify the new key reaches Stripe** — run this from the EC2 host:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" \
     -u "${STRIPE_SECRET_KEY}:" \
     "https://api.stripe.com/v1/customers?limit=1"
   # Expected: 200
   ```
   If you get `401`, the env var was not updated correctly or the service did not reload. Do not proceed to the next step.
9. **Watch logs for 60 seconds:**
   ```bash
   sudo journalctl -u caregist-api -f --since "now"
   ```
   Look for any `401` errors from Stripe or `AuthenticationError` entries. If the log is clean after 60 seconds, the rotation is safe.
10. **Revoke the old key** — return to Stripe Dashboard → Developers → API keys → find the old key (marked "Rolling") → click **Revoke**. Do this now; do not wait for the 12-hour grace period to expire.
11. Record rotation end timestamp in your notepad.

---

## Webhook Signing Secret Rotation (10 min)

> **No grace period:** Unlike the API secret, webhook signing secrets have **no overlap window**. The old signature stops verifying the moment you roll. Steps 1–5 must be completed quickly. Stripe retries failed webhooks with exponential backoff for up to 3 days, so transient failures during the switchover will recover automatically — but minimise the gap.

1. Go to [Stripe Dashboard → Developers → Webhooks](https://dashboard.stripe.com/webhooks).
2. Click your production endpoint URL.
3. Click **Roll signing secret** (or "Reveal" → "Roll"). Confirm when prompted.
4. **Copy the new secret** (`whsec_xxxxx`). Act immediately — proceed to the next steps without delay.
5. On EC2, open `/home/caregist/CareGist/.env` and replace the value of `STRIPE_WEBHOOK_SECRET=` with the new secret:
   ```bash
   sudo nano /home/caregist/CareGist/.env
   ```
6. Reload the API service:
   ```bash
   sudo systemctl restart caregist-api
   ```
7. **Verify** — in the Stripe Dashboard, on the webhook endpoint page, click **Send test webhook** (choose any event type, e.g. `customer.created`). Watch application logs:
   ```bash
   sudo journalctl -u caregist-api -f --since "now"
   ```
   Look for an incoming webhook log entry with a `200` response. A `400` with signature mismatch means the env file or service reload did not apply correctly.
8. Record timestamp.

---

## Price ID Safety Check (2 min)

After any rotation, confirm the `STRIPE_PRICE_*` env vars still reference **live** price IDs (format: `price_...`), not test IDs (format: `price_test_...`). Rotations sometimes surface staging config that has leaked into production.

On EC2, run:
```bash
grep 'STRIPE_PRICE_' /home/caregist/CareGist/.env
```

Verify the following vars are all present and start with `price_` (not `price_test_`):

| Variable | Expected format |
|---|---|
| `STRIPE_PRICE_ALERTS_PRO` | `price_...` |
| `STRIPE_PRICE_STARTER` | `price_...` |
| `STRIPE_PRICE_PRO` | `price_...` |
| `STRIPE_PRICE_PRO_SEAT` | `price_...` |
| `STRIPE_PRICE_BUSINESS` | `price_...` |
| `STRIPE_PRICE_PROFILE_ENHANCED` | `price_...` |
| `STRIPE_PRICE_PROFILE_PREMIUM` | `price_...` |
| `STRIPE_PRICE_PROFILE_SPONSORED` | `price_...` |

If any value starts with `price_test_`, stop. Replace it with the correct live price ID from the Stripe Dashboard → Products.

---

## Post-rotation (5 min)

1. **Password manager** — update the `last_rotated_at` field for the Stripe credentials entry. Note the rotation date and the initiating engineer.
2. **Schedule next rotation** — create a calendar reminder 6 months from today. Owner: `ops@caregist.co.uk`. Title: "Stripe key rotation (standing hygiene)".
3. **Incident-driven rotation only** — if this rotation was triggered by a suspected compromise, write a brief incident summary covering:
   - Trigger and how the key was potentially exposed
   - Timeline (start to revocation of old key)
   - Any webhooks that failed and whether they recovered
   - Actions taken to prevent recurrence

   File the summary as `docs/incidents/YYYY-MM-DD-stripe-key-exposure.md`.

---

## Rollback

### Live API secret rollback

The old key remains valid for **12 hours** from the time you rolled it.

To roll back within that window:
1. Retrieve the old key value from your notepad or password manager (you should have recorded it before rotating).
2. On EC2, restore the old value in `/home/caregist/CareGist/.env`.
3. Restart the API service: `sudo systemctl restart caregist-api`.
4. Verify with the Stripe curl check (step 8 of the API rotation section).
5. Investigate the failure that triggered rollback. Plan a clean rotation once the root cause is resolved.

**After 12 hours:** The old key is permanently gone. You cannot recover it. If the new key is also broken, your only option is to roll again from the Stripe dashboard.

### Webhook secret rollback

There is no grace period. If the new webhook secret broke signature verification:

1. Return to Stripe Dashboard → Webhooks → your endpoint → **Roll signing secret** again immediately.
2. Copy the newly generated secret.
3. Update `STRIPE_WEBHOOK_SECRET` in `/home/caregist/CareGist/.env`.
4. Restart the API: `sudo systemctl restart caregist-api`.
5. Send a test webhook from the dashboard to confirm it is now verifying correctly.

Any webhooks delivered between the bad roll and the corrected update will have been rejected. Stripe retries with exponential backoff for up to 3 days, so most will recover automatically. Check the Stripe Dashboard → Webhooks → your endpoint → **Webhook attempts** log for permanent failures. You can replay them manually from the dashboard.

---

## Standing Schedule

| Item | Detail |
|---|---|
| Frequency | Every 6 months |
| Owner | `ops@caregist.co.uk` |
| Calendar entry | "Stripe key rotation (standing hygiene)" — recurring, 6-month interval |
| Scope | `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` every cycle |
| Annual audit | Each cycle: re-run `grep 'STRIPE_PRICE_' .env.example` to check for newly added price vars that should be added to this runbook's safety check table |

This rotation is mandatory regardless of whether any incident has occurred in the preceding 6 months.
