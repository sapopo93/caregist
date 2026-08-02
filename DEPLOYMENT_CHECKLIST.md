# CareGist Production Deployment Checklist

**Last updated:** 2026-08-02
**Purpose:** Deployment-owner checklist for taking the hardened codebase from staging to production.
**Rule:** Do not send public production traffic until every required item is complete and evidenced.

## Current Release-State Snapshot (2026-08-02)

Verified against the live site and this repo's git history. Supersedes stale TODOs below where they conflict.

- **Release integration**: `codex/caregist-production-remediation-20260802` preserves the hardening history and merges current `origin/main`. Production remains NO-GO until this branch passes PR review, exact-SHA CI/staging evidence and is merged to protected `main`.
- **`.github/workflows/ci.yml`** (lint, migration governance, pytest, pip-audit, real-Postgres migration replay, frontend build/test/audit) only triggers on push to `main` or PRs — it has never run against this remediation work because it lives on unmerged side branches.
- **Readiness vs. freshness are intentionally separate signals**: `readiness_ok` (traffic-serving gate) checks that `pipeline_runs`/`trusted_event_ledger` tables are reachable; it must NOT depend on feed freshness, or an upstream CQC publishing lag would take fully-working routes (search, groups, pricing) offline along with the stale feed. `freshness_ok` and the dedicated `/api/v1/health/freshness` endpoint already exist for that signal and are what monitoring/alerting should watch. Production currently shows `readiness_ok: true, feed_fresh: false` (latest event 2026-06-01, outside the 168h SLA) — that combination is correct behavior, not a bug. The real gap here is **observability**: nothing currently pages on-call when `/freshness` goes stale (see "Monitoring And Alerts" below) — wire an alert on that endpoint rather than coupling it into readiness.
- **`/data-status` 404**: the page (`frontend/app/data-status/page.tsx`) genuinely does not exist at deployed commit `91601e1` — pure deploy drift, resolves on shipping current HEAD.
- **`/provider-sitemap-index.xml` 503**: NOT a backend/data problem — `GET /api/v1/sitemaps/providers/count` returns a healthy `{"total":56742}` when hit directly. The frontend route's own `getServerApiBase()` call is failing before it reaches that healthy backend. The deployment does build with the multi-service architecture (`services/backend/fastapi` + `services/frontend/*` lambdas present per `vercel inspect`), so the `CAREGIST_BACKEND_URL` service binding *should* be auto-injected — but something in that resolution path is not working at runtime. Needs a Vercel function-log capture during a live request (session log-tailing didn't catch it in the available window) or a temporary debug log statement on a preview deploy to pin down exactly where the fetch fails.
- **Backups/PITR**: Neon-native branch restore is the sole recovery model. The inspected production and staging Neon resources are both on the Free plan; a verified seven-day restore window and a successful isolated restore drill are therefore unresolved release prerequisites. AWS backup branches remain outside this release.
- **Migration numbering "collision"**: the duplicate `034_*.sql` pair is intentionally allowlisted in `tools/check_migration_governance.py` (`LEGACY_DUPLICATE_MIGRATIONS`) — checker passes clean. Not a real gap.
- **Governance flags**: checkout, monitoring activation, exports, leads, claims, reviews, enquiries, outbound delivery/communications and remote media all fail closed. Each capability requires its own SOP, approver, denial-path test, monitoring and rollback evidence before activation.

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

Create production secrets in the Vercel project secret store and approved connected-service stores. Required backend values:

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
  "b2b_terms_version": "approved-version-id",
  "b2b_terms_sha256": "lowercase-sha256-of-approved-terms",
  "b2b_evidence_hash_key": "dedicated-random-secret",
  "resend_api_key": "re_...",
  "caregist_to_support_token": "...",
  "support_internal_token": "...",
  "hermes_internal_token": "...",
  "webhook_secret_key": "<32-byte AES-GCM key>",
  "redis_url": "rediss://..."
}
```

Checklist:

- [ ] Confirm Vercel production and preview environments receive only their scoped secret references.
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
- [ ] Profile checkout fails without an approved claim.
- [ ] Profile checkout remains unavailable until the same commercial gates pass; after controlled staging activation it succeeds only for an approved claim and rejects duplicate subscriptions.
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
