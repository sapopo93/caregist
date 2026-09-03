# CareGist Product Specification: New-Provider Intelligence Suite

> **Superseded product specification — historical and non-operative.** The
> products, tiers, prices, entitlements, forecasts, and “live” labels below
> predate catalogue `2026-08` and must not be used for implementation, public
> copy, quoting, outreach, or release approval. Current authority is
> `docs/CAREGIST_MASTER_STRATEGY.md` and
> `deploy/stripe-price-manifest.json`.

## Executive Summary

CareGist will own the "new registration" signal in UK social care by packaging CQC registration data into three ascending product tiers. Each tier targets a distinct buyer persona, increases switching costs through proprietary enrichment, and builds on the existing `trusted_event_ledger` architecture.

> **Implementation status:** This document includes roadmap concepts. The Signal Feed maps to live Starter/Pro/Business feed capabilities. The Intelligence Dossier, dossier API endpoints, dossier billing credits, and Intelligence tier are not implemented as self-serve products unless a later release note says otherwise.

> **Core thesis:** Competitors sell stale, broad datasets. No one owns the *velocity* layer — who just registered, what they look like before they are inspected, and whether they will survive. We do.

---

## 1. Product Tiers

### Tier 1: Signal Feed
**One-sentence value proposition:** *Know a new care provider exists before your competitor finishes their morning coffee.*

**What it is:** Real-time (sub-15-minute latency) alert stream of every newly CQC-registered care provider, delivered via API, webhook, CSV export, or weekly digest.

**Target persona:** High-volume sales teams (CareTech SaaS, medical suppliers, recruitment agencies, compliance consultants) who need **speed and volume** above all else.

**Feature set:**

| Feature | Detail | WTP Driver |
|---------|--------|------------|
| Real-time webhook | HMAC-signed `feed.new_registration` event to customer URL | RevOps teams want instant CRM ingestion |
| API feed endpoint | `GET /api/v1/feed/new-registrations` with filters | SDRs build automated outreach lists |
| Saved filters | Region, LA, service type, postcode prefix, provider type | Territory-based reps only want their patch |
| CSV/XLSX export | One-click, filter-respecting, email-delivered | Field sales teams live in spreadsheets |
| Weekly digest | Email summary of registrations matching a saved filter | Managers who don't want API noise |
| Slack/Teams notifier | Native integration (v1: webhook template, v2: native bot) | Sales teams live in chat |
| Historical backfill | All registrations from 1 Jan 2026 | Data science teams want training sets |

**Data fields (Signal Feed):**
- `name`, `slug`, `registration_date`, `status`
- `type` (e.g., Social Care Org, NHS Trust)
- `region`, `local_authority`, `town`, `county`, `postcode`
- `service_types`, `specialisms`
- `phone`, `website`
- `number_of_beds`
- `overall_rating` (if pre-existing — usually null for new regs)

**Delivery mechanism:** FastAPI feed endpoint + webhook delivery engine (already implemented). Extend with a dedicated "Signal Feed" dashboard card in Next.js frontend.

**Mapping to existing tiers:** Signal Feed is the **Starter** (£99/mo) through **Business** (£499/mo) tier. Webhooks require Business+.

---

### Tier 2: Intelligence Dossier
**One-sentence value proposition:** *Every new provider unpacked — who owns it, where they operate, who to call, and how risky they are before the CQC even knocks.*

**What it is:** An enriched, per-provider profile that fuses CQC data with third-party commercial and regulatory datasets. Sold as API credits, per-dossier lookups, or bundled into a higher subscription tier.

**Target persona:** Strategic sellers, BD leads, M&A advisors, compliance consultants, and property investors who need **depth and context** to prioritize a small set of high-value targets.

**Feature set:**

| Module | Data Points | Source | WTP Driver |
|--------|-------------|--------|------------|
| **Director DNA** | Director names, appointment dates, resignation history, other directorships, linked entities | Companies House API | Sellers want warm introductions via mutual connections |
| **Contact Surface** | Verified business email (pattern-matched + MX verified), publicly listed phone, LinkedIn URLs for directors | Companies House + website scrape + professional directory proxies | Outreach needs a human target, not a building |
| **Property Footprint** | Title register (freehold/leasehold), landlord identity, planning permission history, change-of-use applications | HM Land Registry (INSPIRE + Price Paid) + planning.data.gov.uk + local authority scrapers | Property investors and lenders assess asset backing |
| **Staff Velocity** | Estimated headcount from job postings, role types posted, posting velocity | Indeed API, Reed API, Adzuna API, company careers-page scrapers | Recruitment firms gauge hiring urgency; consultants gauge scale |
| **Capital Signals** | Recent charges/mortgages (CH), filing anomalies, news mentions of funding, acquisition tags | Companies House Filing History + GDELT/NewsAPI | Investors and lenders triage financial health |
| **Compliance Risk Score** | Pre-Inspection Risk Score (see §3) | Proprietary heuristic/ML | Compliance consultants sell remediation services; buyers avoid toxic assets |

