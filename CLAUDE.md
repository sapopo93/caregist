# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Rules

- Check `tools/` and `workflows/` for existing scripts and SOPs before building anything new.
- Don't create or overwrite workflow files (`workflows/*.md`) without asking first.
- If a script uses paid API calls or credits, confirm with the user before re-running it.
- When you fix a bug or discover a constraint (rate limits, timing quirks), update the relevant workflow with what you learned.
- Credentials and API keys live in `.env` — never store secrets anywhere else.
- Final deliverables go to cloud services (Google Sheets, Slides, etc.). Local files are for processing only. Everything in `.tmp/` is disposable.

## Architecture Overview

CareGist is a UK care provider intelligence platform with four main subsystems:

1. **CQC ETL Pipeline** (root `*.py` files) — extracts data from the CQC public API into PostgreSQL
2. **FastAPI Backend** (`api/`) — REST API with tiered API key auth, Stripe billing, new registration feed, and outbound webhooks
3. **Next.js Frontend** (`frontend/`) — SSR directory UI and authenticated dashboard, deployable on AWS EC2, proxies API calls to the backend
4. **Operational Tools** (`tools/`) — Python scripts for recurring jobs (feed cycle, monitor alerts, email queue, weekly digests)

### How They Connect

- The ETL pipeline produces `directory_providers.csv` → seeded into PostgreSQL via `db/seed.py`
- The API reads from PostgreSQL (PostGIS) via `asyncpg` — no ORM, raw SQL in `api/queries/`
- The frontend calls the API server-side via `lib/api.ts` using `X-API-Key` auth header, with 1-hour ISR cache (`revalidate: 3600`)
- Next.js rewrites `/api/*` to the backend URL (`NEXT_PUBLIC_API_URL` / `API_URL` env vars)
- Email is queued to the `pending_emails` table and drained via Resend on each `/api/v1/health` request
- Outbound webhooks (Business+) are delivered by `api/utils/webhook_delivery.py`, signed with HMAC-SHA256
- Production deployment target is AWS EC2. Local development uses standalone processes.

### Database

PostgreSQL with PostGIS. Schema in `db/init.sql`, migrations in `db/migrations/` (17 numbered SQL files, applied via `db/apply_migrations.py`). Applied migrations are tracked in `schema_migrations`.

**Primary tables:**

| Table | Purpose |
|-------|---------|
| `care_providers` | All 55,818+ CQC-registered providers (primary entity) |
| `api_keys` | User API keys — tier, is_active, last_used_at, rate_limit |
| `users` | Registered accounts — email, password_hash, stripe_customer_id, is_verified |
| `subscriptions` | Stripe subscription state — tier, status, included_users, extra_seats, max_users |
| `provider_claims` | Provider listing ownership claims (admin-moderated) |
| `reviews` | User-submitted provider reviews (moderation queue) |
| `enquiries` | Contact enquiries submitted via provider pages |
| `trusted_event_ledger` | Source of truth for all feed events — new registrations, rating changes |
| `analytics_events` | First-party API and frontend analytics events |
| `rating_changes` | Rating change history for monitor alerts and weekly digests |
| `weekly_digest_log` | Delivery tracking for weekly movers digest emails |
| `internal_tasks` | UUID-keyed tasks from support platform integration |
| `webhook_subscriptions` | Business+ outbound webhook registrations (url, events, HMAC secret) |
| `webhook_delivery_log` | Delivery attempt history for outbound webhooks |
| `api_rate_usage_daily` | Per-key daily API usage counters |
| `feed_digest_subscriptions` | Weekly new-registration digest subscriptions per user |
| `feed_digest_delivery_log` | Delivery tracking for feed digest emails |
| `stripe_processed_events` | Processed Stripe event IDs (24h dedup window) |
| `care_groups` | Materialized view — care group aggregations across locations |
| `pending_emails` | Async email queue (status, attempts, send_after) |
| `postcode_cache` | Geocoding cache from postcodes.io |
| `password_reset_tokens` | Time-limited password reset codes |

