# CareGist Production Deployment Checklist

**Last Updated:** 2026-06-29
**Status:** Code hardening complete; ready for infrastructure setup and deployment

---

## Pre-Deployment — Infrastructure Setup

### 1. AWS Secrets Manager
- [ ] Create a JSON secret in AWS Secrets Manager with all required values:
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
    "stripe_price_enterprise": "price_...",
    "stripe_price_profile_enhanced": "price_...",
    "stripe_price_profile_premium": "price_...",
    "stripe_price_profile_sponsored": "price_...",
    "resend_api_key": "re_...",
    "caregist_to_support_token": "...",
    "support_internal_token": "...",
    "hermes_internal_token": "...",
    "webhook_secret_key": "<32-byte AES-GCM key in hex>",
    "redis_url": "redis://..."
  }
  ```
- [ ] Note the secret ID (used in `AWS_SECRETS_MANAGER_SECRET_ID` env var)
- [ ] Test that the backend can read all values via AWS SDK

### 2. Redis
- [ ] Provision Redis (ElastiCache on AWS or Upstash for serverless):
  - Minimum: 256MB tier for dev/staging, 1GB+ for prod
  - Enable AUTH if available
  - Enable encryption in transit (TLS)
- [ ] Test connectivity from the app server
- [ ] Set connection timeout to 5s, retry backoff to 1s
- [ ] Populate `REDIS_URL` in AWS Secrets Manager

### 3. Database
- [ ] Verify PostgreSQL version 14+
- [ ] Enable PostGIS extension (used by provider queries)
- [ ] Configure automatic snapshots/PITR:
  - **If using Neon:** Enable point-in-time restore + branch snapshots
  - **If using RDS:** Configure 7-day retention + automated snapshots
  - **If self-hosted:** Set up pg_dump hourly cron or WAL archiving
- [ ] Test restore-into-staging procedure (see Restore Drill below)

### 4. Deployment Infrastructure
- [ ] Deploy via one of:
  - **Vercel (next.js frontend only):** Provision Vercel Postgres, set env vars
  - **AWS EC2 + RDS:** Terraform module for EC2, ALB, RDS, Secrets Manager, Security Groups
  - **Render/Railway:** Provision Postgres, Redis, set secrets
- [ ] Configure health check endpoint at `/api/v1/health`
- [ ] Set deployment to pull from `origin/main` branch

---

## Database Migration Replay — Staging First, Then Production

### Apply Migrations in Staging
1. [ ] Connect to staging database: `psql $STAGING_DATABASE_URL`
2. [ ] Apply all migrations in order (use `db/apply_migrations.sh` if it exists):
   ```bash
   psql $STAGING_DATABASE_URL -f db/init.sql
   psql $STAGING_DATABASE_URL -f db/migrations/001_*.sql
   ...
   psql $STAGING_DATABASE_URL -f db/migrations/031_enforce_hashed_api_keys.sql
   ```
3. [ ] Verify schema with: `psql $STAGING_DATABASE_URL -c "\dt"`
4. [ ] Run smoke tests against staging (see Smoke Tests below)

### Apply Migrations in Production
- [ ] Create a backup snapshot first
- [ ] Apply same migrations: `psql $PROD_DATABASE_URL -f db/migrations/031_enforce_hashed_api_keys.sql`
- [ ] Verify no errors; check row counts in critical tables

### Critical Migrations in This Release
- **026: hash_api_keys.sql** — Converts plaintext keys to SHA-256 hashes
- **027: user_sessions.sql** — Opaque session table (replaces plaintext tokens in cookies)
- **028: audit_log.sql** — Admin action audit trail
- **029: password_reset_token_entropy.sql** — Stronger reset token generation
- **031: enforce_hashed_api_keys.sql** — Makes hashing permanent (NOT NULL constraint)

---

## Smoke Tests — Staging & Production

### Before Deploying to Production
Run these against your staging environment to verify all integrations:

```bash
# 1. Database connectivity
python3 -c "import asyncpg; asyncpg.run(...)" # verify async DB works

# 2. Stripe integration
python3 tools/verify_stripe.py

# 3. Email service (Resend)
python3 tools/verify_email.py

# 4. Redis rate limiting
python3 tools/verify_redis.py

# 5. Full public smoke test
python3 tools/verify-deploy.py

# 6. Full lead/export smoke (sends real email)
CAREGIST_LEAD_EMAIL=ops@example.com python3 tools/verify-deploy.py
```

### Production Smoke Tests
After deploying to production:

```bash
# 1. Immediate post-deploy smoke (30 attempts, 20s delay between retries)
CAREGIST_APP_URL=https://www.caregist.co.uk python3 tools/verify-deploy.py

