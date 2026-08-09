# CareGist Pricing & Unit Economics

> **Implementation status:** Dossier credits, the Intelligence tier, and strategic report/data-room products in this document are roadmap economics, not live self-serve entitlements. The current live subscription ladder is Free, Alerts Pro, Data Starter, Data Pro, Data Business, and Enterprise/custom.

## 1. Pricing Architecture

### 1.1 Subscription Tiers (Recurring Revenue)

CareGist will operate a **good-better-best** staircase with a usage-based overlay for Tier 2 enrichment.

| Tier | Monthly Price | Annual Price (2 mo free) | Best For | Tier 1 | Tier 2 | Tier 3 |
|------|--------------|--------------------------|----------|--------|--------|--------|
| **Free** | £0 | £0 | Evaluation | 10 rows, view-only | — | — |
| **Starter** | £99 | £990 | Solo SDR / founder | 25 rows, CSV, 3 filters | — | — |
| **Pro** | £199 | £1,990 | Small sales team (3 seats) | 50 rows, 20 filters | — | — |
| **Business** | £499 | £4,990 | High-volume ops (10 seats) | 100 rows, 100 filters, webhooks | 50 dossier credits/mo | — |
| **Intelligence** | £899 | £8,990 | Strategic sellers / consultants | 250 rows, 500 filters, webhooks | 200 dossier credits/mo + bulk API | — |
| **Enterprise** | £2,500+ | £25,000+ | Investors, LAs, corporates | Unlimited feed + webhooks | 1,000 dossier credits/mo | Market maps, white-label reports, custom data room |

**Seat add-ons:** £15/seat/mo on Pro+, £25/seat/mo on Intelligence+.

**Annual discount:** 17% (2 months free) to improve cash flow and reduce churn.

### 1.2 Per-Lead / Per-Dossier Pricing (Usage Overlay)

For customers who do not want a full Intelligence tier subscription, or who exceed bundled credits:

| Product | Price | Minimum | Notes |
|---------|-------|---------|-------|
| **Signal Feed — per lead** | £0.50 | 100-pack (£50) | One-time CSV export of historical new registrations; no ongoing sub required |
| **Dossier — per lookup** | £2.50 | 10-pack (£25) | API or dashboard single-provider enrichment; credits expire in 12 months |
| **Dossier — bulk export** | £1.75 | 500-pack (£875) | Async bulk job; discounted for volume |
| **Strategic Report — bespoke** | £5,000–£15,000 | 1 | White-label PDF/HTML on a region or sector; 5-day SLA |
| **Data Room — one-off** | £2,500 | 1 | Full enriched dataset snapshot (CSV/Parquet) delivered via S3 |

**Buyer psychology:** The £2.50/dossier price anchors against the £800-1,500 day rate of a compliance consultant doing manual research. A dossier that saves 2 hours of manual CH + LR + job board lookup is worth £50-100 to the buyer. At £2.50, it is a no-brainer.

### 1.3 Enterprise Licensing

Enterprise deals are **custom** and priced on three axes:

1. **Data volume:** Number of dossier lookups per month, feed event volume, number of API seats.
2. **Delivery mode:** API-only vs white-label dashboard vs embedded market map widget.
3. **Exclusivity / SLAs:** Dedicated webhook endpoint, <5-min latency SLA, quarterly strategy calls, custom model training.

**Enterprise price bands:**

| Segment | Monthly Fee | Typical Inclusions |
|---------|-------------|-------------------|
| **Emerging Enterprise** (small PE, mid-size care group) | £2,500–£4,000 | 1,000 dossiers, 10 seats, market maps, monthly trend report |
| **Core Enterprise** (large care group, LA consortium) | £5,000–£10,000 | 5,000 dossiers, 25 seats, white-label reports, custom data room, 99.9% uptime SLA |
| **Strategic Partner** (national insurer, REIT, top-10 PE) | £10,000–£25,000 | Unlimited dossiers, unlimited seats, API whitelisting, bespoke survival model per portfolio, quarterly board briefings |

---

## 2. Worked Example: Unit Economics