**`care_providers` extended columns (added by migrations):**
`profile_tier`, `profile_completeness`, `profile_description`, `profile_photos`, `virtual_tour_url`, `inspection_response`, `inspection_summary`, `logo_url`, `funding_types`, `fee_guidance`, `min_visit_duration`, `contract_types`, `age_ranges`, `group_name`, `profile_updated_at`, `profile_subscription_id`, `is_claimed`

The `care_providers.id` column is the CQC `locationId` (VARCHAR, not auto-increment). Spatial queries use PostGIS `geom` column (SRID 4326). Full-text search uses a GIN index on name/town/postcode/services/local_authority.

### API Routers

All routers are registered in `api/main.py`. Full list:

| Router | Prefix | Purpose |
|--------|--------|---------|
| `health` | `/api/v1/health` | Health check — also triggers email queue drain |
| `auth` | `/api/v1/auth` | Registration, login, API key management, password reset |
| `providers` | `/api/v1/providers` | Search, detail, nearby, export, lookups |
| `feed` | `/api/v1/feed` | New registration feed, exports, saved filters, digests |
| `billing` | `/api/v1/billing` | Stripe checkout (B2B + provider), subscription state, webhooks |
| `webhooks` | `/api/v1/webhooks` | Business+ outbound webhook subscriptions |
| `claims` | `/api/v1/claims` | Provider listing claim submissions |
| `provider_profile` | `/api/v1/provider-profile` | Claimed/paid provider profile management |
| `reviews` | `/api/v1/reviews` | Provider reviews (submit, list, moderate) |
| `enquiries` | `/api/v1/enquiries` | Provider enquiry forms |
| `comparisons` | `/api/v1/comparisons` | Saved provider comparisons |
| `groups` | `/api/v1/groups` | Care group aggregation |
| `regions` | `/api/v1/regions` | Region list and provider counts |
| `region_stats` | `/api/v1/region-stats` | Local authority rating distributions |
| `city_pages` | `/api/v1/city-pages` | City-level provider listings (SEO) |
| `analytics` | `/api/v1/analytics` | First-party event ingestion |
| `subscribe` | `/api/v1/subscribe` | Email newsletter subscriptions |
| `api_applications` | `/api/v1/api-applications` | Self-serve API access applications |
| `public_tools` | `/api/v1/tools` | Radius finder, postcode lookup |
| `sitemaps` | `/sitemap.xml`, `/provider-sitemap-*` | Dynamic XML sitemaps |
| `admin` | `/api/v1/admin` | Admin moderation (claims, reviews, enquiries) |
| `internal` | `/api/v1/internal` | Support-platform integration (token-gated) |

### API Tier System

**B2B API tiers** (demand side — data consumers). Defined in `api/config.py` as `TIERS` dict:

| Tier | Price | Rate | Daily | Feed | Webhooks | Users |
|------|-------|------|-------|------|----------|-------|
| free | £0 | 2/s | 20 | 10 rows, view-only | No | 1 |
| alerts-pro | £49/mo | 5/s | 200 | No feed (monitors only) | No | 1 |
| starter | £99/mo | 10/s | 500 | 25 rows, CSV/XLSX export | No | 1 |
| pro | £199/mo | 25/s | 2,000 | 50 rows, 20 saved filters | No | 3 (+seats) |
| business | £499/mo | 60/s | 10,000 | 100 rows, 100 saved filters, webhooks | Yes | 10 (+seats) |
| enterprise | custom | 200/s | 50,000 | 250 rows, 500 saved filters, webhooks | Yes | 10 (+seats) |
| admin | internal | unlimited | unlimited | unlimited | Yes | — |

Tiers also control: `page_size`, `fields` visibility (`basic`/`standard`/`full`), `nearby` search, `export` row limit, `compare` slots, `monitors` count, `feed_digests` count, `seat_price_gbp`.

Field filtering happens via `filter_fields()` in `api/config.py` — restricted fields return `None` (not omitted, to preserve API schema shape).

**Provider listing tiers** (supply side — care providers paying to enhance their profile). Managed via `api/routers/provider_profile.py`:

| Tier | Price | Features |
|------|-------|---------|
| claimed | £0 | Verified badge, inspection response |
| enhanced | £99/mo | Description, photos, virtual tour |
| sponsored | £149/mo | Sponsored badge, top placement |
| enterprise | contact | Multi-location custom package |

