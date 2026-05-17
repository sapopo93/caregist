# Caregist Ship Runbook — Weekend 16–17 May 2026

> **Single source of truth for the full ship.** All 20 draft PRs are pre-staged.
> Payment-gated items (AWS/Bedrock, ICO fee, Stripe tier upgrades) are deferred to **1 June 2026**.
> This document is navigation + consolidated owner script — individual PR descriptions contain
> implementation detail. Cross-reference them as needed.

---

## 1. Pre-flight (before any merges)

Run locally, not on the server.

```bash
# Generate all rotating secrets (output goes to password manager — NOT committed)
bash scripts/generate-all-keys.sh > /tmp/caregist-secrets.env
cat /tmp/caregist-secrets.env   # review, store in 1Password/Bitwarden, then shred
shred -u /tmp/caregist-secrets.env
```

Access checks — confirm all before touching any PR:

- [ ] SSH into prod EC2 as `ubuntu` + confirm `sudo systemctl status caregist-api` responds
- [ ] Neon dashboard: confirm superuser / owner role on the production database
- [ ] Stripe dashboard: confirm owner-level access (can rotate keys + view all webhooks)
- [ ] Resend dashboard: confirm sender domain `caregist.co.uk` is verified
- [ ] Sentry dashboard: confirm project `caregist` is reachable and you can create releases

Env var staging — before Wave 2, open production `.env` on EC2 and add the block:

```
WEBHOOK_SECRET_KEY=<value from generate-all-keys.sh>
SESSION_TTL_SECONDS=2592000
```

Do not restart the API yet — the vars are pre-staged so Wave 2 merges can read them.

---

## 2. Wave 1 — No-dependency merges (merge first, any order)

These PRs are safe to land in any sequence. Merge, then run a quick `git pull && systemctl restart caregist-api` after each batch (or batch all Wave 1 merges then restart once).

| # | Name | PR | Notes |
|---|------|----|-------|
| 1 | Cog | #1 | Stripe rotation runbook — docs only, no restart needed |
| 2 | Cinder | #2 | Drops Redis dependency; if `REDIS_URL` is still set it is now ignored |
| 3 | Mortise | #4 | Adds `.gitignore` + secret-scanner CI; no runtime effect |
| 4 | Pulse | #11 | Adds health dependency checks to `/api/v1/health/readiness` |
| 5 | Pence | #12 | Stripe price audit script — docs/tools only |
| 6 | Mortar | #14 | Adds downgrade SQL for every migration (no forward schema change) |
| 7 | Rivet | #15 | Webhook signature tests — CI only |
| 8 | Compass | #17 | Claim-verification logic hardening |
| 9 | Beacon | #18 | Adds systemd timer units. **After merge**: `sudo cp systemd/*.timer /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now caregist-*.timer` |
| 10 | Quire | #19 | Full README rewrite + runbooks directory. Also runs: `git rm render.yaml` on the branch before merge (PR notes include this step). |

Post-Wave-1 restart:

```bash
ssh ubuntu@<EC2_IP>
cd /home/caregist/CareGist
git pull origin main
sudo systemctl restart caregist-api
curl -s http://localhost:8000/api/v1/health/readiness | python3 -m json.tool
```

---

## 3. Wave 2 — Encryption + auth surface (merge after Wave 1)

**Order within Wave 2 is strict.** Run pre-merge checks (`bash scripts/pre-merge-checks.sh`) before each step.

### 3a. Forge — PR #5 (WEBHOOK_SECRET_KEY + migration 030)

```bash
# 1. Confirm WEBHOOK_SECRET_KEY is set in prod .env (done in pre-flight)
# 2. Count-check
psql $DATABASE_URL -c "SELECT count(*) FROM webhook_subscriptions;"
# If count > 0, the migration will HMAC-encrypt existing rows. Safe to run regardless.
# 3. SSH to EC2 and run migration
source .venv/bin/activate
python3 db/apply_migrations.py   # applies 030_webhook_secret_hmac.sql
# 4. Merge PR #5 on GitHub
# 5. Pull + restart
git pull origin main && sudo systemctl restart caregist-api
```

### 3b. Spool — PR #9 (session table + migration 031)

