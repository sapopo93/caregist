# Codex Handover — CareGist Pre-Launch Audit
Date: 2026-04-09
From: Claude Sonnet 4.6 (session 63b1745a)
Repo: https://github.com/sapopo93/caregist
Live: https://caregist.co.uk

---

## What was completed today (do not redo)

All committed to main and pushed. Four phases:

**Phase A — Pricing copy/config**
- Free badge: EVALUATION → ENTRY
- Rate labels: req/sec/min → `requests/sec` / `requests/day` everywhere (config, dashboard, API page, error messages)
- Benchmark copy on pricing page
- Pro marked recommended, team seats coming-soon label
- Business webhooks enabled in tier config
- Enterprise 422 with contact email
- Competitor names removed from public pages (LaingBuisson, Lottie)
- "Launch moat" label on homepage partially fixed (interrupted — see below)

**Phase B — Excel export**
- `GET /api/v1/providers/export.xlsx` route live
- ExportCSVButton has CSV | Excel toggle
- openpyxl added to requirements.txt

**Phase C — Per-user rating-change alerts**
- `tools/send_monitor_alerts.py` — queries provider_monitors + provider_rating_history
- Gated to Pro+ tier, idempotent watermark, --dry-run flag
- Migration 011: last_alert_sent_at column on provider_monitors

**Phase D — Outbound webhooks**
- Migration 012: webhook_subscriptions table
- `api/utils/webhook_delivery.py` — HMAC-SHA256, 3x retry
- `api/routers/webhooks.py` — POST/GET/DELETE, Business+ gated
- Webhook dispatch wired into send_monitor_alerts.py for Business+ users

**Internal platform (Codex prior work — also committed)**
- `api/routers/internal.py` — 8 remediation actions, X-Internal-Token auth
- Migrations 007–010: provider profile fields, internal_tasks, idempotency, profile_completeness
- ProfileNav.tsx, ServiceBreakdown.tsx, SupportWidgetMount.tsx
- support_quality_hook.py, db/apply_migrations.py

---

## Interrupted task — finish this first

In `frontend/app/why-caregist/page.tsx`, the edit to line 133 was interrupted.
The following changes still need to be made and committed:

**File: `frontend/app/why-caregist/page.tsx`**
- Line 133: `"Monitor local markets and competitor changes continuously"` → `"Monitor local markets and rating changes continuously"`
- Line 157: `"Operational data use remains the primary GTM narrative"` → remove this bullet entirely (it is internal strategy copy on a public page)

**File: `frontend/app/page.tsx`** (already fixed in session but double-check):
- Line 64: confirm it now reads `"What you get"` not `"Launch moat"`
- Line 162: confirm it reads `"Monitor local markets"` not `"Monitor local competitors"`

**File: `frontend/lib/caregist-config.ts`**
- `pricingLogic` field for Enterprise tier (line ~146) reads:
  `"Enterprise motion for public sector, large care groups, and institutional buyers. Slower deal cycle — expand into after product-market fit with Starter–Business."`
  This is rendered verbatim on the public pricing page (`pricing/page.tsx:89`). Replace with customer-facing copy, e.g.:
  `"Built for commissioners, local authorities, and large care groups who need custom limits, procurement support, and contractual terms."`
- Pro pricingLogic (line ~108): `"designed to stop shared-password use"` — internal framing, soften to something like `"Designed for small teams who need named access, accountability, and enough daily headroom for recurring workflows."`
- Business pricingLogic (line ~128): `"internal ops tooling"` — replace with `"internal workflows and operational tooling"`

---

## Outstanding audit — this is the main task

A principal developer review was requested but not started. Run this audit:

### Security
```bash
# Hardcoded localhost in frontend source
grep -rn "localhost:8000\|localhost:3000\|127\.0\.0\.1" frontend/app/ frontend/components/ frontend/lib/ --include="*.tsx" --include="*.ts" | grep -v ".next/" | grep -v "node_modules"

# Exposed secrets in frontend
grep -rn "sk_live\|sk_test\|whsec_\|rk_live" frontend/ --include="*.tsx" --include="*.ts" --include="*.js" | grep -v ".next/" | grep -v "node_modules" | grep -v "placeholder\|example"

# SQL injection risk (f-string interpolation in queries)
grep -rn 'f".*SELECT\|f".*INSERT\|f".*UPDATE\|f".*DELETE' api/ --include="*.py"

# Routes missing auth
grep -rn "@router\." api/routers/ --include="*.py" | grep -v "Depends(validate_api_key)\|Depends(validate_internal_token)\|health\|#"

# Sensitive data in logs
grep -rn "logger\." api/routers/ --include="*.py" | grep -i "key\|password\|secret\|token" | grep -v "#"
```

### Configuration gaps
```bash
# STRIPE_PRICE_PRO_SEAT missing from render.yaml and .env.example
grep "STRIPE_PRICE_PRO_SEAT\|pro_seat" .env.example render.yaml

# Image domains configured for Next.js (broken image risk)
cat frontend/next.config.ts

# robots.txt exists?
ls frontend/public/robots.txt && cat frontend/public/robots.txt

# 404 page exists?
ls frontend/app/not-found.tsx
```

