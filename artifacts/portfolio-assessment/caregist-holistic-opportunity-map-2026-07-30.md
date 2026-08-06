# CareGist Holistic Market and Portfolio Opportunity Map

**Scope:** UK/England CareGist, read-only evidence review across the active-provider stock, change-event history, and the current 90-day new-registration surface.

## DELIVERABLE RETURN

- **What was produced:** Evidence-led market and portfolio map, priority order, launch wedges, revenue scenarios, assumptions, weaknesses, and compliance flags.
- **Evidence used:**
  - `artifacts/portfolio-assessment/caregist-holistic-opportunity-task-brief-2026-07-30.md`
  - `product_specification.md`
  - `buyer_personas.md`
  - `frontend/app/page.tsx`
  - `frontend/lib/directory-db.ts`
  - `pricing-snapshot.md`
  - `api-landing-snapshot.md`
  - `lead-list-snapshot.md`
  - `docs/investor-report.md`
  - `docs/event-intelligence/discovery.md`
  - `docs/event-intelligence/discovery-manifest.json`
- **Assumptions made:**
  - Counts in the brief are treated as the current authenticated evidence unless a source file explicitly contradicted them.
  - The 91-provider `new_90` snapshot is treated as a captured list size, not the full annual flow.
  - Buyer-persona willingness-to-pay figures are hypotheses, not validated demand.
  - No source pack provides paid-customer proof, so no product is marked commercially validated.
- **Known weaknesses / open questions:**
  - No verified UK Country Pack was found.
  - Stock counts drift: investor report segments sum to 55,818 active providers, while the live discovery manifest records 56,743 `care_providers` rows.
  - The 90-day list count (91) does not reconcile cleanly to the 340/month marketing copy without a deeper filter/scope check.
  - No evidence of conversion, retention, churn, or collected revenue in the packet.
- **Compliance flags:**
  - UK GDPR / PECR / profiling / automated decisioning risk if event data is turned into outreach lists or risk scores.
  - No unsupported CQC endorsement claims.
  - Land Registry, LinkedIn, and job-board enrichment are constrained by source/license terms.
  - VAT/pricing status remains unverified.
- **Ready for QA:** yes

---

## Executive summary

CareGist has a real and defensible **event-led intelligence wedge**, but the evidence does **not** support treating the whole active-provider base as one homogeneous market, nor does it support claiming commercial validation from internal WTP statements.

The market breaks into three distinct layers:

1. **Current provider stock** — the full active-provider base that can be searched, segmented, monitored, and mapped.
2. **Change events** — rating changes, stale inspections, not-yet-inspected status, and related monitoring signals on that stock.
3. **New registrations** — the small, fast-moving prospecting wedge that drives immediate sales ROI.

### Key evidence points

- The investor report segments the active market at **55,818 providers**:
  - Homecare 14,240
  - Dentists 12,004
  - Residential homes 10,309
  - Doctors/GPs 9,367
  - Supported living 4,727
  - Nursing homes 4,386
  - Other 785
- The live discovery manifest records **56,743 care_providers** rows and **56,742 trusted_event_ledger** rows, which means CareGist has both a large stock model and a large event-history moat.
- The current `/search?opportunity=new_90` view in the brief showed **91 providers** — a prospecting slice, not the whole market.
- The live surfaces in code and snapshots already include:
  - new registrations
  - Inadequate / Requires Improvement / Not Yet Inspected / stale inspection views
  - monitoring and alerts
  - CSV exports
  - API and webhooks
  - lead-list request flows
  - provider visibility / claims / pricing

### Bottom line

**Continue** the live event-driven intelligence business, **pivot** the story away from a generic directory and toward workflow-triggering market movement, and **stop** treating unvalidated internal WTP and predictive-risk claims as if they were market proof.

---

## Market structure: stock vs events vs new registrations

| Layer | What it is | Evidence | Commercial meaning |
|---|---|---:|---|
| **Stock** | All active CQC providers | 55,818 segmented active providers in the investor report; 56,743 care_providers rows in discovery manifest | Broad directory, segmentation, monitoring, market map |
| **Change events** | Ratings / inspection movement on active providers | Live code exposes Inadequate, Requires Improvement, Not Yet Inspected, stale inspection, monitoring, rating-change workflows | Retention, alerts, remediation, oversight, and recurring usage |
| **New registrations** | Fresh provider entries / early-market opportunities | 56,742 ledger events in brief; 91-provider current `new_90` capture; 340/month copy on live pages | Highest urgency prospecting wedge for suppliers, recruiters, and setup services |