```bash
# 1. Run migration — this creates user_sessions table
psql $DATABASE_URL -c "SELECT count(*) FROM user_sessions;" 2>&1 || echo "table does not exist yet — OK"
python3 db/apply_migrations.py   # applies 031_session_table.sql
# 2. Merge PR #9
# 3. Pull + restart
git pull origin main && sudo systemctl restart caregist-api
# NOTE: existing users will be force-logged out. This is expected and documented in PR #9.
```

### 3c. Cinch — PR #13 (bcrypt API keys + migration 032)

```bash
# 1. Count plaintext keys
psql $DATABASE_URL -c "SELECT count(*) FILTER (WHERE key_format='plaintext') FROM api_keys;"
# If > 0, migration will bcrypt them. Run regardless.
python3 db/apply_migrations.py   # applies 032_bcrypt_api_keys.sql
# 2. Merge PR #13
git pull origin main && sudo systemctl restart caregist-api
```

### 3d. Trill — PR #16 (marketing consent + migration 033)

```bash
python3 db/apply_migrations.py   # applies 033_marketing_consent.sql
# Merge PR #16
git pull origin main && sudo systemctl restart caregist-api
```

### 3e. Quill — PR #20 (DSAR + migration 034)

> **Migration number conflict:** PR #20 was drafted with migration number 030, which collides
> with Forge's 030. **Before merging Quill**, rename the file on the branch:
>
> ```bash
> git checkout quill/<branch-name>
> git mv db/migrations/030_dsar.sql db/migrations/034_dsar.sql
> # Update any internal reference to "030" in the file header comment if present
> git commit -m "fix: rename migration 030 -> 034 to avoid Forge collision"
> git push
> ```
>
> Then merge PR #20 and apply:

```bash
python3 db/apply_migrations.py   # applies 034_dsar.sql
git pull origin main && sudo systemctl restart caregist-api
```

---

## 4. Wave 3 — Frontend + auth (merge after Wave 2)

### 4a. Spindle — PR #6 (kill NEXT_PUBLIC_API_KEY)

```bash
# Merge PR #6
git pull origin main

# IMMEDIATELY POST-MERGE — rotate API_KEY:
# Follow the Stripe rotation runbook pattern (PR #1 / Cog):
#   1. Generate new key in Stripe dashboard
#   2. Update API_KEY in prod .env
#   3. sudo systemctl restart caregist-api
#   4. Rebuild + redeploy frontend (npm run build && pm2 restart caregist-frontend)
#   5. Verify no stale bundle: curl -s https://caregist.vercel.app/ | grep -v 'NEXT_PUBLIC_API_KEY'
```

### 4b. Latch — PR #7 (HttpOnly cookies)

Depends on Spool (031) having been applied. Merge after 3b confirmed healthy.

```bash
# Merge PR #7
git pull origin main && sudo systemctl restart caregist-api
```

### 4c. Lattice — PR #8 (cookie banner + CSP)

> **Merge conflict note:** `scripts/_secret-scan-workflow.yml` has a pre-resolved conflict
> on Lattice's branch (Mason accepted Lattice's version). When merging, take Lattice's file.

```bash
# Merge PR #8
git pull origin main
cd frontend && npm run build && cd ..
sudo systemctl restart caregist-frontend   # or pm2 restart caregist-frontend
```

---

## 5. Wave 4 — Deferred to 1 June 2026 (payment required)

Do not merge or apply these until payment actions are complete.

| Deferral | Blocker | Action on 1 June |
|----------|---------|------------------|
| PR #3 Bedrock | AWS account + Terraform state bootstrapped | `terraform apply` from `infra/` directory; follow PR #3 notes |
| PR #10 Vellum | ICO registration fee (£40) + ICO reg number | Fill `ICO_REG_NUMBER` in privacy page + `.env`; merge PR #10 |
| Cleanup migration (webhook_subscriptions backfill) | 7-day soak after PR #5 live in prod | Drop plaintext backup column once HMAC re-encryption confirmed healthy |
| Blue-green deploy | Terraform (Bedrock) applied | Switch load-balancer target group after Bedrock PR live |