Maps to `care_providers.profile_tier`. Separate Stripe price IDs: `STRIPE_PRICE_PROFILE_ENHANCED`, `STRIPE_PRICE_PROFILE_PREMIUM`, `STRIPE_PRICE_PROFILE_SPONSORED`.

### New Registration Feed

The core product wedge. Delivers a live stream of newly CQC-registered care providers to paid subscribers.

- **Event source:** `trusted_event_ledger` table (event_type: `new_registration`)
- **Service layer:** `api/services/new_registration_feed.py` — handles sync from `care_providers`, dedup via `dedupe_key` (`new_registration:{location_id}:{registration_date}`)
- **Feed endpoint:** `GET /api/v1/feed/new-registrations` — requires Starter+
- **Exports:** `GET /api/v1/feed/new-registrations/export.csv|xlsx` — requires Starter+
- **Saved filters:** `POST /api/v1/feed/new-registrations/saved-filters` — Starter (3), Pro (20), Business (100)
- **Digest subscriptions:** `PUT /api/v1/feed/new-registrations/digest` — weekly email, requires Starter+
- **Outbound webhooks:** Business+ users can register webhook URLs to receive `feed.new_registration` events, signed with HMAC-SHA256
- **Operational sync:** `tools/run_new_registration_feed_cycle.py` — run hourly in production

### Seat/Team Billing

- `subscriptions` table stores `included_users`, `extra_seats`, `max_users`, `seat_price_gbp`
- `STRIPE_PRICE_PRO_SEAT` enables Pro seat add-ons (£15/seat/mo)
- Auth middleware enforces `active_keys <= max_users` per account — excess keys are rejected
- Seat capacity managed via `/api/v1/auth/team-keys` endpoints

### Email & Notifications

- **Email queue:** `api/utils/email_queue.py` — `queue_email()` inserts to `pending_emails`, `process_email_queue()` sends via Resend API
- **Drain trigger:** health check middleware in `api/main.py` — drains 20 emails per health request
- **Manual flush:** `tools/flush_email_queue.py`
- **Monitor alerts:** `tools/send_monitor_alerts.py` — daily, Pro+ users watching providers
- **Weekly movers:** `tools/send_weekly_movers.py` — Monday, personalised CQC rating change digest
- **Feed digests:** queued by `run_new_registration_feed_cycle.py`, sent via email queue

### Frontend

Next.js 15 + React 19 + Tailwind CSS 4. App Router (`frontend/app/`). Brand palette defined in `globals.css` as CSS custom properties (clay, bark, parchment, moss, etc.). Typography: Playfair Display (headings), DM Sans (body). Config types and pricing data centralized in `lib/caregist-config.ts`.

Key pages: `/` (home), `/search`, `/provider/[slug]`, `/provider-dashboard/[slug]`, `/dashboard`, `/admin`, `/groups/[slug]`, `/find-care`, `/compare`, `/pricing`, `/region/[slug]`, rating pages (`/good-care-homes`, `/outstanding-care-homes`, etc.), auth flows, legal pages.

### Observability

- **Sentry:** initialized in `api/main.py` — traces_sample_rate=0.1, profiles_sample_rate=0.1. Environment auto-detected (production if DATABASE_URL is not localhost). Controlled by `SENTRY_DSN`.
- **Logging:** structured JSON in production, human-readable locally (`api/logging_config.py`)
- **API rate usage:** tracked daily in `api_rate_usage_daily` table

### Internal Support Platform Integration

- `api/routers/internal.py` — token-gated endpoints for a separate support platform to trigger actions (remediation, email flush, index rebuild)
- Gated by `SUPPORT_INTERNAL_TOKEN` (checked with `secrets.compare_digest`)
- Tasks tracked in `internal_tasks` table with `idempotency_key` for dedup
- Outbound callbacks to support platform use `CAREGIST_TO_SUPPORT_TOKEN`

## Development Commands