### Scenario: Month 6 of commercial operation

**Assumptions:**

| Assumption | Value | Rationale |
|------------|-------|-----------|
| Customer mix | 40 Starter, 20 Pro, 10 Business, 5 Intelligence, 2 Enterprise | Conservative funnel based on current free-tier signups |
| Average revenue per tier (blended monthly) | Starter £99, Pro £199, Business £499, Intelligence £899, Enterprise £4,000 | No annual contracts yet; all monthly |
| Attach rate — dossier overage | 30% of Business+ customers buy extra credits | Observed in beta |
| Average overage spend | £150/mo | ~60 extra dossiers at £2.50 |
| Attach rate — bespoke reports | 1 report per quarter per Enterprise customer | £7,500 average |
| Gross churn (monthly) | 5% | Typical for B2B data products in year 1 |
| Net revenue retention | 110% | Expansion via overage + upsell |

### Revenue Build

```
Tier 1 (Signal Feed subscriptions):
  Starter:   40 × £99   = £3,960
  Pro:       20 × £199  = £3,980
  Business:  10 × £499  = £4,990
  ─────────────────────────────────
  Tier 1 MRR                           = £12,930

Tier 2 (Intelligence Dossier):
  Intelligence subs:   5 × £899   = £4,495
  Dossier overage:     15 × £150  = £2,250   (30% of 50 Business+ customers)
  One-off bulk packs:  ~£1,000/mo (estimated)
  ─────────────────────────────────
  Tier 2 MRR                           = £7,745

Tier 3 (Strategic Analytics):
  Enterprise subs:     2 × £4,000 = £8,000
  Bespoke reports:     2 × £2,500 = £5,000   (2 Enterprise × 1 report/qtr prorated)
  ─────────────────────────────────
  Tier 3 MRR                           = £13,000

─────────────────────────────────
TOTAL MRR                              = £33,675
ARR run-rate                           = £404,100
```

### Cost Build

| Cost Category | Monthly | % of Revenue | Notes |
|---------------|---------|--------------|-------|
| **Data acquisition** | £3,200 | 9.5% | CH API (£200), Indeed/Reed/Adzuna (£800), NewsAPI (£400), Land Registry bulk (£300), Orbis trial (£500), proxy/infra for scrapers (£1,000) |
| **Cloud infra** | £1,800 | 5.3% | EC2 (c6g.2xlarge), RDS (db.r6g.large), S3, Resend, Sentry |
| **Stripe + payment** | £1,010 | 3.0% | 1.5% + 20p on blended average transaction (~£340) + £670 subscription billing |
| **Sales & marketing** | £8,000 | 23.8% | 1 founder-seller + paid LinkedIn/AdWords (£3,000) + content (£1,000) + events (£1,000) |
| **Engineering** | £12,000 | 35.6% | 2 engineers (founders) at opportunity cost; not cash cost yet |
| **Legal / compliance** | £500 | 1.5% | GDPR counsel, CH API terms review |
| **Admin / misc** | £500 | 1.5% | Accounting, tools, travel |
| **Total cash costs** | £15,010 | 44.6% | Excluding founder-engineering opportunity cost |
| **Total loaded costs** | £27,010 | 80.2% | Including founder-engineering at market rate |

### Unit Economics Summary

| Metric | Value | Benchmark / Target |
|--------|-------|-------------------|
| **Gross Margin** | £30,475 / £33,675 = **90.5%** | >80% is excellent for data/software |
| **Gross Margin (after data acquisition)** | £27,275 / £33,675 = **81.0%** | >75% target for data products |
| **LTV** | £899 × 18 months × 110% NRR × 75% GM = **£13,300** | Blended; higher for Enterprise |
| **CAC** | £8,000 S&M / 8 new customers = **£1,000** | Target <£1,500 for mid-market B2B |
| **LTV:CAC** | **13.3:1** | >3:1 is healthy; >5:1 is best-in-class |
| **Months to recover CAC** | £1,000 / (£33,675 × 81% / 77 customers) = **2.8 months** | Target <12 months |
| **Payback period (cash)** | **<3 months** | Excellent |

