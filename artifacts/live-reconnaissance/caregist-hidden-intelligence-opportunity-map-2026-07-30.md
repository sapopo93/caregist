# CareGist hidden intelligence and opportunity map — 30 July 2026

## DELIVERABLE RETURN
- **What was produced:** Aggregate, cross-signal opportunity analysis beyond the visible UI and prior registration-only framing.
- **Assumptions made:** Rows are locations unless explicitly identified as unique provider IDs. Data presence is not buyer intent. No individual-level inferences were made.
- **Known weaknesses / open questions:** Current production stock/events do not reconcile to local March/April datasets. No paid-customer, conversion, churn, occupancy, procurement or outcome data exists.
- **Compliance flags:** PECR/UK GDPR, profiling, data licensing, fairness and automated-decisioning review required before outreach or risk-scoring use.
- **Ready for QA:** yes.

## Grounded stock and identity facts
- Local active directory: **55,818 location rows**.
- Unique provider IDs: **36,492**.
- Production search/ledger stock: **56,742–56,743 rows**, unreconciled to local stock.
- Multi-service locations: **6,636 (11.89%)**.
- Group mapping coverage: **99.53% by provider row** in `provider_groups.csv`.
- Local contact coverage:
  - website + phone: **41,113**;
  - phone only: **14,555**;
  - website only: **40**;
  - neither: **110**.
- Quality report caveats: 116 invalid phones, 3,631 suspect addresses, 1,907 failed API calls.
- Validation sample: 199/200 fresh and no sampled rating mismatches; this does not reconcile the production registration/event lag.

## Hidden structural signals

### 1. Location-to-organisation graph
The 55,818 locations collapse to 36,492 provider IDs. This supports:
- parent/group account resolution;
- group expansion/contraction monitoring;
- acquisition/rebrand/location-transfer detection;
- account-level supplier planning rather than location spam;
- portfolio concentration and regional exposure.

**Commercial product:** group/account intelligence with explicit location/provider/legal-entity separation.

### 2. Multi-service complexity
Notable local combinations:
- Homecare + Supported Living: **3,428**;
- Homecare + Supported Housing: **234**;
- Homecare + Residential Homes: **125**;
- GP + Mobile Doctors: **140**.

These organisations have broader operational complexity and are more plausible buyers for bundled software, compliance, workforce and insurance solutions than a generic single-location lead.

**Commercial product:** service-adjacency and operational-complexity segmentation.

### 3. Digital-presence gap
- 14,555 phone-only locations and 110 with neither phone nor website are not automatically sales leads.
- Website absence among the local 2026 new-registration file is approximately 48.8%.

**Commercial products:** data correction, provider-claimed profile, digital-readiness benchmark and verified contact enrichment. Avoid treating missing website as distress or purchase intent.

### 4. Registration-episode reconstruction
The production “Not Yet Inspected” cohort contains old registrations and historical inspection dates. Registration dates can occur after visible inspection dates. This indicates event/lifecycle semantics, not a simple startup flag.

**Required derived model:**
- latest active registration episode;
- prior registration/location/provider history;
- ownership or provider-ID change;
- service-type inspection regime;
- registration-to-first-inspection elapsed time;
- evidence confidence and source watermark.

**Commercial product:** verified market-entry/lifecycle feed rather than raw `registration_date` filtering.

### 5. Inspection uncertainty, not universal staleness
The universal stale cohort covers 51,883/56,742 records (**91.44%**) because it combines missing and old dates. A useful model would compare a location with relevant peers and inspection regimes.

**Commercial product:** confidence-adjusted regulatory evidence:
- inspection age percentile by service/geography;
- expected-versus-observed inspection cadence;
- missing/not-applicable/old separated;
- rating coverage and evidence age;
- recent registration after historical inspection flagged.

### 6. Data completeness versus care quality
The existing `quality_score` awards points for populated fields. It is not care quality. This accidental conflation reveals two separate products:
- **Data Completeness / Enrichment Score** for suppliers, provider owners and internal QA;
- **Regulatory Evidence View** using CQC rating, dimensions, age, coverage and history without pretending to measure care quality.

The current group and comparison implementation must be corrected before either can be commercialised.