**Data fields (Intelligence Dossier):**
All Signal Feed fields, plus:
- `directors[]` → `{name, appointment_date, resigned_date, other_directorships_count, linkedIn_url, email}`
- `property[]` → `{address, tenure_type, title_number, last_sale_date, last_sale_price, planning_refs[], landlord_name}`
- `staff_signals` → `{estimated_headcount_low, estimated_headcount_high, open_roles_count, top_role_types[], job_posting_velocity_30d}`
- `capital_signals` → `{latest_charge_date, charge_amount_gbp, funding_news_mentions_90d, filing_anomaly_count_12m}`
- `compliance_risk` → `{pre_inspection_risk_score, risk_tier, primary_risk_factors[]}`

**Delivery mechanisms:**
- API: `GET /api/v1/dossier/{provider_id}` — returns full JSON dossier
- Bulk: `POST /api/v1/dossier/bulk` — async job, S3/CSV delivery
- Dashboard: Expandable provider card in Next.js with "Dossier" tab
- Webhook enrichment: Business+ webhooks optionally include dossier snapshot

**Mapping to existing tiers:** New **"Intelligence"** tier at **£899/mo** (between Business and Enterprise), or per-dossier credits at **£2.50/dossier** for lower-volume users. Bundled into Enterprise.

---

### Tier 3: Strategic Analytics
**One-sentence value proposition:** *See the care market like an institutional investor sees it — maps, forecasts, and a survival index no one else has.*

**What it is:** Aggregated market intelligence, predictive indices, and white-label research outputs built on top of the full enriched dataset.

**Target persona:** Institutional investors (care home PE, REITs), local authority commissioners, corporate strategy teams (large care groups, insurers), and industry analysts.

**Feature set:**

| Feature | Detail | WTP Driver |
|---------|--------|------------|
| **New Provider Market Map** | Interactive map (or embeddable widget) of all new registrations by LA, service type, and survival probability | LAs need to spot market gaps; investors spot saturation |
| **Trend Forecasts** | 12-month forward projections of registration volume by region and service type | Corporate strategy teams plan market entry |
| **White-Label Reports** | Branded PDF/HTML reports on new-provider activity in a region or sector | Consultants and LAs present to stakeholders |
| **New Provider Survival Index** | Predicted 12-month survival probability for each new registration (see §3) | Investors price risk; LAs predict market failure |
| **Competitive Entry Alerts** | Flag when a known competitor group registers a new location | Corporate BD monitors competitive expansion |
| **Custom Data Room** | Bespoke dataset export (BigQuery/CSV/Snowflake) for enterprise clients | PE firms want raw data in their own warehouse |

**Delivery mechanisms:**
- Dashboard: Dedicated `/dashboard/analytics` route in Next.js (or separate Streamlit/Metabase instance for v1)
- API: `GET /api/v1/analytics/market-map`, `GET /api/v1/analytics/survival-index`
- Reports: Async PDF generation (WeasyPrint or headless Chrome) + S3 delivery
- Embed: White-label iframe or JS widget for market maps

**Mapping to existing tiers:** Enterprise tier (£custom) with minimum **£2,500/mo** commitment, or **£5,000-£15,000 per bespoke report**.

---

## 2. Enrichment Pipeline

### 2.1 Data Sources