**Narrative:** At Month 6, CareGist is a high-gross-margin data business with a 3-month CAC payback. The primary cost lever is data acquisition (9.5% of revenue), which *decreases* as a percentage of revenue as we scale because CH and job board APIs have volume tiers. The single biggest margin risk is Land Registry / Orbis costs at scale; we hedge this by starting with open data (INSPIRE, Price Paid) and only paying for title registers on high-value Enterprise dossiers.

---

## 3. Pricing Strategy Notes

### 3.1 Anchoring & Packaging

- **Free tier:** Generous enough to build habit (10 feed rows), but too small to run a workflow. Conversion hook is CSV export.
- **Starter vs Pro:** Pro is 2× price for 2× feed rows + 7× filters + team seats. The jump is designed to capture the "I need to share this with my manager" moment.
- **Business vs Intelligence:** Intelligence unlocks the dossier. The £400 gap (£499→£899) is justified by a single dossier-led deal: one £2.50 dossier that helps close a £10,000 contract pays for 160 months of the upgrade.
- **Enterprise floor:** £2,500/mo is high enough to force a conversation with a budget holder, low enough that a single LA or PE analyst can sign off without a board paper.

### 3.2 Expansion Levers

1. **Seat expansion:** Team functionality is gated behind Pro+. As one user succeeds, they invite colleagues.
2. **Credit overage:** Bundled dossier credits are set at ~60% of expected usage for power users, creating natural expansion revenue.
3. **Tier upsell:** Signal Feed users who hit 100 rows/month are nudged to Business. Dossier users who buy >100 credits are nudged to Intelligence.
4. **Report upsell:** Enterprise customers naturally want bespoke analysis; £5k-£15k reports are high-margin (mostly automated + 1 day of analyst time).

### 3.3 Discounting Policy

- No discounts below Enterprise.
- Enterprise: maximum 15% annual prepay discount + 10% multi-year discount (non-cumulative).
- Non-profits (charity care providers, NHS trusts): 50% discount on data consumer tiers only; no discount on dossier credits or reports.
- Never discount dossier credits below £1.50; this protects perceived value.

---

## 4. Financial Projections (12-Month Model)

| Month | New Customers | Churned | Ending Customers | MRR | Data Costs | Gross Profit | Cumulative Gross Profit |
|-------|--------------|---------|------------------|-----|------------|--------------|------------------------|
| 1 | 2 | 0 | 2 | £598 | £800 | -£202 | -£202 |
| 2 | 4 | 0 | 6 | £2,394 | £1,000 | £1,394 | £1,192 |
| 3 | 6 | 0 | 12 | £5,388 | £1,200 | £4,188 | £5,380 |
| 4 | 8 | 1 | 19 | £9,482 | £1,500 | £7,982 | £13,362 |
| 5 | 10 | 1 | 28 | £14,776 | £2,000 | £12,776 | £26,138 |
| 6 | 12 | 1 | 39 | £22,270 | £2,500 | £19,770 | £45,908 |
| 7 | 14 | 2 | 51 | £31,964 | £3,000 | £28,964 | £74,872 |
| 8 | 16 | 2 | 65 | £43,958 | £3,500 | £40,458 | £115,330 |
| 9 | 18 | 3 | 80 | £58,352 | £4,000 | £54,352 | £169,682 |
| 10 | 20 | 3 | 97 | £75,246 | £4,500 | £70,746 | £240,428 |
| 11 | 22 | 4 | 115 | £94,740 | £5,000 | £89,740 | £330,168 |
| 12 | 24 | 5 | 134 | £117,034 | £5,500 | £111,534 | £441,702 |

**Assumptions in model:**
- Average new customer brings £450 MRR (blended across tiers, weighted to Starter/Pro early, shifting to Business/Intelligence later).
- Churn begins Month 4 at 5% of base.
- Data costs scale sub-linearly (volume discounts, caching, deduplication).
- By Month 12: ~£1.4M ARR run-rate, 81% gross margin after data costs.
