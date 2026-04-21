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
# If using systemd
sudo systemctl restart caregist-api

# If using supervisor
supervisorctl restart caregist-api

# If running manually (dev/staging)
pkill -f "uvicorn api.main:app"
nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 2 > /var/log/caregist/api.log 2>&1 &
```

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
*/10 * * * * www-data cd /home/caregist/CareGist && /home/caregist/CareGist/.venv/bin/python3 tools/flush_email_queue.py >> /var/log/caregist/email-flush.log 2>&1

# Pipeline watchdog — every 15 minutes with deduplicated email alerts
*/15 * * * * www-data cd /home/caregist/CareGist && /home/caregist/CareGist/.venv/bin/python3 tools/check_new_registration_pipeline.py --notify >> /var/log/caregist/pipeline-watchdog.log 2>&1

# Monitor alerts — daily at 08:00
0 8 * * * www-data cd /home/caregist/CareGist && /home/caregist/CareGist/.venv/bin/python3 tools/send_monitor_alerts.py >> /var/log/caregist/monitor-alerts.log 2>&1

# Weekly movers digest — Mondays at 07:00
0 7 * * 1 www-data cd /home/caregist/CareGist && /home/caregist/CareGist/.venv/bin/python3 tools/send_weekly_movers.py >> /var/log/caregist/weekly-movers.log 2>&1
```

---

## Environment Variables (Production `.env`)

The production `.env` must contain all of these. Never commit it to git.

```
DATABASE_URL=postgresql://...
API_MASTER_KEY=<secure random>
SUPPORT_INTERNAL_TOKEN=<secure random>
CORS_ORIGINS=https://caregist.co.uk
APP_URL=https://caregist.co.uk
CQC_API_KEY=<cqc subscription key>

STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ALERTS_PRO=price_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_BUSINESS=price_...
STRIPE_PRICE_PRO_SEAT=price_...
STRIPE_PRICE_PROFILE_ENHANCED=price_...
STRIPE_PRICE_PROFILE_PREMIUM=price_...
STRIPE_PRICE_PROFILE_SPONSORED=price_...

RESEND_API_KEY=re_...
ENQUIRY_FROM_EMAIL=noreply@caregist.co.uk
PIPELINE_ALERT_EMAIL=ops@caregist.co.uk
SENTRY_DSN=https://...@sentry.io/...
```

Frontend `.env.local`:
```
API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=https://caregist.co.uk
API_KEY=<same as API_MASTER_KEY or a dedicated frontend key>
```

Do not set `NEXT_PUBLIC_API_KEY` in production. That exposes a privileged backend key to the browser bundle and creates split-brain key rotation risk between client and server config.

---

## Rollback

If the deploy fails or causes errors:

```bash
# Roll back code
git log --oneline -10       # Find the last good commit
git checkout <commit-hash>

# Restart services (steps 4 and 5 above)

# If a migration caused issues — restore from database backup
# (Neon: restore from branch, RDS: restore from snapshot)
```

---

## Troubleshooting

**API fails to start — "API_MASTER_KEY is still the default"**
- `.env` on the server is missing `API_MASTER_KEY` or has the placeholder value
- Set a secure random value: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

**API fails to start — "FATAL: Live Stripe secret key in local development"**
- The server's DATABASE_URL matches the localhost default
- Check DATABASE_URL in server `.env` is pointing to production Neon, not localhost

**Frontend 500 errors on load**
- Check `API_URL` in frontend `.env.local` points to the running API
- Verify API health: `curl http://localhost:8000/api/v1/health`

**Webhook deliveries failing**
- Check `webhook_delivery_log` for error details
- Verify Stripe webhook secret matches the endpoint in the Stripe dashboard
- Check Stripe Dashboard → Webhooks → endpoint → recent events