| Source | Data Acquired | Defensibility | Cost | Complexity | Speed to Market |
|--------|--------------|---------------|------|------------|-----------------|
| **CQC Public API** | Base provider registry, locations, ratings | — Free public data; our edge is velocity + packaging | Free | Low | ✅ Shipped |
| **Companies House API** | Officers, filing history, charges, PSCs, insolvency | Hard to replicate legally; official gov source | £0.02-£0.10 per document (API streaming); bulk XML free | Medium | ✅ 30 days |
| **HM Land Registry** | Title register, price paid, INSPIRE polygons | Expensive/complex to access at scale; creates moat | £3/title (NLIS), £0.30/transaction (Price Paid), INSPIRE free | High | ⚠️ 60 days |
| **Planning.data.gov.uk** + LAs | Planning applications, change-of-use, building control | Fragmented; building scrapers for 300+ LAs is work | Free | High | ⚠️ 60 days |
| **Job Boards (Indeed, Reed, Adzuna)** | Open roles, posting dates, estimated headcount | Proxy for scale and growth velocity | Indeed: £0.10-£0.30/query; Reed/Adzuna: variable | Medium | ✅ 30 days |
| **News/APIs (GDELT, NewsAPI, Google Alerts RSS)** | Funding, M&A, litigation, insolvency mentions | Signals that appear here before they appear in CH | NewsAPI: $449/mo; GDELT: free (BigQuery) | Low-Medium | ✅ 30 days |
| **OpenCorporates / DueDil** | Ultimate beneficial ownership, global corporate graph | Faster than manually tracing CH links | DueDil: £££ enterprise; OpenCorporates: API credits | Low | ✅ 30 days |
| **LinkedIn** (official Sales Navigator API or legally sourced proxies) | Director profiles, career history, mutual connections | High value but legally constrained | LinkedIn API: restricted; proxies: legal risk | High | 🔴 90+ days |
| **Orbis / Experian / Creditsafe** | Credit scores, payment behaviour, group structures | Very high defensibility; very high cost | £5-£50 per lookup | Low (if purchased) | 🔴 90+ days |
| **ONS / NHS Digital** | Population projections, deprivation indices, bed demand | Public data; our edge is fusion with CQC | Free | Low | ✅ 30 days |

### 2.2 How Each Source Adds Defensibility

1. **Companies House fusion:** Most competitors have CH data. Few fuse it *at the moment of CQC registration* (before the provider has a website or phone listing). The "director DNA" module lets us flag repeat founders, serial operators, and disqualified-adjacent directors in <24 hours.

2. **Property + Planning fusion:** Land Registry + planning data tells us if a new care home is freehold (asset-backed, lower risk) or leasehold with a change-of-use pending (higher regulatory risk). This is expensive to build but impossible to reverse-engineer from public CQC data alone.

3. **Job board velocity:** Staffing is the #1 operational signal in care. A provider posting 15 nurse roles in 30 days is either scaling fast or bleeding staff. Either way, it is a buying signal for recruitment firms and a risk signal for investors. Job board APIs are rate-limited and geographically fragmented; maintaining feeders is operational work that deters copycats.

4. **News sentiment:** Funding news often hits press 30–90 days before it appears in CH filings. Capturing this creates an alpha signal for investors and M&A advisors.

5. **Proprietary scores (§3):** Even if a competitor assembles the same raw sources, the *model* that turns 40 features into a Pre-Inspection Risk Score is a trade secret that improves with every inspection outcome we observe.

### 2.3 Legal & Compliance Notes

- **GDPR:** Dossier emails must be business addresses derived from pattern matching or public filings, not harvested from private consumer databases. Provide opt-out and data-deletion workflows.
- **CH API:** Compliant by design (public register).
- **Land Registry:** Must route through licensed NLIS provider or use open data (INSPIRE, Price Paid) only. Title register lookups require licensed access.
- **LinkedIn:** Do not scrape without contractual right. v1 uses Companies House + public website data only. v2 negotiates official API access or buys from compliant enrichment vendor (e.g., Cognism, Lusha with UK TPS filtering).
- **Job boards:** Use official APIs only; respect robots.txt and rate limits.

---

## 3. Proprietary Analytics

### 3.1 Pre-Inspection Risk Score (PIRS)

**Business question:** *Which newly registered providers are most likely to receive an "Inadequate" or "Requires Improvement" rating at their first inspection?*

**Why buyers pay:** Compliance consultants use this to pre-sell remediation services. Investors use it to avoid write-downs. LAs use it to triage oversight resources.

**Methodology — v1 Heuristic (30-day ship):**

| Feature Category | Feature | Weight | Source |
|------------------|---------|--------|--------|
| Structural | Service type = "Domiciliary care agency" | +15 | CQC |
| Structural | Service type = "Nursing home" | +5 | CQC |
| Structural | Number of beds > 60 | +10 | CQC |
| Ownership | First-time director (0 previous care directorships) | +20 | CH |
| Ownership | Director has resigned from >2 care providers in 3 years | +25 | CH |
| Ownership | Overseas/unknown PSC | +15 | CH |
| Property | Leasehold + no planning permission found | +15 | Planning/LR |
| Property | Freehold + recent purchase | −10 | LR |
| Velocity | Registration date < 30 days after CH incorporation | +20 | CQC + CH |
| Velocity | >5 job postings in first 30 days (urgent hiring = understaffed) | +15 | Job boards |
| Geography | LA with >20% of providers rated RI/Inadequate | +10 | CQC |
| Group | Part of a group with existing RI/Inadequate locations | +20 | CQC |

