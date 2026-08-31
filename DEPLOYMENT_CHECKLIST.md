# CareGist Production Deployment Checklist

**Last updated:** 2026-08-09
**Purpose:** Deployment-owner checklist for taking the hardened codebase from staging to production.
**Rule:** Public directory traffic is allowed. Source collectors may run only in delivery-disabled shadow mode after the recovery and migration gates pass. Do not enable paid Radar, outbound delivery, or other commercial capabilities until every applicable item is complete and evidenced.

## Current Release-State Snapshot (2026-08-09)

The controlled catalogue-safety release is deployed at https://www.caregist.co.uk. The paid Radar release is **NO-GO** until the recovery, source-trust, legal, billing, and pilot gates below pass. Production health intentionally reports degraded/stale and checkout intentionally fails closed.

### Gates satisfied

- [x] **Final catalogue deployed:** Free Directory, Radar Regional, Radar National, Intelligence Feed Pilot, and quote-only Embedded Enterprise are the only public product surfaces.
- [x] **Stripe test and live modes reconciled explicitly:** each mode contains exactly four active Products and three active Prices with the approved lookup keys and amounts; all legacy Products and Prices are archived.
- [x] **Legacy sales paths retired:** `/full-dataset` permanently redirects to `/intelligence-feed`; legacy checkout endpoints remain fail-closed and legacy Price IDs are retained only for subscription replay compatibility.
- [x] **Release verification:** the deployed Git SHA is exposed by `/api/v1/version` and `/api/v1/health/liveness`; the exact-commit preview smoke workflow passes.
- [x] **Local validation:** 555 backend tests and 126 frontend tests pass; Ruff, TypeScript, the Next.js 16.2.12 production build, migration replay, and dependency audits pass.
- [x] **Customer-surface verification:** public routes, pricing, search-to-provider rendering, CQC attribution, legal pages, checkout denial, and source-status wording were verified with the Chrome browser plugin.
- [x] **Production recovery:** Neon is on Launch with seven-day history; a pre-migration recovery checkpoint and isolated point-in-time restore passed with 56,743 provider rows, 56,742 active rows, and zero duplicate canonical CQC location IDs.
- [x] **Database migration:** the pending chain through `049_cqc_signal_intelligence.sql` passed on an isolated Neon branch and production; provider counts were preserved, trusted-ledger public IDs were fully populated, and delivery-outbox RLS is enabled.

### Items still requiring operator action before taking payments

- [ ] Run the source collectors in shadow mode for seven consecutive days and pass the poll-completion, rolling-sweep, reconciliation, checksum, and p95 latency thresholds.
- [ ] Obtain human legal approval for the deployed Terms, Privacy, OGL attribution, digital-content wording, and B2B checkout evidence version.
- [ ] Exercise Checkout, Portal, duplicate/reordered webhooks, cancellation, and refund lifecycle in Stripe test mode against staging.
- [ ] Confirm Redis-backed rate limiting, Resend delivery, alert routing, and independent kill switches in the release environment.
- [ ] Complete the private compliance pilot and grounded-narrative gates before enabling paid Radar one account at a time.

## 0. Paid Radar Release Gate

### Required Before Paid Activation

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
- [x] Removed paid-listing and Full Dataset checkout endpoints return `410 Gone` before any Stripe call.
- [x] Frontend dependency audit is clean.

## 1. Secrets

Create production secrets in the Vercel project secret store and approved connected-service stores. Required backend values:

```json
{
  "database_url": "postgresql://...",
  "api_master_key": "cm_...",
  "stripe_secret_key": "sk_live_...",
  "stripe_webhook_secret": "whsec_...",
  "stripe_price_radar_regional": "price_...",
  "stripe_price_radar_national": "price_...",
  "stripe_price_intelligence_feed": "price_...",
  "b2b_terms_version": "approved-version-id",
  "b2b_terms_sha256": "lowercase-sha256-of-approved-terms",
  "b2b_evidence_hash_key": "dedicated-random-secret",
  "digital_content_terms_version": "approved-version-id",
  "digital_content_terms_sha256": "lowercase-sha256-of-approved-terms",
  "resend_api_key": "re_...",
  "caregist_to_support_token": "...",
  "support_internal_token": "...",
  "hermes_internal_token": "...",
  "webhook_secret_key": "<32-byte AES-GCM key>",
  "redis_url": "rediss://..."
}
```

