# CareGist — Technical Completion Report

**Prepared for:** Prospective investors
**Date:** 28 March 2026
**Status:** Product complete. Ready for deployment and first customers.

---

## Executive Summary

CareGist is a care provider intelligence platform for the UK market. It transforms raw Care Quality Commission (CQC) regulatory data into a searchable, scorable, validated directory of **55,818 active care providers** across England — covering care homes, nursing homes, GP surgeries, dental practices, home care agencies, and supported living providers.

The product is fully built: data pipeline, REST API, consumer frontend, billing system, and growth features. It is ready to deploy and accept paying customers.

---

## What Was Built

### Data Layer (the moat)

| Metric | Value |
|--------|-------|
| Active providers | 55,818 |
| Data completeness (COMPLETE tier) | 98.2% |
| Coordinate coverage | 99.99% (3 records missing) |
| CQC rating accuracy vs live API | 99.5% (200-record validation) |
| Phone number coverage | 99.8% |
| Service type coverage | 99.99% |
| Key question ratings (Safe/Effective/Caring/Responsive/Well-Led) | Populated |
| Researcher fields (UPRN, ODS, ICB, constituency) | Populated |

The data pipeline extracts from the CQC public API, normalises UK-specific fields (postcodes, phone numbers, coordinates, ratings), deduplicates on location ID, scores each record across 14 weighted dimensions, and validates against live CQC data to detect staleness.

**Competitive advantage:** A new entrant would need 3-6 months to replicate this pipeline. The validation system (which cross-references our data against the live CQC website) is not commercially available elsewhere.

### API (the product)

15+ REST endpoints serving provider data from PostgreSQL + PostGIS:

- **Search** — Full-text search with region, rating, service type, postcode filters, 7 sort options
- **Nearby** — Geographic radius search using PostGIS spatial indexes
- **Compare** — Side-by-side comparison of up to 3 providers
- **Export** — CSV download of search results (up to 10,000 rows)
- **Detail** — Complete provider profile with all 40+ fields
- **Lookups** — Regions, service types, ratings with provider counts

Authentication via API key (auto-generated on registration). Rate limiting enforced per tier. All queries parameterised (no SQL injection risk).

### Frontend (the experience)

Consumer-facing directory at feature parity with established competitors:

- Homepage with search, stats, and service type browsing
- Search results with filter sidebar, sort dropdown, map toggle (Leaflet/OpenStreetMap)
- Provider detail pages with CQC ratings (all 5 key questions), contact info, Google Maps link, inspection report link
- Region and service type browse pages
- Loading skeletons, error boundaries, branded 404 page
- Per-page SEO metadata (55,818 unique title/description combinations)

Brand system: warm earth-tone palette (terracotta, moss, parchment) deliberately positioned against clinical healthcare blue. Typography: Playfair Display (display), Lora (body), DM Sans (UI).

### Billing (the revenue)

Stripe integration with three tiers:

| Tier | Price | Rate Limit | Features |
|------|-------|------------|----------|
| Free | £0 | 100 req/min | Search + basic details |
| Starter | £49/month | 1,000 req/min | Full API + CSV export + nearby |
| Pro | £199/month | 5,000 req/min | Everything + bulk export + priority support |

Self-serve flow: signup → API key generated instantly → optional Stripe checkout for paid tiers → dashboard with key display, plan info, and usage guide.

Webhook handler processes subscription lifecycle (upgrades, downgrades, cancellations) and automatically adjusts API key tier and rate limits.

### Growth Features (the flywheel)

| Feature | Business Purpose | Status |
|---------|-----------------|--------|
| Provider claiming | Providers claim listings → invest in profile → attract clients | Built (with admin moderation) |
| Reviews | User-generated content → SEO + trust signals → more visitors | Built (1-5 stars, moderation queue) |
| Enquiry forms | Lead capture → monetisable referrals to providers | Built (name, email, care type, urgency) |
| Comparison tool | Decision support → higher engagement → longer sessions | Built (up to 3 providers side-by-side) |
| Admin dashboard | Operational control → moderate claims/reviews/enquiries | Built (stats, queues, approve/reject) |

### Infrastructure

| Component | Technology | Status |
|-----------|-----------|--------|
| Database | PostgreSQL 16 + PostGIS | Schema complete, seeded, indexed |
| API | Python FastAPI + asyncpg | Built, containerised |
| Frontend | Next.js 15 + Tailwind CSS | Built, Vercel-ready |
| Containers | Docker + docker-compose | One-command local deployment |
| Tests | pytest (139 passing) | Pipeline + API coverage |
| CI/CD | Railway (API) + Vercel (frontend) configs | Deployment configs ready |
| Data refresh | Incremental update script (CQC changes API) | Built, needs scheduling |

