# CareGist product reconnaissance — public exhaustive, authenticated partial — integrated founder report

**Date:** 30 July 2026
**Mode:** Read-only product, runtime, source and aggregate-data reconnaissance
**Decision scope:** Internal product/resource decision only; no launch, outreach, export delivery, publication, payment, pricing or contract authority

## DELIVERABLE RETURN
- **What was produced:** A route-by-route capability atlas, live runtime findings, source-backed protected-facility inventory, cross-signal data analysis and commercial opportunity map.
- **Assumptions made:** Production rows are regulated locations unless proven otherwise. A coded route is not called live unless exercised or independently evidenced by a supplied screenshot.
- **Known weaknesses / open questions:** The authenticated Business dashboard session expired before an exhaustive live click-through. Its top section is screenshot-observed; lower dashboard, admin and provider-owner facilities are executable-source-backed but not live-state verified.
- **Compliance flags:** Existing governance, entity, CQC reuse, privacy, VAT, terms, marketing and data-use blockers remain. No external action is authorised.
- **Ready for QA:** yes.

## Executive conclusion

CareGist is materially broader and more capable than a 91-record new-registration list. It contains the foundations of at least five products:

1. CQC location/search and geospatial discovery;
2. event-led supplier intelligence and workflow;
3. group/account portfolio intelligence;
4. provider participation, profile and enquiry network;
5. API/export/webhook infrastructure.

The strongest defensible future product is a **verified market-lifecycle and account-movement intelligence system**, not a raw directory and not the proposed attended-demo service.

However, CareGist is not commercially safe to scale in its present state. The most important discovery is that the field presented throughout the product as a care **“Quality Score”** is actually a **data-completeness score**. This semantic error contaminates provider comparison, local ranking, group averages, national benchmarks, city ordering and the sample assessment. Several public route families also return false zero counts, provider sitemaps return 503, claiming is broken and the new-registration feed is visibly stale.

**Founder decision:** continue only as a controlled repair-and-validation project. Do not launch paid quality ranking, supplier alerts, provider-profile claims, bulk intelligence or family recommendations until the blocking corrections pass.

## What was actually explored

### Live public routes exercised
- homepage;
- full search and all five opportunity modes;
- new-registration final page;
- lead-list request screen;
- pricing and exact plan links;
- API product page;
- groups and a large group detail;
- provider detail;
- provider claim route;
- postcode/radius family search;
- direct provider comparison;
- sample assessment;
- Why CareGist;
- animated narrated story;
- valid/invalid service pages;
- London region page;
- Bournemouth care-home and rating city pages;
- signup, login, password recovery and email verification;
- privacy, terms, acceptable use, review policy and cookies;
- directory health, service taxonomy, robots and sitemaps;
- protected route redirects for dashboard, provider dashboard and admin.

### Authenticated evidence
A supplied authenticated screenshot verifies:
- Business plan;
- 60 requests/second and 10,000/day;
- full fields, signed feed webhooks, 10,000-row exports and 500 monitors;
- 10 included users;
- service-type and provider-category analytics.

The live session then expired. The managed browser and current Chrome profile both redirected to login. Therefore lower authenticated sections are classified from executable code, not falsely claimed as live-clicked.

### Source and data inspection
- 32 frontend page routes;
- 7 Next route handlers;
- 24 backend router modules;
- 72 `/api/v1/...` references;
- dashboard, new-registration feed, provider-owner and admin source;
- claim stepper and assessment engine;
- quality-score generation;
- local directory, raw providers/locations, 2026 registrations, groups, quality and validation reports.

## Critical findings

### C1 — “Quality Score” is data completeness, not care quality
`quality_audit.py` awards points for populated name, postcode, phone, website, coordinates, rating field, inspection date, service types, specialisms, regulated activities, beds, authority and region. The source explicitly says the tier is **“Data completeness — NOT a quality rating.”**

Production nevertheless uses the field to:
- order relevance and “quality” search;
- choose top city providers;
- calculate group “average quality” and national benchmarks;
- rank nearby providers;
- compare providers;
- state above/below national quality;
- select a “highest-rated alternative”; and
- drive sample assessment verdicts.

This explains why an unrated group can show near-perfect average quality and why a 2017 inspection can produce 100/100.

**Required correction:** rename the existing field everywhere to Data Completeness Score; remove it from care-quality, recommendation and ranking language; independently design and legally/clinically review any separate regulatory-evidence metric.

