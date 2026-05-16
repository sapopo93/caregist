# Runbook: Sentry DSN Rotation

**Estimated total time:** ~15 min
**Applies to:** `SENTRY_DSN` in `/home/caregist/CareGist/.env` (backend) and `NEXT_PUBLIC_SENTRY_DSN` / `SENTRY_DSN` in the frontend build environment
**Pattern:** Mirrors [`workflows/secret-rotation-stripe.md`](secret-rotation-stripe.md) (Cog PR #1)

---

## When to Rotate

Rotate the Sentry DSN in any of these situations:

- **Suspected compromise** — the DSN was exposed publicly (e.g. in a public git commit, client-side JS bundle in a way that allows abuse). Rotate immediately.
- **Project migration** — moving to a new Sentry project or organisation.
- **Annual standing schedule** — DSNs are lower risk than API keys (they only accept inbound events), but rotate annually as hygiene or if abuse is detected (e.g. event quota exhausted by a third party).
- **Developer departure** — if the departing developer had admin access to the Sentry organisation.

> **Note on DSN risk profile:** A Sentry DSN allows anyone who possesses it to *submit events to your project*. It does not grant read access to your event data. The primary abuse risk is event-quota exhaustion. Rotate if you detect unexpected event volume from unknown sources.

---

## Pre-flight (3 min)

1. **Sentry organisation access** — confirm you can log in to [sentry.io](https://sentry.io) (or your self-hosted Sentry) and have Owner or Manager role on the `caregist` organisation.
2. **EC2 SSH access** — confirm you can SSH to the production host. See [`workflows/deploy-ec2.md`](deploy-ec2.md).
3. If frontend is deployed as a build artifact, confirm you have access to the CI/CD pipeline to trigger a rebuild.

---

## Rotation Procedure

### Backend DSN (8 min)

1. Log in to Sentry → **Settings** → **Projects** → `caregist-backend` (or your project name).
2. Navigate to **Client Keys (DSN)**.
3. Click **Generate New Key**. Note the new DSN (format: `https://<key>@<host>/<project_id>`).
4. SSH to EC2:
   ```bash
   ssh ubuntu@<EC2_IP>
   ```
5. Update the env file:
   ```bash
   sudo nano /home/caregist/CareGist/.env
   # Find SENTRY_DSN= and replace its value with the new DSN.
   # Save and close.
   ```
6. Restart the API service:
   ```bash
   sudo systemctl restart caregist-api
   sudo systemctl status caregist-api
   curl -s http://localhost:8000/api/v1/health
   ```
7. Verify Sentry is receiving events from the new DSN — trigger a test event:
   ```bash
   # On EC2, in the caregist virtualenv
   cd /home/caregist/CareGist
   source .venv/bin/activate
   python -c "import sentry_sdk; sentry_sdk.capture_message('DSN rotation test', level='info')"
   ```
   Confirm the test event appears in the Sentry project within ~30 seconds.
8. **Revoke the old DSN** — in Sentry → Client Keys → find the old key → **Revoke**. This immediately stops accepting events from the old key.

### Frontend DSN (5 min)

The frontend uses `@sentry/nextjs`. The DSN is typically embedded at build time via environment variables (`NEXT_PUBLIC_SENTRY_DSN` and/or `SENTRY_DSN`).

1. Log in to Sentry → **Settings** → **Projects** → `caregist-frontend`.
2. Navigate to **Client Keys (DSN)** → **Generate New Key**.
3. Update the DSN in your CI/CD environment variables (GitHub Actions secrets or `.env` on the build host).
4. Trigger a new production build and deploy.
5. After deploy, verify error events from the frontend appear in Sentry under the correct project.
6. Revoke the old frontend DSN.

---

## Verification

- [ ] Backend health check passes after restart.
- [ ] Test Sentry event (`capture_message`) appears in the correct project.
- [ ] Old DSN is revoked in Sentry.
- [ ] No `SentryError` or transport errors in `api.log` after restart.
- [ ] Frontend events route to the correct project (check Sentry Issues after triggering a test client-side error).

---

## Rollback

If the new DSN is incorrect or not working:

1. In Sentry, generate another new key — do not try to un-revoke the old one.
2. Update `.env` and restart the service.
3. Verify as above.

---

## Post-rotation

1. **Password manager** — update the DSN entry with the new value and `last_rotated_at` date.
2. If this was triggered by suspected abuse (unexpected event volume), review Sentry's **Usage & Stats** to confirm event rate normalised after revoking the old key.
3. If triggered by a compromise, file an incident summary at `docs/incidents/YYYY-MM-DD-sentry-dsn-exposure.md`.

---

## Standing Schedule

| Item | Detail |
|---|---|
| Frequency | Annually, or on any suspected abuse |
| Owner | `ops@caregist.co.uk` |
| Scope | `SENTRY_DSN` (backend) + frontend Sentry project key |
