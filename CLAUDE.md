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

CareGist is a UK care provider directory with three main subsystems:

1. **CQC ETL Pipeline** (root `*.py` files) — extracts data from the CQC public API into PostgreSQL
2. **FastAPI Backend** (`api/`) — REST API serving provider data with tiered API key auth and Stripe billing
3. **Next.js Frontend** (`frontend/`) — SSR dashboard and directory UI, deployable alongside the backend on AWS EC2, proxies API calls to the backend

### How They Connect

- The ETL pipeline produces `directory_providers.csv` → seeded into PostgreSQL via `db/seed.py`
- The API reads from PostgreSQL (PostGIS) via `asyncpg` — no ORM, raw SQL in `api/queries/`
- The frontend calls the API server-side via `lib/api.ts` using `X-API-Key` auth header, with 1-hour ISR cache (`revalidate: 3600`)
- Next.js rewrites `/api/*` to the backend URL (`NEXT_PUBLIC_API_URL` / `API_URL` env vars)
- Production deployment target is AWS EC2. Local development can still use Docker Compose and standalone processes.

### Database

PostgreSQL with PostGIS. Schema in `db/init.sql`, migrations in `db/migrations/` (numbered SQL files, applied manually in local/dev and during EC2 deploys via `db/apply_migrations.py`). Key tables: `care_providers` (primary), `api_keys`, `users`, `subscriptions`, `provider_claims`, `reviews`, `enquiries`, `trusted_event_ledger`.

The `care_providers.id` column is the CQC `locationId` (VARCHAR, not auto-increment). Spatial queries use PostGIS `geom` column (SRID 4326). Full-text search uses a GIN index on name/town/postcode/services.

### API Tier System

Defined in `api/config.py` as `TIERS` dict. Tiers (free/starter/pro/business/admin) control: rate limits, daily/monthly quotas, page size, field visibility, nearby search, export limits, comparison slots, and webhook access. Field filtering happens via `filter_fields()` — hidden fields return `None`, not omitted.

### Frontend

Next.js 15 + React 19 + Tailwind CSS 4. App Router (`frontend/app/`). Brand palette defined in `globals.css` as CSS custom properties (clay, bark, parchment, moss, etc.). Typography: Playfair Display (headings), DM Sans (body). Config types and pricing data centralized in `lib/caregist-config.ts`.

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

# --- ETL Pipeline ---
pip install -r requirements.txt
./run_enriched_pipeline.sh                  # Full pipeline
python3 extract_cqc.py --sleep 0.02        # Individual stages
python3 clean_cqc.py
python3 quality_audit.py
python3 prepare_directory.py
```

### Environment Variables

Backend reads from `.env` via pydantic-settings. Key vars: `DATABASE_URL`, `API_MASTER_KEY`, `CORS_ORIGINS`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `RESEND_API_KEY`, `SENTRY_DSN`. Frontend needs: `API_URL` (server-side), `API_KEY`, `NEXT_PUBLIC_API_URL` (client rewrites).

## File Structure

```
api/                    # FastAPI backend
  config.py             # Settings + tier definitions (single source of truth for tiers/fields)
  database.py           # asyncpg connection pool
  routers/              # Route modules (providers, billing, claims, reviews, etc.)
  queries/              # Raw SQL query modules
  middleware/            # Auth (API key), rate limiting, IP rate limiting
  utils/                # Analytics, email queue
frontend/               # Next.js 15 app
  app/                  # App Router pages
  components/           # React components
  lib/api.ts            # Server-side API client (apiFetch with X-API-Key)
  lib/types.ts          # TypeScript interfaces (Provider, Review, User, config types)
  lib/caregist-config.ts # Pricing tiers, feature gates, growth config
db/                     # Database schema
  init.sql              # Base schema (PostGIS, care_providers, api_keys, users, etc.)
  migrations/           # Numbered SQL migrations
  seed.py               # CSV → PostgreSQL seeder
tools/                  # Python scripts for execution (API calls, data transforms, file ops)
workflows/              # Markdown SOPs
tests/                  # pytest tests (mock DB via conftest.py fixtures)
*.py (root)             # CQC ETL pipeline scripts
```

## CQC Directory Pipeline

Python ETL pipeline that extracts UK care provider data from the CQC (Care Quality Commission) public API, cleans/normalizes it, runs quality audits, and produces directory-ready outputs.

### Pipeline Stages

The full pipeline runs via `run_enriched_pipeline.sh` and executes in order:

1. **`extract_cqc.py`** — Pulls all providers and locations from `api.service.cqc.org.uk/public/v1`. Paginates list endpoints, fetches detail endpoints for enrichment. Resumable via `checkpoint.json`; logs failed IDs to `failed_ids.txt`. Caches provider details in `_provider_cache.sqlite`. Outputs `raw_combined.csv`.

2. **`clean_cqc.py`** — Normalizes names, phones (UK format via `phonenumbers`), postcodes, websites, addresses, dates, coordinates, ratings, and taxonomy fields. Deduplicates on `locationId`. Splits into `cleaned_cqc.csv` (active), `inactive_providers.csv`, and `duplicates_removed.csv`.

3. **`quality_audit.py`** — Scores each record (0–100) across weighted fields and assigns data completeness tiers (NOT CQC ratings): COMPLETE ≥85, GOOD ≥60, PARTIAL ≥40, SPARSE <40. Writes scores back into `cleaned_cqc.csv`. Produces `quality_report.json` and `quality_summary.txt`.

4. **`prepare_directory.py`** — Transforms cleaned data into directory-ready schema with slugs, meta titles/descriptions, CQC inspection URLs, and optional geocoding via postcodes.io. Outputs `directory_providers.csv`, `.json`, `.sql`, and `import_to_db.sql` (PostgreSQL + MySQL DDL).

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