### C2 — Source freshness is not operationally controlled
- New-registration view: 91 records.
- Latest visible registration: 29 May 2026.
- Review date: 30 July 2026.
- Lag: 62 days.
- Production health says database/email are healthy but exposes no source watermark, last successful ingestion or lag.
- Public pages claim daily refresh; privacy says weekly refresh.

**Required correction:** source-to-ledger reconciliation, last-successful-ingestion watermark, completeness counts, event lag SLO and customer-visible freshness status.

### C3 — Public discovery route families produce false market statements
- `/region/london` states zero providers because search is unavailable.
- `/services/home-care` states zero despite 14,240 production service rows.
- `/care-homes/bournemouth` states zero while radius search reports 644 providers within ten miles.
- rating-specific city pages share the failing path.
- provider sitemap index and shard return 503.

**Required correction:** repair the server-side API path or fail closed with no indexable zero claim; restore provider sitemaps; test canonical city/region/service pages.

### C4 — Claiming and provider participation are blocked
A real provider claim route renders “Something went wrong.” This blocks:
- verified provider participation;
- corrections and enrichment;
- provider responses;
- paid profile conversion;
- review responses; and
- the strongest proprietary-data path.

The claim flow also advertises optional fast-track review without visible price/term and promises verification email to a registered address that must be proven available.

### C5 — Current opportunity cohorts are not decision-ready
- “Not Yet Inspected” includes old registrations and records with historical inspection dates.
- Registration dates can be later than visible inspection dates.
- “Stale inspection” combines old and missing dates and covers 51,883/56,742 records (91.44%).
- Inadequate/Requires Improvement labels are called current although event freshness is unproven.

**Required correction:** registration-episode and status-history reconstruction, service-specific inspection semantics, event freshness and confidence flags.

## High findings

### H1 — Group intelligence is strong but currently misleading
The location/group graph is a genuine asset. Group detail contains locations, beds, regions, ratings, inspection dates and scores. But list/detail metrics disagree, rated denominators are unclear and “average quality” is completeness.

**Better product:** rated coverage, uninspected share, inspection-age distribution, rating dispersion, service/geographic concentration, additions/removals and confidence.

### H2 — Comparison is under-discovered and contractually inconsistent
Direct comparison works and includes contact, beds, ownership, five CQC domains, reviews and enquiries. The source allows only 2–3 providers while Data Pro advertises up to 5. Its headline score is semantically invalid.

### H3 — Radius/family discovery has contradictory result counts
BH1 1AA within ten miles reported 644 providers, rendered three and said 197 more. “Skip and show results” did not reveal more. Export is exposed but was not exercised.

### H4 — Product and policy claims conflict
- daily versus weekly refresh;
- traffic-analysis banner versus no analytics-cookie claim;
- informational/data-completeness scoring versus public “Quality Score”;
- immediate outreach positioning versus AUP prohibition on unsolicited marketing;
- live plan names versus older Terms names;
- “every provider has an assessment” while real provider pages do not import it.

### H5 — API product is broad but documentation proof is incomplete
The platform supports search, detail, nearby, exports, monitors, feeds, digests, saved views, webhooks, applications and keys. The advertised `/api/v1/openapi.json` path returns `detail: Not Found`. No machine-readable live contract was found.

### H6 — Security and data-handling design needs focused review
- Cookie policy states API key and tier are stored in localStorage; dashboard code stores user and tier locally but requires password re-entry to reveal the key.
- Named/team keys and master admin key are handled in browser state.
- Provider photos/logos/virtual tours are remote URLs.
- Claim/review/enquiry/admin surfaces contain personal data.

No exploit was attempted. A dedicated threat model and runtime security review are required before launch.

## Complete facility picture

### Customer intelligence workspace
- plan entitlements and usage limits;
- provider service/category analytics;
- 90-day versus prior-90-day service growth;
- new-registration ledger;
- filters by query, region, authority, service, provider type, postcode prefix and date range;
- confidence sorting and pagination;
- CSV/XLSX export;
- saved views;
- weekly digest;
- API-key reveal;
- named seats/keys;
- webhook delivery status;
- quick-start API;
- account deletion.

### Provider-owner workspace
- claim identity/authority workflow;
- inspection response;
- logo, description and photos;
- virtual tour;
- funding and fee guidance;
- minimum visit duration;
- contract types and age groups;
- profile tier checkout.

### Admin workspace
- provider/claim/review/enquiry metrics;
- service/category/growth analytics;
- top-enquired providers;
- claim approval/rejection;
- review moderation;
- enquiry status management.

