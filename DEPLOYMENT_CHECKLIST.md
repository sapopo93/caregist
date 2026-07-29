# CareGist Production Deployment Checklist

**Last updated:** 2026-06-29
**Purpose:** Deployment-owner checklist for taking the hardened codebase from staging to production.
**Rule:** Do not send public production traffic until every required item is complete and evidenced.

## 0. Release Gate

### Required Before Production

- [ ] CI is green on the exact commit being deployed.
- [ ] Staging deploy uses the same build artifact or commit as production.
- [ ] Staging smoke tests pass with `CAREGIST_REQUIRE_DATABASE=1`.
- [ ] Stripe webhook test events pass against staging.
- [ ] Resend live email delivery is confirmed.
- [ ] Redis-backed rate limiting is confirmed.
- [ ] Database backups/PITR are enabled.
- [ ] One restore drill has completed successfully.
- [ ] Production monitoring and alerting are live.

### Current Code Gates

- [x] Session cookie is `HttpOnly`, `Secure` in production, and `SameSite=strict`.
- [x] Protected frontend routes fail closed on missing/invalid/unverifiable session.
- [x] API keys authenticate by hash only.
- [x] Production startup requires webhook encryption key and Redis URL for non-local DB deployments.
- [x] Stripe webhook side effects are transactionally deduplicated.
- [x] Profile checkout requires an approved provider claim.
- [x] Frontend dependency audit is clean.

## 1. Secrets

Create a production secret in AWS Secrets Manager or the selected hosting secret manager. Required backend values:

```json
{
  "database_url": "postgresql://...",
  "api_master_key": "cm_...",
  "stripe_secret_key": "sk_live_...",
  "stripe_webhook_secret": "whsec_...",
  "stripe_price_alerts_pro": "price_...",
  "stripe_price_starter": "price_...",
  "stripe_price_pro": "price_...",
  "stripe_price_pro_seat": "price_...",
  "stripe_price_business": "price_...",
  "stripe_price_profile_enhanced": "price_...",
  "stripe_price_profile_premium": "price_...",
  "stripe_price_profile_sponsored": "price_...",
  "resend_api_key": "re_...",
  "caregist_to_support_token": "...",
  "support_internal_token": "...",
  "hermes_internal_token": "...",
  "webhook_secret_key": "<32-byte AES-GCM key>",
  "redis_url": "rediss://..."
}
```

Checklist:

- [ ] Set `AWS_SECRETS_MANAGER_SECRET_ID` or equivalent host secret references.
- [ ] Confirm the backend can read the secret in staging.
- [ ] Confirm `WEBHOOK_SECRET_KEY` decodes to exactly 32 bytes for AES-GCM.
- [ ] Confirm no production secret is present in tracked files.
- [ ] Do not set `NEXT_PUBLIC_API_KEY`.

## 2. Redis

- [ ] Provision Redis with TLS/AUTH where supported.
- [ ] Set `REDIS_URL` in the production secret manager.
- [ ] Confirm backend startup fails when `REDIS_URL` is missing against a non-local DB.
- [ ] Confirm rate-limit requests use Redis, not in-memory fallback.
- [ ] Add Redis availability and latency alerts.

## 3. Database

### Provisioning

- [ ] PostgreSQL 14+ is available.
- [ ] PostGIS is enabled if provider geospatial queries are used.
- [ ] Connection pool limits match the deployment worker count.
- [ ] Automated backups or PITR are enabled before migrations.

### Migrations

For staging:

```bash
python3 db/apply_migrations.py --target staging
```

For production:

```bash
python3 db/apply_migrations.py --target production --confirm-production-backup
```

Required checks:

- [ ] Run migrations in staging first.
- [ ] `STAGING_DATABASE_URL` and `PROD_DATABASE_URL` are both set and point to different databases.
- [ ] Confirm migrations through `031_enforce_hashed_api_keys.sql` are recorded in `schema_migrations`.
- [ ] Confirm `api_keys.key_hash` is `NOT NULL`.
- [ ] Confirm `api_keys.key` is `NULL` for all rows.
- [ ] Confirm no production migration is run before a backup snapshot exists.

Example verification:

```sql
SELECT filename FROM schema_migrations ORDER BY filename DESC LIMIT 5;
SELECT COUNT(*) FROM api_keys WHERE key_hash IS NULL OR key IS NOT NULL;
```

## 4. Backups And Restore

