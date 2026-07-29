# CareGist Production Readiness Status

**Date:** 2026-06-29  
**Code status:** READY for staging and controlled production deploy after CI passes  
**Deployment status:** NO-GO until the external infrastructure gates below are complete  
**Current score:** 95/100 for the codebase, not yet scored for live infrastructure

## Executive Summary

CareGist's main code-level production blockers have been addressed. The backend now enforces hashed-only API keys, stores session tokens as database hashes, requires production webhook encryption and Redis secrets, verifies approved provider claims before profile checkout, and gates Stripe webhook side effects behind transactional event deduplication. The frontend removes the unsafe `NEXT_PUBLIC_API_KEY` fallback and protects authenticated routes with middleware that fails closed when session validation cannot complete.

This is ready to deploy to staging. It is not a public production go until secrets, Redis, database backups, migrations, monitoring, and live smoke tests are completed by the deployment owner.

## Go / No-Go

**GO for staging deployment**

- Local backend and frontend gates pass.
- Required production-secret checks are in code.
- Current docs identify the remaining live-environment work.

**NO-GO for public production until these are complete**

- AWS Secrets Manager or hosting secrets contain every required production value.
- Redis is provisioned and reachable from the backend.
- Database migrations through `031_enforce_hashed_api_keys.sql` have been applied in staging and production.
- Automated backups/PITR are enabled and a restore drill has passed.
- Staging smoke tests pass with `CAREGIST_REQUIRE_DATABASE=1`.
- Stripe webhook, Resend email, Redis rate-limit, and billing checkout flows are verified against staging/live services.
- Sentry/logging/alerts are configured before traffic is sent.

## Resolved Code-Level Blockers

- **Session security:** `user_sessions` stores `token_hash`; the cookie carries an opaque `cs_...` session token and is `HttpOnly`, `Secure` in production, and `SameSite=strict`.
- **Frontend route protection:** `frontend/middleware.ts` protects `/dashboard`, `/provider-dashboard`, and `/admin`; it redirects to `/login` when the session is missing, invalid, or cannot be validated.
- **Secret enforcement:** `WEBHOOK_SECRET_KEY` and `REDIS_URL` are required for non-local production database deployments.
- **API keys:** `api/middleware/auth.py` validates only `key_hash`; `db/migrations/031_enforce_hashed_api_keys.sql` makes that invariant permanent.
- **Frontend credential exposure:** `frontend/lib/server-api-config.ts` no longer reads `NEXT_PUBLIC_API_KEY`.
- **Stripe webhooks:** duplicate Stripe events are gated by `INSERT ... ON CONFLICT DO NOTHING RETURNING` inside the subscription-mutating transaction.
- **Profile checkout ownership:** profile upgrades require an approved `provider_claims` row for the authenticated user's email and provider.
- **Sales-claim alignment:** free and Alerts Pro exports are disabled in entitlement config and docs/copy no longer promise unavailable self-serve features.
- **Dependency security:** frontend dependency audit is clean after the Sentry upgrade and scoped PostCSS override.

## Remaining Work

### Pre-Launch External Gates

- Provision Redis with TLS/AUTH where supported and set `REDIS_URL`.
- Store all backend secrets in AWS Secrets Manager or the selected host's secret manager.
- Apply migrations in staging, then production, using `python3 db/apply_migrations.py --database-url "$DATABASE_URL"`.
- Enable database PITR/snapshots and complete one restore into staging.
- Run staging smoke tests with database mode required.
- Send Stripe dashboard test events to the deployed webhook endpoint.
- Confirm Resend domain, SPF/DKIM, and live email delivery.
- Configure Sentry and operational alerts.

### Accepted Post-Launch Follow-Ups

These should be scheduled before broad GA, but they do not block a controlled launch if the external gates above pass:

- Re-tier or revoke existing API keys on subscription downgrade.
- Add master API-key rotation and audit alerts.
- Add a constant-time floor for forgot-password email enumeration resistance.
- Add CI integration tests that replay migrations against a real Postgres service.
- Add retention jobs for analytics/audit/email tables.
- Validate `X-Forwarded-For` only from trusted proxies.
- Document rollback strategy for forward-only migrations.

## Validation Record

Latest local gates run on 2026-06-29:

- `pytest` -> 266 passed
- `npm test` -> 35 passed
- `npm run build` -> passed
- `npm audit` -> 0 vulnerabilities
- Python 3.12 clean-room `pip check` -> no broken requirements
- Python syntax checks for changed auth/config modules -> passed

## Release Decision

The codebase is production-ready from a local correctness/security gate perspective. The live service is not production-ready until the infrastructure checklist in `DEPLOYMENT_CHECKLIST.md` is complete and evidenced.