### Active-provider stock mix

Using the 55,818 segmented active-provider total:

- Homecare: **25.51%**
- Dentists: **21.51%**
- Residential homes: **18.47%**
- Doctors/GPs: **16.78%**
- Supported living: **8.47%**
- Nursing homes: **7.86%**
- Other: **1.41%**

The top four categories make up **82.27%** of active stock, so they matter for coverage. But the **commercial fit** is not uniform: the best near-term buying motives are still tied to **new registrations, change events, staffing urgency, compliance risk, and market mapping**.

---

## Opportunity matrix

| Priority | Market / product opportunity | Primary buyer / problem | Status in evidence | Monetization role | Kill test |
|---:|---|---|---|---|---|
| 1 | **New registrations feed + lead lists** | Equipment suppliers, recruiters, policy/setup services need the earliest possible contact window | **Live and priced** via Search, Lead List, API, CSV/export, feeds | Core wedge; fastest ROI | Kill if target accounts do not convert from the new-registration workflow after repeated outreach and trials |
| 2 | **Monitoring / rating-change / stale-inspection / not-yet-inspected alerts** | Compliance consultants, turnaround firms, insurers, internal market-shaping teams need repeat signal | **Live and priced** via Alerts Pro, monitoring, saved watchlists, weekly digests | Retention engine and upsell layer | Kill if watchlist usage stays one-off and does not justify recurring subscription value |
| 3 | **API + webhooks + CRM push** | Software teams and ops teams want events inside their own systems | **Live and priced** via Data Business / API landing copy | Delivery layer; raises switching costs | Kill if teams will not integrate or only want manual CSV exports |
| 4 | **Public directory search + CSV exports** | Researchers and sales teams need a filtered provider list now | **Live**; public directory + filtered export routes | Acquisition funnel and low-friction entry product | Kill if it is only used as a free lookup tool with no upgrade path |
| 5 | **Provider visibility / claims / sponsored listing** | Providers want control of how they appear to families/partners | **Live** on pricing page | Secondary supply-side monetization; useful for SEO/trust, not the main engine | Kill if it distracts from demand-side intelligence economics |
| 6 | **Enriched dossier** (Companies House, property, jobs, news, risk factors) | Lenders, investors, M&A advisors, compliance consultancies want context and prioritisation | **Coded-but-unverified / roadmap** in the product spec | Higher-ACV upsell if data rights and cost structure work | Kill if source licensing, cost, or compliance blocks are too heavy for the margin model |
| 7 | **PIRS / survival index / market-map analytics** | Institutional investors, LAs, ICBs want market-level direction and triage | **Roadmap-only** in product spec; no live proof in packet | Enterprise / white-label future state | Kill if buyers will not pay for it without bespoke service and human support |
| 8 | **White-label reports / custom data rooms** | Enterprise buyers want a packaged answer, not raw data | **Roadmap-only** (spec’d, not validated) | Service-led enterprise revenue path | Kill if procurement cycles and compliance overhead swamp the margin |

### Interpretation

- **Live now:** new registrations, monitoring, exports, API/webhooks, provider search, provider visibility.
- **Worth building next:** dossiers if source access and compliance are controllable.
- **Do not lead with yet:** predictive survival / market-map analytics as software-first products; they need validation and governance.

---

## Full-market niches and what to do with the wider base

### 1) Homecare, residential homes, and nursing homes
These are the most obviously care-specific and operationally urgent niches.

- **Best use:** new-registration prospecting, compliance monitoring, staffing urgency, and property/risk enrichment.
- **Why:** high operational complexity, visible staffing pressure, and strong need for early contact.
- **What to do with the wider base:** keep them in segmentation and monitoring, not just outbound lists.

### 2) Dentists and GPs
These categories materially widen the active-provider base, but they are not the cleanest first wedge for the current care-sector workflow.

- **Best use:** broad directory coverage, market mapping, and long-tail dataset value.
- **Commercial caution:** messaging built for care-home vendors does not automatically transfer.
- **What to do with the wider base:** retain as coverage and map depth; do not force them into the same sales narrative as care-home registrations.

### 3) Supported living
Strong fit for staffing, compliance, and market-shaping use cases.

- **Best use:** monitoring, risk triage, and recruitment.
- **What to do with the wider base:** route to monitoring and lead-list workflows rather than generic search.