---

## Total Addressable Market

55,818 active providers across England:

| Segment | Providers | UK Sector Value |
|---------|-----------|-----------------|
| Homecare agencies | 14,240 | ~£200M |
| Dental practices | 12,004 | ~£9B |
| Residential care homes | 10,309 | ~£30B |
| GP surgeries | 9,367 | ~£16B |
| Supported living | 4,727 | — |
| Nursing homes | 4,386 | — |
| Other (clinics, ambulance, NHS) | 785 | — |

Geographic coverage: all 9 English regions. South East (9,731), London (9,266), North West (7,099) are the three largest.

### Target Customers (B2B data API)

1. **Care placement agencies** — Currently search CQC manually. Our API saves hours per placement.
2. **Local authority commissioning teams** — Need provider intelligence for procurement decisions.
3. **PropTech companies** — Need "nearby care homes" data for property listings.
4. **Insurance underwriters** — Need portfolio risk assessment on care provider portfolios.
5. **Care comparison startups** — Need a data layer to build consumer products on.

### Revenue Model

Three monetisation paths, all proven in the UK care market:

1. **Data API subscriptions** (Starter £49/mo, Pro £199/mo) — Highest margin (~90%), fastest to revenue
2. **Lead generation** — Enquiry forms capture family details; providers pay £5-15 per qualified lead
3. **Provider listings** — Claimed profiles with enhanced features; providers pay £20-100/month

---

## What's Not Built (and doesn't need to be for launch)

- Mobile app (responsive web works on mobile)
- Email notification system (can use Resend or SendGrid when needed)
- Analytics dashboard for providers (post-first-customer feature)
- Multi-country support (England-only is the correct scope for launch)

---

## Deployment Checklist (remaining)

| Step | Time | Cost |
|------|------|------|
| Stripe account + product setup | 20 min | Free (2.9% + 20p per transaction) |
| Domain registration (caregist.co.uk) | 10 min | ~£8/year |
| Deploy API to Railway | 30 min | ~£5/month |
| Deploy frontend to Vercel | 15 min | Free (hobby tier) |
| Deploy managed PostgreSQL | 15 min | ~£7/month (Neon free tier or Railway) |
| Seed database | 5 min | — |
| Stripe webhook configuration | 10 min | — |
| **Total** | **~2 hours** | **~£12/month** |

---

## Investment Thesis

**The gap in the market:** CQC publishes inspection data for 120,000+ regulated providers, but their own search is poor (no map, no comparison, no API, limited filtering). Existing commercial directories (carehome.co.uk, Lottie) are pay-to-play or concierge models. No one offers a neutral, data-first, API-accessible directory.

**What CareGist offers:** Every CQC-registered provider, cleaned and geocoded, accessible via API. No pay-to-play rankings. Data you can trust because it comes straight from the regulator.

**The defensible advantage:** The data pipeline (extraction, cleaning, validation) is 3-6 months of specialised work. The validation system (99.5% accuracy vs live CQC) is unique. The quality scoring (14-dimension weighted model) adds intelligence that raw CQC data lacks.

**Path to revenue:**
- Month 1: Deploy, send 20 outreach emails
- Month 2: First 3 customers on free trial (Starter tier)
- Month 3: Convert to paying (£150-600 MRR)
- Month 6: 20 customers, £1,000-4,000 MRR
- Month 12: 50 customers, £5,000+ MRR, seed-ready

**Capital needed:** £0 to launch. ~£20k to hire part-time sales/marketing for 6 months. Seed round (£500k-1.5M) makes sense at £5k MRR to fund engineering team and go-to-market acceleration.

---

## Technical Summary

| Metric | Value |
|--------|-------|
| Total lines of code | ~11,000 |
| Files | 80+ |
| Test coverage | 139 tests passing |
| Languages | Python (backend/pipeline), TypeScript (frontend) |
| Database | PostgreSQL 16 + PostGIS (55,818 records, 8 indexes, spatial search) |
| API endpoints | 15+ |
| Frontend pages | 12 (homepage, search, detail, compare, pricing, signup, login, dashboard, admin, region, services, 404) |
| Monthly infrastructure cost | ~£12 |
| Time to deploy | ~2 hours |

---

*CareGist — the gist of good care.*

*Built March 2026. Ready for customers.*