### Public/family workspace
- search and opportunity lists;
- provider facts and CQC report;
- reviews and enquiries;
- postcode radius discovery;
- compare;
- group reports;
- sample assessment;
- education/story content.

## Hidden intelligence beyond the existing proposition

### 1. Organisation and group movement
55,818 local locations map to 36,492 provider IDs. This supports parent/group resolution, location changes, expansion, contraction, rebrand/transfer detection and account-level monitoring.

### 2. Service-adjacency complexity
6,636 locations (11.89%) have multiple service types. Material combinations include Homecare + Supported Living (3,428), Homecare + Supported Housing (234), Homecare + Residential (125) and GP + Mobile Doctors (140).

These combinations are better workflow signals than “new provider” alone.

### 3. Digital/data completeness
Local contact stock includes 14,555 phone-only locations and 110 with neither phone nor website. This supports data-quality and provider-correction products, not an automatic outbound-intent claim.

### 4. Geospatial territory and whitespace
Coordinates, radius, postcode and authority fields can support territory design, competitor density, service gaps, travel routing and group-footprint overlap.

### 5. Regulatory evidence confidence
Replace universal staleness with peer/service-adjusted evidence age, rating coverage, missing/not-applicable separation and source confidence.

### 6. Provider participation and demand graph
If claims, reviews and enquiries develop volume, CareGist can derive provider responsiveness, information gaps, care-type/geographic demand and outcome attribution. No such volume is currently evidenced.

### 7. Distinct regulated verticals
The production taxonomy exposes 58 raw labels across social care, dental, GP, diagnostics, hospitals, mental health, ambulances, rehabilitation, urgent care, remote advice, prison healthcare, Shared Lives and hospices. Legacy/current duplicates must be canonicalised; verticals need separate propositions.

### 8. Education and reporting
The animated story and assessment component can become narrated family explainers, provider induction, visit-question packs and white-labelled reports after the scoring model is corrected.

## Product priority after repair

### First priority
**Verified market lifecycle and group/account movement intelligence**
- fresh registration/status/rating/ownership/location events;
- explicit provenance and confidence;
- saved views, digests, API and webhooks;
- group and territory context.

### Second priority
**Data completeness and provider enrichment**
- accurate field-completeness score;
- correction/claim workflow;
- verified provider-supplied practical information;
- provenance by field.

### Third priority
**Group portfolio and geospatial intelligence**
- portfolio confidence and movement;
- geographic/service concentration;
- territory and whitespace maps.

### Later, only after genuine participation
- enquiry routing/outcomes;
- reviews/provider responses;
- profile sponsorship;
- family reports.

### Do not lead with
- raw CQC records;
- £175 attended demos;
- family-facing quality ranking;
- universal stale-inspection lists;
- broad cold-outreach lists;
- distress, occupancy or buying-intent inference.

## Required repair sequence
1. Rename and remove misuse of the completeness score.
2. Restore source ingestion; expose freshness and reconcile all denominators.
3. Repair claim, region, service, city and sitemap paths.
4. Build canonical provider/location/group/entity and service taxonomy.
5. Generate true event history for registration, status, rating, location/group movement.
6. Validate monitors, digests, exports, API and signed webhooks end to end.
7. Define provider identity/authority verification and moderation operations.
8. Threat-model local storage, keys, remote media, admin and personal-data flows.
9. Resolve entity, CQC reuse, UK Country Pack, privacy, terms, VAT, price display and lawful-use controls.
10. Only then run controlled internal proof briefs and Human Gate 1.

## Decision and gates

**Continue:** yes, because the provider/group/geospatial graph and workflow infrastructure contain defensible raw material.
**Pivot:** yes, from raw lists/demos toward verified lifecycle and account intelligence.
**Launch now:** no.
**External spend:** not authorised.
**Outreach/publication/billing:** not authorised.

The immediate founder resource should fund only internal repair, reconciliation and three proof briefs. Any external validation, price test, outreach, provider claim activation, monitoring delivery, export sale, API commitment or publishing change requires explicit Human Gate 1 and applicable legal/privacy/finance/publishing approvals.

## Evidence files
- `artifacts/live-reconnaissance/caregist-engineering-capability-atlas-2026-07-30.md`
- `artifacts/live-reconnaissance/caregist-hidden-intelligence-opportunity-map-2026-07-30.md`
- `artifacts/live-reconnaissance/caregist-exhaustive-live-recon-task-brief-2026-07-30.md`
- Existing portfolio assessment and QA artifacts under `artifacts/portfolio-assessment/`.