# 2. Confirm health endpoint
curl https://www.caregist.co.uk/api/v1/health

# 3. Test authentication flow
curl -X POST https://www.caregist.co.uk/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"..."}'

# 4. Test Stripe webhook delivery (send test event from Stripe dashboard)
curl https://www.caregist.co.uk/api/v1/webhooks/stripe \
  -H "X-Stripe-Signature: $(your_computed_signature)" \
  -d '{"type":"checkout.session.completed",...}'
```

### Automated Production Smoke Tests
The GitHub Actions workflow `.github/workflows/production-smoke.yml` runs:
- Every 30 minutes on the `main` branch
- On every push to `main`
- Full availability check + user flow validation

Check workflow runs at: `.github/workflows/production-smoke.yml`

---

## Backup & Restore Drill

### Configure Automated Backups

**Neon (recommended for ease):**
```bash
# Neon automatically snapshots; enable point-in-time restore in project settings
# Test restore: Create a branch from a snapshot and verify data integrity
```

**RDS:**
```bash
# AWS Console → RDS → Databases → Modify
# Enable "Backup retention period": 7 days (minimum for compliance)
# Enable "Copy automated snapshots to another region": Yes (for DR)
# Enable "Enhanced monitoring": Yes
```

**Self-hosted PostgreSQL:**
```bash
# Add to crontab (daily 2 AM backup):
0 2 * * * /usr/local/bin/backup-caregist.sh

# backup-caregist.sh:
#!/bin/bash
pg_dump $DATABASE_URL | gzip > /backups/caregist_$(date +%Y%m%d_%H%M%S).sql.gz
# Rotate old backups; ship to S3
```

### Restore Drill (Run Monthly)

1. [ ] Create a new staging database or restore to a point-in-time clone
2. [ ] Replay all migrations: `psql $RESTORE_DB -f db/init.sql && ...`
3. [ ] Run smoke tests against the restore
4. [ ] Verify 3-5 critical tables have expected row counts:
   ```bash
   psql $RESTORE_DB -c "SELECT COUNT(*) FROM care_providers;"
   psql $RESTORE_DB -c "SELECT COUNT(*) FROM subscriptions WHERE status='active';"
   ```
5. [ ] Document restore time (RPO/RTO)
6. [ ] Schedule next drill

**Acceptance criteria:** Restore completes in < 30 min; all smoke tests pass.

---

## Post-Deployment Verification

### Day 1 (Launch Day)
- [ ] Monitor error rate in Sentry (should be < 1% error rate on all endpoints)
- [ ] Check database connection pool usage (target: < 80% of max)
- [ ] Verify Redis cache hit rate (target: > 80% on rate limit lookups)
- [ ] Manually test user signup → email verify → login flow
- [ ] Manually test B2B checkout flow (Starter plan)
- [ ] Confirm provider listing claim flow works end-to-end
- [ ] Review audit logs for any suspicious activity

### Week 1
- [ ] Monitor 99th-percentile latency (target: < 1s on most endpoints)
- [ ] Review Sentry for new error patterns
- [ ] Verify cron jobs are running (new-registration feed, weekly digest, etc.)
- [ ] Check webhook delivery success rate (target: > 99%)
- [ ] Verify email delivery (check with sample lead submission)

### Month 1
- [ ] Review analytics for sign-up funnel conversion rates
- [ ] Verify payment success rate (target: > 95%)
- [ ] Run full restore drill from production backup
- [ ] Review and rotate API_MASTER_KEY if exposed anywhere
- [ ] Plan capacity for next 6 months based on growth

---

## Go/No-Go Checklist

### Code Readiness ✅
- [x] All blocker findings fixed (F-1 through F-11)
- [x] Auth perimeter hardened (sessions, API keys, CSRF)
- [x] Secret management enforced (WEBHOOK_SECRET_KEY, REDIS_URL required)
- [x] Frontend middleware added for protected routes
- [x] Stripe webhook dedup race fixed
- [x] Tests passing (test suite should run in CI)
- [x] README + deployment guide complete

### Infrastructure Readiness (TODO: Owner)
- [ ] AWS Secrets Manager secret created with all required values
- [ ] Redis provisioned and tested
- [ ] Database backups configured with 7-day retention
- [ ] Restore drill executed and documented
- [ ] Deployment infrastructure ready (Vercel project, EC2, RDS, etc.)
- [ ] SSL certificate valid and auto-renewing
- [ ] CDN/CloudFront configured if using (cache headers set correctly)

### Testing Readiness (TODO: Owner)
- [ ] Smoke tests pass on staging infrastructure
- [ ] Stripe webhook tests pass (send test events)
- [ ] Email delivery confirmed (Resend working)
- [ ] Rate limits verified (Redis working correctly)
- [ ] Load test completed (1000 req/s without dropping)

### Monitoring Readiness (TODO: Owner)
- [ ] Sentry project created and wired
- [ ] CloudWatch/monitoring dashboards created
- [ ] Alerts configured for:
  - Error rate > 5%
  - P99 latency > 2s
  - Database CPU > 80%
  - Disk usage > 80%
  - Webhook delivery failure > 1%
- [ ] On-call runbook updated
- [ ] Escalation policy defined

### Legal/Compliance Readiness (TODO: Owner)
- [ ] Privacy policy review complete (covers data use, retention, etc.)
- [ ] Terms of service review complete
- [ ] Cookie consent flow tested (blocks non-essential cookies pre-consent)
- [ ] Right to erasure tested (DELETE /account works end-to-end)
- [ ] DPA in place with AWS, Stripe, Resend, Sentry

---

## Known Limitations & Future Work

### High Priority (2-3 weeks post-launch)
- **F-17:** Subscription downgrade should revoke/re-tier API keys
- **F-18:** Master API key rotation + audit logging
- **F-24:** Email enumeration timing attack (add constant-time floor)
- **F-27:** CI integration tests (Postgres service, replay migrations)
- **F-28:** Analytics table retention (90d events, 2y audit logs)

### Medium Priority (Month 2)
- **F-19:** X-Forwarded-For proxy trust list validation
- **F-29:** Cron monitoring via systemd timers or ECS scheduled tasks
- **F-30:** Rollback migration strategy
- High-order Stripe seat/tier logic (nested subscription items)

### Low Priority (Post-GA)
- [ ] HA setup (multi-AZ, blue/green deployments)
- [ ] Full test coverage on invoice/credit logic
- [ ] Webhook customer round-trip signature verification test
- [ ] CSP nonce-based injection (next/image migration)
- [ ] Accessibility audit (alt text, ARIA labels)

---

## Deployment Commands (Example — Adjust Per Your Infrastructure)

### Vercel (Next.js Frontend Only)
```bash
# 1. Link project
vercel link --project caregist