### 7. Group portfolio uncertainty
Groups support location counts, beds, regions, ratings, inspection dates and per-location completeness. New defensible measures include:
- rated coverage denominator;
- uninspected/no-date share;
- inspection-age distribution;
- rating dispersion and outliers;
- region/service concentration;
- additions/removals/transfers over time;
- bed-capacity data coverage;
- contact/digital completeness;
- confidence score for the portfolio view.

**Commercial product:** group watchlists and board/portfolio packs for suppliers, lenders, advisers, investors and operators—subject to strict non-advisory language.

### 8. Geospatial territory intelligence
Nearby search, coordinates, postcode and local-authority fields support:
- market density and whitespace;
- field-sales territory planning;
- local competitor/service mix;
- underserved-category mapping;
- travel-radius account prioritisation;
- group footprint overlap.

The current family radius UI is inconsistent, but the geospatial substrate is valuable.

**Commercial product:** postcode/territory maps and API queries, not raw national CSVs.

### 9. Supplier trigger combinations
Potential high-value combinations, requiring validation:
- new active registration episode + missing website + valid phone;
- group location addition + service adjacency + new geography;
- registration + no inspection + elapsed-time band;
- rating deterioration/improvement + group exposure + recent date;
- ownership/provider-ID change + retained location/service;
- new supported-living/homecare combination + local market density;
- new mobile/remote-service registration + national reach;
- location closure/removal + nearby replacement/expansion signals.

These are hypotheses, not buying intent.

### 10. Demand and participation graph
Enquiries contain provider, geography, care type, urgency and outcome state; claims/profiles/reviews contain provider participation and content. If genuine volume develops, CareGist can learn:
- demand by care type/geography/urgency;
- enquiry-to-response and claimed-versus-unclaimed performance;
- provider information gaps preceding enquiries;
- outcome attribution and referral quality;
- recurring family questions.

This would be more defensible than CQC data. Presently, no volume or outcome proof exists.

### 11. Service niches beyond generic social care
Production taxonomy exposes 58 raw labels. Larger overlooked categories include supported housing, diagnostics/screening, community healthcare, rehabilitation, hospitals, mental-health services, ambulances, urgent care, remote advice, prison healthcare, Shared Lives and hospices.

Raw labels contain legacy/current duplicates, so a canonical taxonomy and inclusion criteria are prerequisites. Launch verticals separately; do not imply one sales motion fits all.

### 12. Education/report generation
The animated story and assessment component suggest a content/report engine:
- narrated family explainers;
- provider induction/safeguarding content;
- provider-specific visit-question packs;
- white-labelled portfolio briefings;
- accessible print/audio reports.

The current sample assessment is not production-grade because it hard-codes benchmarks and misuses completeness as care quality.

## Opportunity priority

### Priority A — repair and internal validation
1. Reconcile location/provider/group/entity counts and dates.
2. Restore CQC ingestion and expose last-successful-source watermark.
3. Rename `quality_score` to data completeness everywhere.
4. Repair claim, region, service, city and sitemap paths.
5. Activate and validate real rating/status/registration events.
6. Separate CQC service taxonomy into canonical verticals.

### Priority B — first defensible recurring products
1. Verified market-entry and lifecycle alerts.
2. Group/account movement and portfolio-confidence monitoring.
3. Geospatial territory/whitespace intelligence.
4. Data-completeness/enrichment workflows.
5. Event API, saved views, digests and signed webhooks with freshness SLOs.

### Priority C — participation/demand products after evidence
1. Claimed profile and provider information workflow.
2. Enquiry routing and outcome attribution.
3. Moderated reviews and provider responses.
4. Family/provider reports and education.

### Defer
- family-facing care-quality ranking;
- paid rank/sponsorship before traffic and disclosure controls;
- broad bulk-data moat claims;
- distress/risk/occupancy/buying-intent inference;
- immediate outreach based solely on public data.

## Commercial wedge hypotheses to test
1. **Group intelligence pilot:** 10 supplier/investor/adviser interviews using one reconciled group pack.
2. **Territory intelligence pilot:** one region + one service vertical + geospatial whitespace and new-entry changes.
3. **Data QA pilot:** provider owners validate completeness/corrections and claim workflow.
4. **Lifecycle feed pilot:** prove 30-day source freshness and event precision before charging.

No external test should begin without Human Gate 1, verified UK Country Pack, resolved entity/controller, lawful-use guidance and explicit budget approval.
