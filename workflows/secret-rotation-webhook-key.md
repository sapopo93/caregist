# Runbook: WEBHOOK_SECRET_KEY Rotation

**Estimated total time:** ~45 min (generation 5 min + re-encryption migration 15 min + deploy 10 min + verify 10 min + revocation 5 min)
**Applies to:** `WEBHOOK_SECRET_KEY` in `/home/caregist/CareGist/.env`
**Cross-reference:** Forge PR #5 (crypto implementation for HMAC-SHA256 webhook signatures and any at-rest encryption of the key)

---

## Background

`WEBHOOK_SECRET_KEY` is the HMAC-SHA256 secret used to sign outbound webhook payloads for Business-tier subscribers. Each delivery includes an `X-Caregist-Signature` header. Subscribers verify this header against the shared secret to confirm authenticity.

Unlike a simple API key rotation, rotating `WEBHOOK_SECRET_KEY` requires:

1. Generating a new key.
2. Running a **one-shot re-encryption migration** if any stored subscriber configurations embed a derivative of the old key (see Forge PR #5 for the exact crypto scope).
3. Deploying the new key to production.
4. Notifying affected Business-tier subscribers that their verification logic must be updated.
5. Revoking the old key only after subscribers have confirmed they have updated.

---

## When to Rotate

- **Suspected compromise** — the key may have been exposed. Rotate immediately; coordinate subscriber notification in parallel.
- **Annual standing schedule** — rotate once per year as hygiene.
- **Developer departure** — if the departing developer had access to the production `.env`.

---

## Pre-flight (5 min)

1. **EC2 SSH access** — confirm you can SSH to the production host. See [`workflows/deploy-ec2.md`](deploy-ec2.md).
2. **Database access** — confirm `psql "$DATABASE_URL"` connects successfully.
3. **Business-tier subscriber list** — pull the current list of active webhook subscriptions from the database:
   ```sql
   SELECT id, endpoint_url, organisation_name, created_at
   FROM webhook_subscriptions
   WHERE active = TRUE
   ORDER BY created_at;
   ```
   Record this list. You will need to notify each subscriber.
4. **No in-flight webhook deliveries** — check that the delivery queue is not in the middle of a high-volume dispatch:
   ```bash
   tail -20 /var/log/caregist/webhooks.log
   # Look for any bulk delivery batches in progress.
   ```
5. **Open a notepad** — record rotation start timestamp (UTC), your name, reason, and the subscriber list.

---

## Step 1: Generate a New Key (5 min)

Generate a cryptographically secure 256-bit key:

```bash
# On any secure machine (or the EC2 host)
python3 -c "import secrets; print(secrets.token_hex(32))"
```

This produces a 64-character hex string. Record it securely (password manager only — do not paste into Slack or any log).

---

## Step 2: Run the Re-encryption Migration (15 min)

> **Check Forge PR #5** to confirm the exact scope of data that must be re-encrypted. If `WEBHOOK_SECRET_KEY` is used only for outbound HMAC signing (not for encrypting stored data), you may skip the re-encryption step and go directly to Step 3.

If re-encryption is required:

```bash
ssh ubuntu@<EC2_IP>
cd /home/caregist/CareGist
source .venv/bin/activate

# Export both old and new keys for the migration script.
# The migration script should accept OLD_WEBHOOK_SECRET_KEY and NEW_WEBHOOK_SECRET_KEY.
OLD_WEBHOOK_SECRET_KEY="<old_key>" \
NEW_WEBHOOK_SECRET_KEY="<new_key>" \
python db/migrate_webhook_key.py
```

Verify the migration completed without errors. The script should print a count of rows re-encrypted and exit with code 0.

If the migration script does not exist yet, raise this as a blocker — do not proceed with rotation until the migration path is confirmed.

---

## Step 3: Deploy the New Key (10 min)

1. Update the env file on EC2:
   ```bash
   sudo nano /home/caregist/CareGist/.env
   # Find WEBHOOK_SECRET_KEY= and replace with the new key.
   # Save and close.
   ```
2. Restart the API service:
   ```bash
   sudo systemctl restart caregist-api
   sudo systemctl status caregist-api
   curl -s http://localhost:8000/api/v1/health
   ```

---

## Step 4: Notify Subscribers (parallel with Step 3)

Send each active Business-tier subscriber the following notification:

```
Subject: Caregist webhook signing key rotation — action required by [DATE]

We are rotating our webhook signing key on [DATE UTC].

After [DATE + 48h], signatures generated with the old key will no longer be valid.

Please update your webhook verification to accept signatures generated with the new key:

  New signing key: [INSERT NEW KEY — send via secure channel, not email]

If you use our SDK or follow our verification docs, only the key value changes — the 
algorithm (HMAC-SHA256, X-Caregist-Signature header) remains identical.

If you have questions, contact support@caregist.co.uk.
```

**Important:** Send the new key value via a separate secure channel (e.g. 1Password share, encrypted message), not in the same email.

---

## Step 5: Verify Deliveries (10 min)

After deploying the new key, trigger a test webhook delivery to a subscriber endpoint you control and verify the signature:

```bash
# On EC2
curl -s http://localhost:8000/api/v1/internal/webhooks/test \
  -H "Authorization: Bearer $API_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"subscription_id": "<test_subscription_id>"}'
```

Check the recipient endpoint received the request and that the signature is valid using the new key.

Also check the webhook audit log:
```sql
SELECT id, subscription_id, delivered_at, status_code, signature_valid
FROM webhook_delivery_log
ORDER BY delivered_at DESC
LIMIT 20;
```

---

## Step 6: Revoke the Old Key (5 min)

After the grace period has expired and all subscribers confirm they have updated:

1. Confirm no active subscriptions are still using the old key (check `webhook_delivery_log` for any `signature_valid = false` entries that indicate a subscriber still using the old key).
2. The old key is already inactive (it was replaced in `.env` in Step 3). Confirm it is not stored anywhere else:
   ```bash
   grep -r "WEBHOOK_SECRET_KEY" /home/caregist/CareGist/ --include="*.env*" --include="*.bak"
   ```
3. Remove any backup files containing the old key.
4. Update the password manager entry.

---

## Rollback

If the new key breaks delivery and you need to revert quickly:

1. Replace `WEBHOOK_SECRET_KEY` in `.env` with the old key.
2. Restart the service.
3. Re-run the re-encryption migration in reverse (old and new keys swapped).
4. Notify subscribers that the rotation was aborted and the old key is still active.

---

## Post-rotation

1. **Password manager** — update `WEBHOOK_SECRET_KEY` entry with `last_rotated_at`.
2. **Audit log check** — after 72 hours, verify no `signature_valid = false` entries remain in `webhook_delivery_log` (which would indicate a subscriber still using the old key).
3. **Schedule next rotation** — calendar reminder 12 months from today. Owner: `ops@caregist.co.uk`. Title: "WEBHOOK_SECRET_KEY rotation (annual hygiene)".
4. If triggered by a compromise, file an incident summary at `docs/incidents/YYYY-MM-DD-webhook-key-exposure.md`.

---

## Standing Schedule

| Item | Detail |
|---|---|
| Frequency | Annually |
| Owner | `ops@caregist.co.uk` |
| Scope | `WEBHOOK_SECRET_KEY` |
| Grace period for subscribers | 48 hours (coordinate in advance) |