### Frontend quality
```bash
# console.log left in source
grep -rn "console\.log\|console\.warn\|debugger" frontend/app/ frontend/components/ frontend/lib/ --include="*.tsx" --include="*.ts" | grep -v ".next/" | grep -v "node_modules"

# @ts-ignore / any type escapes
grep -rn "@ts-ignore\|@ts-expect-error\|eslint-disable\|: any>" frontend/app/ frontend/components/ frontend/lib/ --include="*.tsx" --include="*.ts" | grep -v ".next/" | grep -v "node_modules"

# Missing loading.tsx / error.tsx per route
find frontend/app -name "loading.tsx" -o -name "error.tsx" | sort

# Meta descriptions on key pages
grep -rn "export const metadata" frontend/app/pricing/page.tsx frontend/app/page.tsx frontend/app/why-caregist/page.tsx frontend/app/api/page.tsx
```

### Missing features vs competitors
These were identified but not built. Assess feasibility and prioritise:

1. **Seat enforcement at auth layer** — `max_users` is stored in subscriptions table but never checked during `validate_api_key`. A Pro user can share their key with unlimited people. The check needs to count active API keys per organisation/user_id and block new key creation above the seat limit.

2. **Email verification on signup** — unknown if implemented. Check `api/routers/auth.py` for email verification flow.

3. **Password reset flow** — `frontend/app/forgot-password/page.tsx` exists. Check if the backend route is wired and tested.

4. **Rate limit persistence across restarts** — all rate limit state is in-memory (`api/middleware/rate_limit.py`). Render free tier spins down. On wake, all daily/weekly quotas reset. Free users can game this. Fix: move daily/weekly counts to Redis or Postgres.

5. **Export row count in response headers** — the CSV export sets `X-Total-Count` header. Verify it's present and correct on xlsx too.

6. **No email on monitor alert failure** — if `send_monitor_alerts.py` fails mid-run (e.g. DB timeout), no notification. Add basic error alerting.

7. **Webhook retry visibility** — `delivery_failures` is incremented but never surfaced to the user in the dashboard. Add it to the GET /webhooks response (already there) but verify the frontend reads it.

8. **Provider profile completeness score** — migration 010 adds `profile_completeness` column, internal.py has `_recompute_profile_completeness` action, but there is no scheduled job calling it. It will only update when triggered via the internal API.

9. **Missing OG images** — check if `opengraph-image.tsx` or `twitter-image.tsx` exist per key route. Critical for social sharing.

10. **No sitemap for provider profiles** — `frontend/app/sitemap.ts` likely only covers static pages. With 55,818 providers it needs dynamic sitemap splitting (Google limit: 50,000 URLs per sitemap file).

---

## Key files reference

| File | Purpose |
|---|---|
| `api/config.py` | Single source of truth for tier limits, field sets |
| `api/middleware/rate_limit.py` | In-memory rate limiter (burst, daily, 7d, monthly) |
| `api/middleware/auth.py` | API key validation, calls check_rate_limit |
| `api/routers/billing.py` | Stripe checkout, webhook handler, seat logic |
| `api/routers/providers.py` | Main provider routes incl. export.csv and export.xlsx |
| `api/routers/webhooks.py` | Webhook subscription CRUD |
| `api/utils/webhook_delivery.py` | HMAC-SHA256 delivery, retry logic |
| `tools/send_monitor_alerts.py` | Cron script: rating change emails + webhook dispatch |
| `frontend/lib/caregist-config.ts` | All frontend pricing, tier copy, rate labels |
| `frontend/app/pricing/page.tsx` | Pricing page — renders pricingLogic from config |
| `db/migrations/` | 001–012 applied; 013+ needed for any new schema |

## Env vars needed but not yet in render.yaml
- `STRIPE_PRICE_PRO_SEAT` — seat add-on price ID
- `STRIPE_PRICE_ENTERPRISE` — in .env.example but not render.yaml
- `SUPPORT_PLATFORM_URL`, `CAREGIST_TO_SUPPORT_TOKEN`, `SUPPORT_INTERNAL_TOKEN` — for internal API and quality hook
- `NEXT_PUBLIC_API_URL` — must be set in Vercel dashboard to the Render service URL, otherwise all /api/* rewrites fall back to localhost:8000 and return 404

## DB connection
```
postgresql://neondb_owner:npg_peob3Oh5UcIQ@ep-wandering-grass-abgnc3qe-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require
```

## Run tests
```bash
cd /Users/user/CareGist
.venv/bin/python -m pytest tests/ -v
```

## Start API locally for testing
```bash
DATABASE_URL="postgresql://..." API_MASTER_KEY="local-test-key" CORS_ORIGINS="http://localhost:3000" .venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8001 --log-level warning
```