```bash
# --- Backend ---
docker compose up db          # Start PostgreSQL (PostGIS)
docker compose up seed        # Seed DB from directory_providers.csv
uvicorn api.main:app --reload # API at localhost:8000 (docs at /docs)

# --- Frontend ---
cd frontend && npm run dev    # Next.js dev at localhost:3000
cd frontend && npm run build  # Production build

# --- Tests ---
pytest                        # All tests (mocked DB, no real connection needed)
pytest tests/test_api_reviews.py            # Single test file
pytest tests/test_api_reviews.py::test_name # Single test

# --- Operational tools ---
python3 tools/run_new_registration_feed_cycle.py  # Sync feed + deliver webhooks + queue digests
python3 tools/send_monitor_alerts.py              # Send rating-change alerts to Pro+ users
python3 tools/send_weekly_movers.py               # Send weekly movers digest
python3 tools/flush_email_queue.py                # Manually drain pending_emails
python3 db/apply_migrations.py                    # Apply pending DB migrations

# --- ETL Pipeline ---
pip install -r requirements.txt
./run_enriched_pipeline.sh                  # Full pipeline
python3 extract_cqc.py --sleep 0.02        # Individual stages
python3 clean_cqc.py
python3 quality_audit.py
python3 prepare_directory.py
```

### Environment Variables

Backend reads from `.env` via pydantic-settings:

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `API_MASTER_KEY` | Yes | Master API key (no default — must be set) |
| `SUPPORT_INTERNAL_TOKEN` | Yes | Gates `/api/v1/internal/*` endpoints |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (default: localhost:3000) |
| `STRIPE_SECRET_KEY` | Yes | Stripe API key (`sk_test_` in dev, `sk_live_` in prod) |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |
| `STRIPE_PRICE_ALERTS_PRO` | Yes | Stripe price ID for Alerts Pro tier |
| `STRIPE_PRICE_STARTER` | Yes | Stripe price ID for Starter tier |
| `STRIPE_PRICE_PRO` | Yes | Stripe price ID for Pro tier |
| `STRIPE_PRICE_BUSINESS` | Yes | Stripe price ID for Business tier |
| `STRIPE_PRICE_PRO_SEAT` | No | Stripe price ID for Pro seat add-on |
| `STRIPE_PRICE_PROFILE_ENHANCED` | No | Provider Enhanced listing price |
| `STRIPE_PRICE_PROFILE_PREMIUM` | No | Provider Premium listing price |
| `STRIPE_PRICE_PROFILE_SPONSORED` | No | Provider Sponsored listing price |
| `RESEND_API_KEY` | Yes | Resend email API key |
| `ENQUIRY_FROM_EMAIL` | Yes | From address for outbound emails |
| `SENTRY_DSN` | No | Sentry error tracking DSN |
| `APP_URL` | No | Base URL for redirect links (default: localhost:3000) |
| `SUPPORT_PLATFORM_URL` | No | URL of support platform for task callbacks |
| `CAREGIST_TO_SUPPORT_TOKEN` | No | Auth token for outbound calls to support platform |

Frontend reads from `frontend/.env.local`:
- `API_URL` — server-side backend URL
- `API_KEY` — server-side API key (master key or dedicated frontend key)
- `NEXT_PUBLIC_API_URL` — client-side rewrite base URL
- Never set `NEXT_PUBLIC_API_KEY` — that exposes a privileged backend credential to the browser bundle

**Stripe environment guard:** The API will refuse to start with `sk_live_` if the DATABASE_URL is the localhost default. Use `sk_test_` credentials for local development.

## File Structure