See [Section 10](#10-june-1-follow-up-procedure) for detailed steps.

---

## 6. Per-merge env var checklist

| Env var | Source PR | How to generate | Example value |
|---------|-----------|-----------------|---------------|
| `WEBHOOK_SECRET_KEY` | #5 Forge | `openssl rand -base64 32` | `abc123...=` (32-byte base64) |
| `SESSION_TTL_SECONDS` | #9 Spool | No generation needed — hardcoded default | `2592000` (30 days) |
| `STRIPE_SECRET_KEY` | #1 Cog / #6 Spindle | Stripe dashboard → API keys → Create restricted key | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | #1 Cog | Stripe dashboard → Webhooks → signing secret | `whsec_...` |
| `DATABASE_URL` | existing | Neon dashboard → Connection string | `postgresql://...` |
| `RESEND_API_KEY` | existing | Resend dashboard → API keys | `re_...` |
| `SENTRY_DSN` | existing | Sentry project settings | `https://...@sentry.io/...` |
| `NEXT_PUBLIC_SENTRY_DSN` | existing | Same project, separate env | `https://...@sentry.io/...` |
| `API_KEY` | #6 Spindle | Rotate post-merge via Stripe rotation runbook pattern | internal opaque key |
| `ICO_REG_NUMBER` | #10 Vellum (JUNE 1) | ICO self-registration portal after £40 fee | `ZA123456` |

**REDIS_URL**: Cinder (PR #2) removes the Redis dependency. Leave `REDIS_URL` unset or blank after Wave 1.

---

## 7. Per-merge migration checklist

All migrations apply via `python3 db/apply_migrations.py` on EC2 (venv activated). Run in strict number order.

| Order | File | PR | Pre-merge check |
|-------|------|----|-----------------|
| 1 | `030_webhook_secret_hmac.sql` | #5 Forge | `SELECT count(*) FROM webhook_subscriptions;` |
| 2 | `031_session_table.sql` | #9 Spool | Table must not exist yet |
| 3 | `032_bcrypt_api_keys.sql` | #13 Cinch | `SELECT count(*) FILTER (WHERE key_format='plaintext') FROM api_keys;` |
| 4 | `033_marketing_consent.sql` | #16 Trill | No pre-check needed (additive column) |
| 5 | `034_dsar.sql` | #20 Quill | **Rename from 030 to 034 on branch before merge** |

Full run command on EC2:

```bash
ssh ubuntu@<EC2_IP>
cd /home/caregist/CareGist
source .venv/bin/activate
python3 db/apply_migrations.py
python3 -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(os.environ['DATABASE_URL'])
    rows = await conn.fetch('SELECT filename FROM schema_migrations ORDER BY applied_at DESC LIMIT 5')
    for r in rows: print(r['filename'])
    await conn.close()
asyncio.run(check())
"
```

---

## 8. Post-deploy smoke tests

Run after all Wave 3 merges and restarts are complete:

```bash
bash scripts/post-deploy-smoke.sh https://caregist.co.uk
```

Additionally run the existing internal smoke test:

```bash
python3 tools/smoke_new_registration_pipeline.py \
  --base-url https://caregist.co.uk \
  --api-key "$API_KEY" \
  --internal-token "$SUPPORT_INTERNAL_TOKEN"
```

Check Sentry for new errors (filter last 30 minutes).

---

## 9. Merge conflict resolution guide

| File | Conflict source | Resolution |
|------|-----------------|------------|
| `scripts/_secret-scan-workflow.yml` | Mortise (#4) vs Lattice (#8) | Take **Lattice's** version — pre-resolved by Mason on Lattice's branch |
| `README.md` | Mortise stub + Vellum H-Kay section vs Quire full rewrite | Take **Quire's** version — it is a superset (incorporates Mortise stub and Vellum H-Kay section) |
| `frontend/app/layout.tsx` | Latch (#7) vs Lattice (#8) | Both additive (Latch adds cookie jar, Lattice adds banner component) — **auto-merge** |
| `api/main.py` | Multiple PRs add startup health-check assertions | All additive — **auto-merge**; run `pytest` after to confirm no duplicate blocks |
| `.env.example` | Many PRs add new vars | All additive — **auto-merge**; verify final file against Section 6 table above |
| `db/migrations/030_*.sql` | Forge (#5) vs Quill (#20) | **Rename Quill's file to 034** before merge (see Wave 2, step 3e) |

---

## 10. June 1 follow-up procedure

Prerequisites before starting:
- [ ] AWS account created and billing set up
- [ ] ICO registration fee (£40) paid and registration number received
- [ ] Terraform installed locally (`>= 1.7`)

### 10a. Bedrock — PR #3 (Terraform)

```bash
cd infra/
terraform init
terraform plan -out=tfplan
# Review plan carefully — creates VPC, EC2 target group, ALB, etc.
terraform apply tfplan
```

After `terraform apply` succeeds:
1. Update DNS to point `caregist.co.uk` at the ALB endpoint (not the bare EC2 IP)
2. Merge PR #3 to main
3. Update `APP_URL` and `CORS_ORIGINS` in production `.env` if the domain changes

### 10b. Vellum — PR #10 (Privacy + DPIA + ICO reg number)

```bash
# 1. Log in to ICO self-registration portal with your reg number
# 2. Fill ICO_REG_NUMBER in prod .env:
echo "ICO_REG_NUMBER=ZA######" >> /home/caregist/CareGist/.env
# 3. Merge PR #10 on GitHub
git pull origin main
sudo systemctl restart caregist-api
# 4. Verify privacy page
curl -s https://caregist.co.uk/privacy | grep 'H-Kay Limited'
```

### 10c. Cleanup migration — webhook_subscriptions backfill column drop

After 7-day soak with PR #5 (Forge) in prod and no errors:

```bash
# Confirm all rows migrated
psql $DATABASE_URL -c "SELECT count(*) FILTER (WHERE hmac_hash IS NULL) FROM webhook_subscriptions;"
# If 0, safe to drop plaintext backup column
psql $DATABASE_URL -c "ALTER TABLE webhook_subscriptions DROP COLUMN IF EXISTS secret_plaintext_backup;"
```

### 10d. Blue-green deploy switch (after Bedrock live)

Once ALB and target groups are created by Terraform:
1. Register current EC2 instance as blue target
2. Launch new EC2 from AMI snapshot as green target
3. Deploy latest main to green target
4. Run smoke tests against green target
5. Shift ALB listener weights 10% → 50% → 100% over 15 minutes
6. Confirm Sentry shows no new errors on green
7. Deregister blue target

---

## Quick-reference: PR → file change surface

| PR | Key files changed | Migration |
|----|-------------------|-----------|
| #1 Cog | `workflows/stripe-rotation.md` | none |
| #2 Cinder | `api/rate_limit.py`, `requirements.txt` | none |
| #3 Bedrock | `infra/*.tf` | none (JUNE 1) |
| #4 Mortise | `.gitignore`, `scripts/_secret-scan-workflow.yml` | none |
| #5 Forge | `api/webhooks.py`, `.env.example` | **030** |
| #6 Spindle | `frontend/`, `api/auth.py` | none |
| #7 Latch | `api/session.py`, `frontend/app/layout.tsx` | none |
| #8 Lattice | `frontend/app/layout.tsx`, `api/csp.py` | none |
| #9 Spool | `api/session_store.py` | **031** |
| #10 Vellum | `frontend/app/privacy/`, `docs/dpia.md` | none (JUNE 1) |
| #11 Pulse | `api/health.py` | none |
| #12 Pence | `tools/stripe_price_audit.py` | none |
| #13 Cinch | `api/api_keys.py` | **032** |
| #14 Mortar | `db/migrations/*_down.sql` | none |
| #15 Rivet | `tests/test_webhooks.py` | none |
| #16 Trill | `api/consent.py`, `frontend/signup` | **033** |
| #17 Compass | `api/claims.py` | none |
| #18 Beacon | `systemd/*.timer`, `systemd/*.service` | none |
| #19 Quire | `README.md`, `workflows/` | none |
| #20 Quill | `api/dsar.py` | **034** (rename from 030) |

---

*Generated by Plinth on 2026-05-17. Do not edit this file directly — open a PR against `prod-ready/ship-runbook`.*