- [ ] Enable Neon PITR/branch snapshots, RDS 7-day retention, or equivalent backup policy.
- [ ] Restore a snapshot into staging.
- [ ] Run smoke tests against the restored database.
- [ ] Record restore duration, RPO, and RTO.
- [ ] Schedule a monthly restore drill.

Acceptance criteria: restore completes in under 30 minutes and smoke tests pass.

## 5. Build And Local Verification

Run before tagging/releasing:

```bash
pytest
cd frontend && npm test
cd frontend && npm run build
cd frontend && npm audit
```

Optional backend dependency check in a Python 3.12 virtualenv:

```bash
python3.12 -m venv /tmp/caregist-pipcheck
/tmp/caregist-pipcheck/bin/python -m pip install -r requirements.txt
/tmp/caregist-pipcheck/bin/python -m pip check
```

## 6. Staging Smoke Tests

Run against the deployed staging URL:

```bash
CAREGIST_APP_URL=https://staging.caregist.co.uk \
CAREGIST_REQUIRE_DATABASE=1 \
python3 tools/verify-deploy.py
```

Run a full lead/export smoke. This sends a real email:

```bash
CAREGIST_APP_URL=https://staging.caregist.co.uk \
CAREGIST_REQUIRE_DATABASE=1 \
CAREGIST_LEAD_EMAIL=ops@example.com \
python3 tools/verify-deploy.py
```

Manual staging checks:

- [ ] Signup -> email verify -> login.
- [ ] Protected route access redirects unauthenticated users.
- [ ] Starter checkout creates a Stripe checkout session.
- [ ] Stripe dashboard test event reaches `/api/v1/billing/webhook`.
- [ ] Profile checkout fails without an approved claim.
- [ ] Profile checkout succeeds for an approved claim.
- [ ] Redis-backed rate limiting blocks over-quota traffic.

## 7. Production Smoke Tests

Immediately after deploy:

```bash
CAREGIST_APP_URL=https://www.caregist.co.uk \
CAREGIST_REQUIRE_DATABASE=1 \
CAREGIST_SMOKE_ATTEMPTS=15 \
CAREGIST_SMOKE_RETRY_DELAY_SECONDS=20 \
python3 tools/verify-deploy.py
```

Then run a lead/export smoke with an operational inbox:

```bash
CAREGIST_APP_URL=https://www.caregist.co.uk \
CAREGIST_REQUIRE_DATABASE=1 \
CAREGIST_LEAD_EMAIL=ops@example.com \
python3 tools/verify-deploy.py
```

The scheduled workflow `.github/workflows/production-smoke.yml` runs the public smoke every 30 minutes and on pushes to `main`.

## 8. Monitoring And Alerts

- [ ] Sentry project configured for frontend and backend.
- [ ] Error-rate alert configured at > 5% over 5 minutes.
- [ ] P99 latency alert configured at > 2 seconds.
- [ ] Database CPU/connections/storage alerts configured.
- [ ] Redis availability and latency alerts configured.
- [ ] Stripe webhook failure alert configured.
- [ ] Resend bounce/failure monitoring configured.
- [ ] On-call escalation path documented.

## 9. Launch-Day Verification

- [ ] Monitor Sentry for the first hour.
- [ ] Confirm `/api/v1/health` and frontend `/api/health/directory` are healthy.
- [ ] Confirm database connection pool usage is below 80%.
- [ ] Confirm Redis is serving rate-limit checks.
- [ ] Confirm signup, login, checkout, claim, lead, and export flows.
- [ ] Review audit logs for unexpected admin or master-key use.

## 10. Known Post-Launch Work

Complete before broad GA:

- [ ] Re-tier or revoke existing API keys on subscription downgrade.
- [ ] Add master API-key rotation and audit alerts.
- [ ] Add a constant-time floor for forgot-password email enumeration resistance.
- [ ] Add CI integration tests that replay migrations against a real Postgres service.
- [ ] Add retention jobs for analytics/audit/email tables.
- [ ] Validate `X-Forwarded-For` only from trusted proxies.
- [ ] Document forward-only migration rollback strategy.

## Rollback

If the application deploy fails before migrations:

```bash
git revert HEAD
git push origin main
```

If migrations were applied, treat rollback as a database restore unless a forward-fix migration is safer. Restore only from a verified backup snapshot and rerun smoke tests before sending traffic.

## Support References

- Production status: `PRODUCTION_READY.md`
- Historical audit: `PRODUCTION_AUDIT.md`
- Public smoke script: `tools/verify-deploy.py`
- Production smoke workflow: `.github/workflows/production-smoke.yml`
