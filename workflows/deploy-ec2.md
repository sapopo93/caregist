# Workflow: Deploy to EC2

## Overview
Standard deployment sequence for CareGist on AWS EC2. Covers the API (uvicorn), frontend (Next.js), migration application, and post-deploy verification.

## Prerequisites
- SSH access to the EC2 instance
- Code pushed to `main` branch on GitHub
- `.env` populated with production credentials on the server (never committed to git)
- venv set up at `/home/caregist/CareGist/.venv`

---

## Step 1 — Pull Latest Code

```bash
ssh ubuntu@<EC2_IP>
cd /home/caregist/CareGist
git pull origin main
```

Verify the pull:
```bash
git log --oneline -5
```

---

## Step 2 — Apply Database Migrations

Always run migrations before restarting services so the new code boots against the updated schema.

```bash
source .venv/bin/activate
python3 db/apply_migrations.py
```

Expected output: list of migrations applied (or "No pending migrations" if already up to date).

Verify:
```bash
python3 -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(os.environ['DATABASE_URL'])
    rows = await conn.fetch('SELECT filename FROM schema_migrations ORDER BY applied_at DESC LIMIT 3')
    for r in rows: print(r['filename'])
    await conn.close()
asyncio.run(check())
"
```

---

## Step 3 — Install/Update Dependencies

If `requirements.txt` or `frontend/package.json` changed:

```bash
# Backend
source .venv/bin/activate
pip install -r requirements-api.txt

# Frontend
cd frontend && npm ci && cd ..
```

---

## Step 4 — Restart the API

```bash
# Preferred: use PM2 (ecosystem.config.cjs already pins --workers 1)
pm2 restart caregist-api

# If using systemd
sudo systemctl restart caregist-api

# If using supervisor
supervisorctl restart caregist-api

# If running manually (dev/staging)
pkill -f "uvicorn api.main:app"
nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1 > /var/log/caregist/api.log 2>&1 &
```

> **Why `--workers 1`?** Caregist uses in-memory token buckets for rate limiting. Running
> multiple workers would give each worker its own independent bucket, effectively multiplying
> the allowed burst rate by the worker count. A single worker eliminates this drift entirely
> without requiring Redis. See [docs/scaling.md](../docs/scaling.md) for the scaling path
> when load eventually warrants more than one worker.

Verify API is up:
```bash
curl -s http://localhost:8000/api/v1/health
# Expected: {"status":"healthy"}
```

---

## Step 5 — Rebuild and Restart the Frontend

```bash
cd /home/caregist/CareGist/frontend

# Build
npm run build

# Restart (if using pm2)
pm2 restart caregist-frontend

# If using systemd
sudo systemctl restart caregist-frontend
```

Verify frontend is up:
```bash
curl -s http://localhost:3000/ | head -5
```

---

## Step 6 — Verify End-to-End

```bash
# Health check
curl https://caregist.co.uk/api/v1/health

# Test a real API endpoint
curl "https://caregist.co.uk/api/v1/providers?q=care&per_page=1" \
  -H "X-API-Key: $API_MASTER_KEY" | python3 -m json.tool | head -20

# Test new registration feed
curl "https://caregist.co.uk/api/v1/feed/new-registrations?per_page=5" \
  -H "X-API-Key: $API_MASTER_KEY" | python3 -m json.tool | head -20

# Full wedge smoke check
python3 tools/smoke_new_registration_pipeline.py \
  --base-url https://caregist.co.uk \
  --api-key "$API_MASTER_KEY" \
  --internal-token "$SUPPORT_INTERNAL_TOKEN"
```

Check Sentry for new errors at https://sentry.io (filter by `release` tag or last 10 minutes).

---

## Step 7 — Run Scheduled Jobs (if first deploy or schedule missed)

```bash
# Refresh care_providers from the CQC changes API
python3 incremental_update.py

# Sync new registration feed and deliver webhooks
python3 tools/run_new_registration_feed_cycle.py

# Send monitor alerts (if daily schedule missed)
python3 tools/send_monitor_alerts.py

# Flush any queued emails
python3 tools/flush_email_queue.py
```

---

## Scheduled Jobs on EC2

Configure these in `/etc/cron.d/caregist`:

```cron
# Incremental CQC refresh — every 30 minutes
*/30 * * * * www-data cd /home/caregist/CareGist && /home/caregist/CareGist/.venv/bin/python3 incremental_update.py >> /var/log/caregist/incremental-update.log 2>&1

# Feed cycle — hourly
5 * * * * www-data cd /home/caregist/CareGist && /home/caregist/CareGist/.venv/bin/python3 tools/run_new_registration_feed_cycle.py >> /var/log/caregist/feed-cycle.log 2>&1

# Flush queued emails — every 10 minutes
*/10 * * * * www-data cd /home/caregist/CareGist && /home/caregist/CareGist/.venv/bin/python3 tools/flush_email_queue.py >> /var/log/caregist/email-queue.log 2>&1
```

---

## Environment Variables (Production `.env`)

The production `.env` must contain all of these. Never commit it to git.

See `.env.example` for the full list. Key variables:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `API_MASTER_KEY` | Internal master key — rotate if exposed |
| `STRIPE_SECRET_KEY` | Live key (`sk_live_...`) in production |
| `STRIPE_WEBHOOK_SECRET` | From Stripe dashboard webhook config |
| `RESEND_API_KEY` | Transactional email |
| `SENTRY_DSN` | Error tracking |
| `WEBHOOK_SECRET_KEY` | AES-256-GCM 32-byte base64 key |

`REDIS_URL` must **not** be set. Caregist runs single-worker uvicorn with in-memory rate
limiting. Setting `REDIS_URL` will cause a hard startup failure. See
[docs/scaling.md](../docs/scaling.md) if you need to reintroduce Redis.

Frontend `.env.local`:
- `API_URL`, `API_KEY`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPPORT_PLATFORM_URL`

---

## Rollback

If the deploy fails or causes errors:

```bash
cd /home/caregist/CareGist
git log --oneline -10          # find previous good SHA
git checkout <previous-sha>
pm2 restart caregist-api
```