Archived legacy Price IDs may remain configured only for existing-subscription
replay and compatibility entitlements. They must not be reactivated, exposed as
saleable plans, or accepted by new checkout sessions.

Checklist:

- [ ] Confirm Vercel production and preview environments receive only their scoped secret references.
- [ ] Store a dedicated Vercel automation-bypass secret in GitHub as `VERCEL_AUTOMATION_BYPASS_SECRET`; do not disable preview protection for smoke tests.
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
- [ ] A seven-day Neon restore window is verified before migrations.

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
- [ ] Treat both already-applied `034` files as reserved history; never rename them and require every future migration number to be unique.
- [ ] `STAGING_DATABASE_URL` and `PROD_DATABASE_URL` are both set and point to different databases.
- [ ] Confirm migrations through `044_b2b_contract_acceptance.sql` are recorded in `schema_migrations`.
- [ ] Confirm `api_keys.key_hash` is `NOT NULL`.
- [ ] Confirm `api_keys.key` is `NULL` for all rows.
- [ ] Confirm no production migration is run before a backup snapshot exists.

Example verification:

```sql
SELECT filename FROM schema_migrations ORDER BY filename DESC LIMIT 5;
SELECT COUNT(*) FROM api_keys WHERE key_hash IS NULL OR key IS NOT NULL;
```

## 4. Backups And Restore

- [ ] Upgrade the Neon plan if required and verify a seven-day restore window.
- [ ] Create a timestamped Neon recovery branch/restore point before every production migration.
- [ ] Restore to a temporary isolated Neon branch and run schema and row-count invariants.
- [ ] Record restore duration, achieved RPO, RTO and approver evidence.
- [ ] Delete the temporary branch only after drill approval.
- [ ] Schedule the drill monthly.

Acceptance criteria: RPO remains within configured Neon history, restore completes in under 30 minutes and all invariants/smoke tests pass.

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
- [ ] Checkout returns the governed unavailable response while any legal/privacy/VAT gate is red.
- [ ] After every gate is evidenced in staging, a browser session plus the exact approved terms version and business-authority confirmation creates one Stripe Checkout Session.
- [ ] Stripe dashboard test event reaches `/api/v1/billing/webhook`.
- [ ] Radar checkout rejects every legacy tier, extra-seat request, and self-service Feed/Enterprise request without creating a Stripe object.
- [ ] After controlled staging activation, only Radar Regional and Radar National create Checkout Sessions and their fixed seat limits match the approved catalogue.
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

Only after the individual lead and export gates are approved and deliberately enabled, run their delivery smoke with an operational inbox:

```bash
CAREGIST_APP_URL=https://www.caregist.co.uk \
CAREGIST_REQUIRE_DATABASE=1 \
CAREGIST_LEAD_EMAIL=ops@example.com \
python3 tools/verify-deploy.py
```

The scheduled workflow `.github/workflows/production-smoke.yml` runs the public smoke hourly and on pushes to `main`.

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
- [ ] Confirm signup and login; confirm every gated checkout, claim, lead, and export capability either follows its approved path or fails closed.
- [ ] Review audit logs for unexpected admin or master-key use.

## 10. Remaining Evidence Work

The code includes downgrade re-tiering, master-key rotation controls, real-Postgres CI replay, retention tooling, trusted-proxy handling, and forward-only recovery documentation. The remaining work is operational evidence: run those controls in staging, retain their outputs, and keep every dependent capability disabled until its evidence is approved.

## Rollback

If the application deploy fails before migrations:

```bash
git revert HEAD
git push origin main
```

If migrations were applied, preserve schema compatibility and use a forward-fix migration for isolated defects. Use Neon PITR only for destructive or irrecoverable database changes, then rerun complete smoke and reconciliation checks before sending traffic.

## Support References

- Production status: `PRODUCTION_READY.md`
- Historical audit: `PRODUCTION_AUDIT.md`
- Public smoke script: `tools/verify-deploy.py`
- Production smoke workflow: `.github/workflows/production-smoke.yml`