- Score range: 0–100
- Tiers: **Low (0-30)**, **Moderate (31-60)**, **High (61-80)**, **Critical (81-100)**
- Update frequency: Recalculated on every enrichment cycle; major model updates monthly

**Methodology — v2 ML (90-day ship):**
- Train a gradient-boosted classifier (LightGBM/XGBoost) on historical first-inspection outcomes.
- Features: all v1 features + embedding of provider name (catches shell-company naming patterns) + CH filing text embeddings.
- Target: first published overall rating (binary: "Good/Outstanding" vs "RI/Inadequate").
- Validation: temporal split (train on pre-2024, validate on 2024-2025).
- Performance target: AUC-ROC ≥ 0.75 (better than random; good enough for prioritization).

**Data feedback loop:** Every time a provider in our training set gets its first inspection, the pipeline ingests the outcome and retrains the model weekly.

---

### 3.2 First 90 Days Survival Index (FDSI)

**Business question:** *Which new providers will deregister, change ownership, or go dormant within 12 months of registration?*

**Why buyers pay:** Investors price deals. LAs plan market capacity. Corporate strategy teams model competitive landscape churn.

**Methodology — v1 Heuristic (60-day ship):**

| Feature | Direction | Rationale |
|---------|-----------|-----------|
| Director has no prior care sector experience | + | Naive entrants fail faster |
| Registered as dormant or non-trading in CH within 90 days | +++ | Strong death signal |
| Zero job postings in first 90 days | ++ | No hiring = no revenue = no operations |
| Leasehold with <5 years remaining | + | Lease break risk |
| LA with >3 provider deregistrations in prior 12 months | + | Market stress |
| Part of a group with >20% deregistration rate | ++ | Group-level operational failure |
| Rapid registration (<14 days CH→CQC) | + | Rushed setup, often undercapitalised |
| No website or placeholder website at 90 days | + | Lack of commercial seriousness |

- Score: probability 0.0–1.0
- Buckets: **Survivor (<0.25)**, **At Risk (0.25–0.50)**, **Vulnerable (0.50–0.75)**, **Likely Fail (>0.75)**

**Methodology — v2 ML (90-day ship):**
- Cox proportional hazards model or survival random forest.
- Target: time-to-deregistration or change-of-control event (censored at 12 months if still active).
- Features: all enrichment features + macroeconomic indices (local unemployment, care worker wage inflation from ONS).
- Output: 3-month, 6-month, 12-month survival probability per provider.

---

## 4. Buyer Personas & Willingness-to-Pay Validation

| Persona | Tier | Job-to-be-done | WTP Evidence |
|---------|------|----------------|--------------|
| **SDR / BDR** (CareTech vendor) | Signal Feed | Fill pipeline with net-new accounts before competitors | LinkedIn Sales Navigator is £80/seat/mo; they will pay £99-199 for territory-filtered leads |
| **VP Sales** (medical supply) | Signal Feed + Dossier credits | Prioritize 50 high-intent accounts from 500 new regs | Willing to pay £2-5 per enriched lead; £899/mo for team access |
| **M&A Advisor** (care home broker) | Dossier | Pre-qualify targets: asset backing, director quality, compliance risk | Success fees are 1-3% of transaction; £899-2,500/mo is negligible vs one avoided bad deal |
| **Compliance Consultant** | Dossier | Proactively contact high-risk new providers before CQC does | Day rates are £800-1,500; one retained client per month justifies £899/mo |
| **LA Commissioner** | Strategic Analytics | Market oversight, predict failure, justify capital grants | Budget holders for £10k-£50k research contracts; annual subscriptions feasible |
| **PE Associate** (social care fund) | Strategic Analytics | Market maps, deal origination, portfolio risk monitoring | Data room budgets are £20k-£100k per deal; £5k/mo for persistent intelligence is standard |

---

## 5. Speed-to-Market Roadmap

### Days 0–30: Tier 1 Hardening + Tier 2 MVP Launch

**Goal:** Ship Tier 1 as a standalone SKU with 99.9% webhook reliability. Launch Tier 2 with Companies House enrichment only.