# 2. Set environment secrets
vercel env add POSTGRES_URL
vercel env add STRIPE_PAYMENT_LINK_URL
vercel env add NEXT_PUBLIC_API_URL

# 3. Deploy
vercel deploy --prod

# 4. Run smoke test
python3 tools/verify-deploy.py
```

### AWS EC2 + RDS
```bash
# 1. SSH into server
ssh -i ~/.ssh/key.pem ec2-user@your-instance

# 2. Pull latest code
cd /var/www/caregist && git pull origin main

# 3. Apply migrations
DATABASE_URL=$PROD_DB psql -f db/migrations/031_enforce_hashed_api_keys.sql

# 4. Restart services
sudo systemctl restart caregist-api
sudo systemctl restart caregist-frontend

# 5. Verify health
curl http://localhost:8000/api/v1/health
```

---

## Rollback Plan

If critical issues emerge post-deployment:

1. **Immediate (< 5 min):** Revert to previous commit and redeploy
   ```bash
   git revert HEAD
   git push origin main
   # Re-deploy via your CD pipeline
   ```

2. **If database migrations failed:** Restore from backup
   ```bash
   # Restore latest backup
   psql $NEW_DB < caregist_backup_latest.sql.gz
   # Re-apply migrations if partial
   psql $NEW_DB -f db/migrations/031_enforce_hashed_api_keys.sql
   ```

3. **If secrets misconfigured:** Update AWS Secrets Manager, restart API
   ```bash
   # Fix value in AWS Secrets Manager console
   # Restart processes to pick up new secrets
   ```

---

## Support & Escalation

- **Backend issues:** Check Sentry dashboard, logs in CloudWatch
- **Database issues:** Connect to RDS/Neon, run diagnostic queries
- **Stripe failures:** Check Stripe dashboard for webhook errors, retry events
- **Email delivery:** Check Resend logs for bounces, verify domain SPF/DKIM
- **Rate limit issues:** Verify Redis is running, check connection pool

---

**Questions?** Reference the main README.md and individual service documentation.