### 4) Cross-market stock layer
The entire stock should power:

- search and comparison
- segmentation
- lead lists
- monitoring and alerts
- market maps
- customer retention

**Do not** try to sell the entire active-provider base as one monolithic subscription. Use it as the data substrate, then route by job-to-be-done.

---

## Launch wedges: no more than 3

### Wedge 1 — New registrations feed for suppliers and recruiters
**Why first:** fastest ROI, clearest timing advantage, easiest to explain.

- Buyers: equipment suppliers, recruiters, policy/setup providers
- Product: feed + CSV/export + saved filters + webhook/API path
- Evidence: live pages already position the core product around new registrations and workflow delivery
- Success condition: recurring usage and upgrade from free / basic lookup to paid feed access

### Wedge 2 — Monitoring and at-risk provider workflows
**Why second:** turns the stock base into recurring value.

- Buyers: compliance consultants, turnaround firms, insurers, market-shaping teams
- Product: watchlists, rating-change alerts, not-yet-inspected, stale-inspection, weekly digests
- Evidence: live pricing and search pages already expose Alerts Pro and monitor counts
- Success condition: watchlists used as a workflow, not a curiosity

### Wedge 3 — Enterprise analytics / white-label reports
**Why third:** highest ACV, but longest sales cycle and highest compliance burden.

- Buyers: investors, lenders, LAs, ICBs
- Product: market maps, white-label reports, dossiers, data rooms
- Evidence: mostly roadmap/spec only; no paid validation in packet
- Success condition: one or more paid pilots that justify the service/compliance overhead

---

## Revenue scenario arithmetic

These are **illustrative** only, using the live pricing page. They are not demand proof.

| Scenario | Assumed mix | Monthly recurring revenue | Annualised run-rate |
|---|---|---:|---:|
| Downside | 15 Data Starter, 5 Data Pro, 1 Data Business, 10 Alerts Pro | £3,469 | £41,628 |
| Base | 30 Data Starter, 10 Data Pro, 3 Data Business, 20 Alerts Pro | £7,437 | £89,244 |
| Upside | 60 Data Starter, 20 Data Pro, 8 Data Business, 40 Alerts Pro | £15,872 | £190,464 |

### What the arithmetic says

- To reach **£1m recognised revenue in 12 months**, the business needs to average about **£83.3k MRR**.
- At **£499/mo** Data Business pricing, that would require about **167 Data Business customers** if that were the only product — which is not supported by the evidence.
- Therefore, the **self-serve stack alone is not enough** for the £1m target.
- The path to £1m requires some combination of:
  - enterprise contracts,
  - bespoke reports,
  - data-room style services,
  - or materially higher seat volume than the current evidence suggests.

---

## Priority order

1. **New registrations + lead lists** — highest urgency, easiest ROI.
2. **Monitoring / alerts / watchlists** — strongest retention and recurring-value layer.
3. **API/webhooks + exports** — delivery and stickiness.
4. **Dossiers** — build only once source rights and cost-to-serve are controlled.
5. **Enterprise analytics / white-label** — pursue as a later-stage monetisation path, not the initial thesis.

---

## Evidence-based recommendation

### Continue
- The **live event-driven intelligence** business.
- The **new registration feed**.
- The **monitoring / alerts** workflow.
- The **search / export / API** packaging.

### Pivot
- From “we are a complete directory” to **“we surface market movement and workflow triggers”**.
- From broad TAM language to **segmented use cases by buyer and event type**.
- From speculative predictive claims to **testable heuristics and operational alerts**.

### Stop
- Treating buyer-persona WTP as market validation.
- Treating predictive survival / risk scoring as already-validated demand.
- Assuming the active-provider base is one uniform sale.

### Overall stance
**Conditional continue on a narrow wedge.** The market is real, the event history is real, and the live product surfaces exist. The evidence is not yet strong enough to justify broad platform expansion without validation.

---

## Compliance and governance notes

- Keep outreach and profiling within UK GDPR / PECR boundaries.
- Avoid any claim of CQC endorsement or affiliation.
- Treat enrichment sources as licensing-constrained.
- Do not operationalise predictive-risk scores as if they are regulated truth.
- Reconcile stock count drift before using the numbers in external collateral.

---

## Ready for QA

**Yes.** This is a source-linked, read-only portfolio map suitable for independent QA / Red Team review.