| Week | Deliverable |
|------|-------------|
| 1 | Add `dossier` table schema; build Companies House enrichment worker (`tools/enrich_ch.py`) |
| 2 | Add `pre_inspection_risk_score` column; ship v1 heuristic PIRS; expose on API |
| 3 | Build bulk dossier endpoint (`POST /api/v1/dossier/bulk`); add Dossier tab to Next.js provider page |
| 4 | Marketing page for "Signal Feed" + "Intelligence Dossier"; launch Intelligence tier in Stripe |

**Tier 2 MVP scope (30-day):**
- Director DNA (Companies House only)
- Capital signals (CH charges + basic news search)
- PIRS v1 heuristic
- No Land Registry, no job boards yet

### Days 31–60: Tier 2 Depth + Tier 3 Alpha

**Goal:** Make Dossier truly defensible with property and staffing signals. Launch internal alpha of Survival Index.

| Week | Deliverable |
|------|-------------|
| 5 | Land Registry INSPIRE + Price Paid ingestion; property tenure module |
| 6 | Planning.data.gov.uk scraper + 5 high-volume LA scrapers; planning permission module |
| 7 | Job board API feeders (Indeed + Reed); staff velocity module |
| 8 | FDSI v1 heuristic; internal dashboard for Survival Index; invite 3 Enterprise beta customers |

### Days 61–90: Tier 3 Launch + Model Maturation

**Goal:** Ship Strategic Analytics as a white-glove Enterprise product. Upgrade PIRS to ML.

| Week | Deliverable |
|------|-------------|
| 9 | Market map API + embeddable widget; regional trend forecasts |
| 10 | White-label report generator (HTML → PDF); first paid bespoke report |
| 11 | PIRS v2 LightGBM model in production (shadow mode, then live) |
| 12 | Case studies + pricing page for all three tiers; first Enterprise contract |

---

## 6. Data Schema Additions (Summary)

### New tables

```sql
-- Enrichment cache (one row per provider, updated incrementally)
CREATE TABLE provider_enrichment (
  provider_id VARCHAR(20) PRIMARY KEY REFERENCES care_providers(id),
  ch_company_number VARCHAR(8),
  ch_status VARCHAR(50),
  ch_incorporation_date DATE,
  directors JSONB DEFAULT '[]',
  charges JSONB DEFAULT '[]',
  pscs JSONB DEFAULT '[]',
  property_tenure VARCHAR(20), -- freehold / leasehold / unknown
  property_landlord VARCHAR(255),
  planning_refs JSONB DEFAULT '[]',
  estimated_staff_low INT,
  estimated_staff_high INT,
  open_roles_count INT,
  job_posting_velocity_30d INT,
  funding_news_mentions INT,
  filing_anomaly_count INT,
  pre_inspection_risk_score INT,
  pre_inspection_risk_tier VARCHAR(20),
  survival_index_12m DECIMAL(3,2),
  survival_bucket VARCHAR(20),
  enriched_at TIMESTAMP,
  next_enrichment_at TIMESTAMP,
  source_versions JSONB DEFAULT '{}' -- which pipeline versions produced this row
);

-- Dossier audit log (who queried what, for compliance)
CREATE TABLE dossier_access_log (
  id SERIAL PRIMARY KEY,
  api_key_id INT REFERENCES api_keys(id),
  provider_id VARCHAR(20) REFERENCES care_providers(id),
  accessed_at TIMESTAMP DEFAULT NOW(),
  fields_requested TEXT[],
  delivery_mode VARCHAR(20) -- api, bulk, webhook
);

-- Enrichment pipeline job queue
CREATE TABLE enrichment_jobs (
  id SERIAL PRIMARY KEY,
  provider_id VARCHAR(20),
  job_type VARCHAR(50), -- ch_lookup, lr_lookup, planning_lookup, jobs_lookup
  status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
  payload JSONB,
  result JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  error_message TEXT
);
```

---

## 7. Success Metrics (30-60-90)

| Metric | 30-day target | 60-day target | 90-day target |
|--------|--------------|---------------|---------------|
| Signal Feed MRR | £3,000 | £6,000 | £10,000 |
| Dossier lookups / month | 500 | 3,000 | 8,000 |
| Intelligence tier customers | 2 | 8 | 20 |
| Enterprise (Strategic Analytics) customers | 0 | 1 (pilot) | 3 |
| PIRS accuracy (vs actual inspections) | N/A (heuristic) | 60% top-decile catch | 75% AUC-ROC |
| Enrichment coverage (% of new regs) | 80% CH | 60% property + 70% jobs | 90% all sources |