```
api/                       # FastAPI backend
  config.py                # Settings + tier definitions (single source of truth)
  database.py              # asyncpg connection pool
  main.py                  # App factory — router registration, middleware, lifespan
  logging_config.py        # Structured JSON logging
  routers/                 # All 22 route modules
  queries/                 # Raw SQL query modules
  middleware/
    auth.py                # API key validation + seat enforcement
    rate_limit.py          # Per-key in-memory rate limiting
    ip_rate_limit.py       # Per-IP rate limiting (public endpoints)
  utils/
    analytics.py           # First-party analytics event logging
    email_queue.py         # queue_email() + process_email_queue() via Resend
    webhook_delivery.py    # Outbound HMAC-signed webhook delivery
  services/
    new_registration_feed.py  # Feed sync, filtering, digest logic
frontend/                  # Next.js 15 app
  app/                     # App Router pages (27 route groups)
  components/              # React components (~40)
  lib/
    api.ts                 # Server-side API client (apiFetch with X-API-Key)
    types.ts               # TypeScript interfaces (Provider, Review, User, etc.)
    caregist-config.ts     # PRICING_LADDER, PROVIDER_TIERS, feature gates
db/
  init.sql                 # Base schema (PostGIS, all core tables)
  migrations/              # 17 numbered SQL migrations (001–017)
  apply_migrations.py      # Migration runner (idempotent)
  seed.py                  # CSV → PostgreSQL seeder
tools/
  run_new_registration_feed_cycle.py  # Hourly: sync feed, webhooks, digests
  send_monitor_alerts.py              # Daily: Pro+ rating-change alerts
  send_weekly_movers.py               # Weekly: CQC movers digest
  populate_group_names.py             # One-time: backfill group_name column
  flush_email_queue.py                # Manual: drain pending_emails
workflows/                 # Markdown SOPs for operational tasks
  apply-migrations.md
  deploy-ec2.md
  flush-email-queue.md
  run-feed-cycle.md
  send-monitor-alerts.md
tests/                     # pytest tests (mock DB via conftest.py fixtures)
*.py (root)                # CQC ETL pipeline scripts
```

## CQC Directory Pipeline

Python ETL pipeline that extracts UK care provider data from the CQC public API, cleans/normalizes it, runs quality audits, and produces directory-ready outputs.

### Pipeline Stages

The full pipeline runs via `run_enriched_pipeline.sh` and executes in order:

1. **`extract_cqc.py`** — Pulls all providers and locations from `api.service.cqc.org.uk/public/v1`. Paginates list endpoints, fetches detail endpoints for enrichment. Resumable via `checkpoint.json`; logs failed IDs to `failed_ids.txt`. Caches provider details in `_provider_cache.sqlite`. Outputs `raw_combined.csv`.

2. **`clean_cqc.py`** — Normalizes names, phones (UK format via `phonenumbers`), postcodes, websites, addresses, dates, coordinates, ratings, and taxonomy fields. Deduplicates on `locationId`. Splits into `cleaned_cqc.csv` (active), `inactive_providers.csv`, and `duplicates_removed.csv`.

3. **`quality_audit.py`** — Scores each record (0–100) across weighted fields and assigns data completeness tiers (NOT CQC ratings): COMPLETE ≥85, GOOD ≥60, PARTIAL ≥40, SPARSE <40. Writes scores back into `cleaned_cqc.csv`. Produces `quality_report.json` and `quality_summary.txt`.

4. **`prepare_directory.py`** — Transforms cleaned data into directory-ready schema with slugs, meta titles/descriptions, CQC inspection URLs, and optional geocoding via postcodes.io. Outputs `directory_providers.csv`, `.json`, `.sql`, and `import_to_db.sql`.

### Shared Module

`cqc_common.py` — Shared utilities: `normalize_whitespace`, `parse_any_date`, `ensure_list`, `flatten_json`, `deep_get`, `first_non_empty`, `to_float`, `as_json`.

### Data Flow

```
CQC API → raw_combined.csv → cleaned_cqc.csv → directory_providers.{csv,json,sql}
                               ├── inactive_providers.csv
                               ├── duplicates_removed.csv
                               └── quality_report.json / quality_summary.txt
```

Intermediate files prefixed with `_` (e.g., `_providers_list.ndjson`, `_provider_cache.sqlite`) are regenerable pipeline artifacts.

### Key Conventions

- CQC API key is passed via `CQC_API_KEY` environment variable
- UK-specific validation: postcodes match `^[A-Z]{1,2}[0-9][0-9A-Z]?\s[0-9][A-Z]{2}$`, coordinates within 49–61°N / 8°W–2°E
- Taxonomy fields (service types, specialisms, regulated activities) are pipe-delimited (`|`)
- `locationId` is the primary key for deduplication and record identity
- The extract stage is resumable via `checkpoint.json`
