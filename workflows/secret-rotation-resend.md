# Runbook: Resend API Key Rotation

**Estimated total time:** ~20 min
**Applies to:** `RESEND_API_KEY` in `/home/caregist/CareGist/.env`
**Pattern:** Mirrors [`workflows/secret-rotation-stripe.md`](secret-rotation-stripe.md) (Cog PR #1)

---

## When to Rotate

Rotate the Resend API key in any of these situations:

- **Suspected compromise** — the key may have been exposed in logs, error messages, Slack, or git history. Rotate immediately; treat as an incident.
- **Six-monthly standing schedule** — every 6 months regardless of incidents.
- **Developer departure** — whenever a team member with Resend dashboard access leaves.
- **Untrusted environment** — if the key was copied to a laptop, staging environment, or CI system that is no longer trusted.

---

## Pre-flight (5 min)

Complete all checks before generating a new key.

1. **Resend dashboard access** — confirm you can log in at [resend.com](https://resend.com) and have permission to create and revoke API keys.
2. **EC2 SSH access** — confirm you can SSH to the production host and edit `/home/caregist/CareGist/.env`. See [`workflows/deploy-ec2.md`](deploy-ec2.md).
3. **No in-flight email sends** — check that no large batch send (e.g. weekly movers digest, monitor alerts) is in progress:
   ```bash
   # On EC2
   sudo systemctl status caregist-api
   tail -20 /var/log/caregist/email.log
   ```
4. **Open a notepad** — record rotation start timestamp (UTC), your name, reason for rotation.

---

## Key Rotation Procedure (10 min)

> **Note:** Resend does not offer a grace-period overlap like Stripe's rolling window. Once you revoke the old key, any in-flight sends using it will fail. Complete steps 1–6 quickly to minimise the gap.

1. Log in to [resend.com](https://resend.com) → **API Keys**.
2. Click **Create API Key**. Name it `caregist-production-YYYY-MM-DD`.
3. Set permissions to **Full Access** (required for sending and domain management).
4. **Copy the new key** immediately — Resend shows it only once.
5. SSH to EC2:
   ```bash
   ssh ubuntu@<EC2_IP>
   ```
6. Update the env file:
   ```bash
   sudo nano /home/caregist/CareGist/.env
   # Find RESEND_API_KEY= and replace its value with the new key.
   # Save and close.
   ```
7. Restart the API service:
   ```bash
   sudo systemctl restart caregist-api
   # Wait ~5 seconds
   sudo systemctl status caregist-api
   curl -s http://localhost:8000/api/v1/health
   # Expected: {"status":"healthy",...}
   ```
8. Verify the new key works — trigger a test send:
   ```bash
   # Manually invoke the monitor-alerts tool (safe; it only sends to configured alert addresses)
   cd /home/caregist/CareGist
   source .venv/bin/activate
   python tools/send_monitor_alerts.py --dry-run
   # If --dry-run is not available, check logs after the next scheduled run instead.
   ```
   Alternatively, check `email.log` for a successful send in the next few minutes:
   ```bash
   tail -f /var/log/caregist/email.log
   ```
9. **Revoke the old key** — return to Resend dashboard → API Keys → locate the old key → **Revoke**. Do this immediately; do not leave the old key active.
10. Record rotation end timestamp in your notepad.

---

## Verification

After completing rotation, confirm:

- [ ] `GET /api/v1/health` returns HTTP 200.
- [ ] No `ResendError` or `401` entries in `email.log` after the restart.
- [ ] Old key is revoked in the Resend dashboard.
- [ ] `.env` contains only the new key (no stale copies).

---

## Rollback

Resend has no grace-period window. If the new key does not work:

1. In the Resend dashboard, create another new key immediately (do not try to un-revoke the old one — it is gone).
2. Repeat steps 5–8 with the second new key.
3. File an incident note describing what went wrong.

---

## Post-rotation

1. **Password manager** — update the `last_rotated_at` field for the Resend credentials entry.
2. **Schedule next rotation** — create a calendar reminder 6 months from today. Owner: `ops@caregist.co.uk`. Title: "Resend API key rotation (standing hygiene)".
3. If this rotation was triggered by a suspected compromise, file an incident summary at `docs/incidents/YYYY-MM-DD-resend-key-exposure.md` using the post-mortem template in [`workflows/incident-response.md`](incident-response.md).

---

## Standing Schedule

| Item | Detail |
|---|---|
| Frequency | Every 6 months |
| Owner | `ops@caregist.co.uk` |
| Calendar entry | "Resend API key rotation (standing hygiene)" — recurring, 6-month interval |
| Scope | `RESEND_API_KEY` every cycle |
