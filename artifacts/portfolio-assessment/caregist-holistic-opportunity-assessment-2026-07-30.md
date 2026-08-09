# CareGist holistic opportunity assessment — final

**Date:** 30 July 2026
**Status:** Read-only assessment; no launch authority
**Country:** UK/England
**Governance blocker:** No verified UK Country Pack was located. Every UK-specific pricing, VAT, contracting, privacy, direct-marketing, data-sharing and launch conclusion below is **provisional and blocked** pending a verified Country Pack plus qualified legal/accounting review. Internal product and strategy analysis may continue; it authorises no external action.

## Executive conclusion

CareGist is materially larger than the rolling 90-day registration cohort. The deployed homepage displayed 56,742 as “active CQC providers tracked” during public browser inspection on 30 July 2026, while 91 appeared in the rolling 90-day list. However, the 30 June discovery manifest separately records 56,743 `care_providers` rows and 56,742 `trusted_event_ledger` rows without proving an ACTIVE filter. The exact active provider/location denominator remains unreconciled. The 55k+ provider/location graph is still the reusable market asset; the 90-day list is one change-trigger product derived from it.

**Current recognised revenue: £0, as reported in the founder/project context; not independently audited here.** CareGist is not exploiting the whole asset commercially today. It has broad deployed capability and several sensible product surfaces, but no demonstrated paying-customer evidence, repeatable acquisition, retention, validated willingness to pay or observed unit economics. The correct decision is therefore neither “abandon” nor “scale”: preserve the platform, reduce the portfolio to three testable commercial wedges, and demand paid evidence before further product expansion.

The pay-per-qualified-demo proposal should be treated as a premium service experiment, not the company’s core model.

## Evidence boundary

### Verified from the deployed public/authenticated application

- Authenticated Business dashboard with exports, full fields, webhooks, 500 monitors, up to 10,000-row exports and 10 users.
- Dashboard market analytics and event-ledger-driven new registration feed.
- The public homepage displayed 56,742 as “active CQC providers tracked” on 30 July 2026; this label is not treated as a reconciled database count.
- The public homepage and live rolling list displayed 91 recent registrations during browser inspection on 30 July 2026.
- 53 Inadequate, 2,904 Requires Improvement and 20,989 Not Yet Inspected records shown publicly.
- 1,091 groups with at least three locations.
- Search, filtering, provider profiles, public discovery, group pages, compare, CSV/XLSX exports, API, signed webhooks and monitoring/rating-change surfaces represented in deployed pages and code.
- Product-truth limitation: the 30 June discovery manifest records 56,742 new-registration ledger rows but zero `rating_changes` and zero `provider_monitors`; rating-movement delivery is implemented/advertised but not proven active.
- Public launch pricing: £49 Alerts Pro, £99 Data Starter, £199 Data Pro and £499 Data Business per month excluding VAT; custom Enterprise.
- Provider-side claimed, £99/location/month Pro and £149/location/month sponsored products shown in deployed pricing materials.

### Verified from the 28 March 2026 repository dataset snapshot

- 55,818 active location rows and 36,492 unique provider IDs.
- 4,876 provider IDs with at least two locations; 24,202 locations sit within those multi-location provider IDs.
- Service-type counts include Homecare Agencies 14,240; Dentist 12,004; Residential Homes 10,309; Doctors/GPs 9,367; Supported Living 4,727; Nursing Homes 4,386.
- Snapshot ratings include Good 22,617; Not Yet Inspected 20,989; Inspected But Not Rated 5,928; Requires Improvement 2,904; Outstanding 1,452; No Published Rating 1,858; Inadequate 52.
- 55,668 records contain a phone, 41,153 a website and 15,097 a positive bed count.

Differences between the March snapshot and July deployed counts demonstrate that CareGist is a moving dataset. Every external market-size claim must carry an exact definition, source, date and deduplication method.

### Database reconciliation still required

The 30 June discovery manifest reports 56,743 `care_providers` rows and 56,742 `trusted_event_ledger` rows. It does not show whether the provider count is filtered to `status='ACTIVE'`. The March directory snapshot contains 55,818 rows, all marked ACTIVE. Until a fresh status-filtered query is verified, CareGist must not externally claim that 56,742 or 56,743 equals unique active provider organisations.

The observed 91-record rolling 90-day cohort also conflicts with the deployed historical claim of 340 new registrations per month for January–March 2026: at the same scope and a current feed, a 90-day window would be materially larger. This may reflect different units, changed volume, filter scope or stale/incomplete ingestion. The cause is not verified. Suspend the 340/month claim and do not sell the 90-day feed as complete/current until a dated source-to-ledger reconciliation and freshness check pass.

### Roadmap or unverified concepts—not sellable facts

The internal product specification proposes Companies House enrichment, Director DNA, property and planning data, job-posting velocity, capital signals, dossiers, pre-inspection risk scoring, survival indices, forecasts, white-label reports and an Intelligence tier. The specification itself says dossiers and Intelligence-tier capabilities are not implemented as self-serve products unless later release evidence says otherwise.

Internal willingness-to-pay statements, conversion claims, competitive assertions and risk-score weights are hypotheses. They are not market evidence.

## What the 55,000 are

The 55k+ records are not one list and should not become 55,000 cold prospects. They are a provider/location graph from which CareGist can produce event-driven, buyer-specific intelligence.

The monetisable objects are:

1. **Provider stock:** who exists, where, type, services, ratings, beds and contact surface.
2. **Provider events:** new registration, rating change, inspection, status change, new location, group expansion, ownership/data change and eventual deregistration.
3. **Provider cohorts:** recently registered, uninspected, at-risk, high-performing, stale inspection, multi-location, expanding, geographic and service-type slices.
4. **Provider groups:** group footprint, location mix, ratings, beds, regions and expansion/quality movement.
5. **Market aggregates:** supply, growth, concentration, quality distribution, service gaps and movement by geography and category.

The value is not the raw count. It is converting those objects into decisions for a specific buyer.

## Lifecycle opportunity map

| Provider cohort / event | Current live scale | Buyer problem | Likely buyers | Product form | Main caution |
|---|---:|---|---|---|---|
| New registration within 90 days | 91 observed; historical 340/month claim is suspended pending reconciliation | Reach entrants during setup | Software, recruitment, training, equipment, insurance, policies | Feed, alerts, CRM webhook, filtered list, optional introduction | Completeness/freshness unverified; registration does not prove need or pre-registration access |
| Not Yet Inspected | 20,989 | Identify early-stage or unevaluated services | Compliance, training, software, insurers, suppliers | Cohort monitoring and prioritised lists | May include old services or categories not routinely rated; not synonymous with new |
| Requires Improvement | 2,904 | Identify quality-improvement demand | Turnaround, compliance, training, workforce, governance technology | Rating-change alerts, filtered account lists, reports | Sensitive targeting; no exploitation or guaranteed-need claim |
| Inadequate | 53 | Urgent quality and operational support | Specialist turnaround and compliance firms | Immediate alerts and tightly governed account intelligence | Very sensitive; small market; safeguarding and reputational risk |
| Good / Outstanding | 24,069 in March snapshot | Reputation, growth, benchmarking, partnerships | Providers, recruiters, investors, groups, families | Visibility, group benchmarking, reports | Paid prominence must not distort objective quality presentation |
| Stale/missing inspection | 50,959 in March snapshot using local 3-year rule | Monitor uncertainty and inspection backlog | Insurers, consultants, commissioners, provider groups | Watchlists and transparent recency analytics | Extremely broad and may reflect inspection policy, not risk |
| Multi-location/group | 1,091 public groups with 3+ locations | Account planning, benchmarking, expansion and portfolio risk | Enterprise vendors, insurers, lenders, investors, provider groups | Group dashboard, expansion alerts, enterprise API/reports | Group identity/deduplication quality and procurement requirements |
| New location in existing group | Event-dependent | Detect expansion and supplier opportunity | National vendors, property, recruitment, equipment | Group expansion webhook and account alert | Must distinguish location from new legal provider |
| Rating improvement or deterioration | Event-dependent | Retention, intervention, reputation and portfolio monitoring | Consultants, insurers, groups, commissioners | Rating-change webhook, monitors, weekly digest | Causal claims prohibited; avoid automated adverse decisions |
| Geographic/service-market movement | Whole graph | Capacity, competition and territory strategy | LAs/ICBs, investors, large vendors, groups | Market map, periodic report, enterprise data feed | Methodology, public procurement and data-sharing controls |
| Provider contact/data changes | Event-dependent | Keep CRM current and detect operating change | Vendors and data teams | Change feed / refresh service | Source accuracy, personal data, suppression and provenance |

## Service-type niches

### Social-care operating niches

- **Homecare Agencies (14,240):** rostering, eMAR, care-planning software, recruitment, training, insurance, payroll, finance, compliance and telephony.
- **Residential + Nursing Homes (14,695 combined):** property, beds/furniture, nurse-call systems, pharmacy, food, laundry, equipment, agency staffing, facilities, energy, insurance and compliance.
- **Supported Living (4,727 in the March snapshot):** housing partnerships, assistive technology, transport, workforce, medication, finance and compliance. Supported-housing counts require separate sourcing and are not combined here.
- **Hospice, mental-health, rehabilitation and specialist services:** specialist workforce, clinical systems, governance, pharmacy, equipment and commissioning intelligence.

### Wider CQC-regulated healthcare niches

- **Dentists (12,004)** and **Doctors/GPs (9,367)** are together a very large part of the dataset. They create possible dental/primary-care software, recruitment, compliance, insurance and equipment products.
- They should not be mixed casually into a “care-provider procurement concierge.” They require separate buyer language, category knowledge, legal review and validation.
- The broader healthcare data may ultimately justify a parent “CQC market intelligence” product with vertical modules for social care, dental, primary care and independent healthcare.

**Deferred dental vertical:** potential buyers include dental-practice software, equipment, consumables, compliance, recruitment and insurance firms. Potential signals include new registrations, ownership/group expansion, inspections and new locations. Current CareGist fields may support territory/account lists, but no dental buyer demand or willingness to pay has been evidenced.

**Deferred primary-care/GP vertical:** potential buyers include clinical-system, workforce, premises, diagnostics, compliance and insurance suppliers. Potential signals include registration/location movement, group structure and inspections. NHS procurement, commissioning structures and sector-specific data rules require a separate assessment. Neither vertical should enter the first social-care proof cycle.

## Buyer/product architecture

### Wedge 1 — CQC market-movement intelligence (first priority)

**Buyers:** care-sector software, recruitment, training, equipment, insurance and compliance suppliers.
**Product:** implemented new-registration feed, filters, exports, API and webhooks; feed freshness/completeness must be reconciled before sale. Rating-change monitoring is coded/advertised but must be activated and verified before sale.
**Why first:** largely deployed, recurring, lower marginal delivery cost, short buyer feedback loop and uses the full provider graph.
**Commercial test:** sell the decision workflow—not raw CSV. Test whether buyers act on new registrations, rating changes, group expansion or a combination.

### Wedge 2 — Group/account intelligence (second priority)

**Buyers:** national suppliers, insurers, lenders, investors, large provider groups and M&A teams.
**Product:** existing group footprint/benchmarking plus monitored new locations, rating movements and bespoke account/market reports.
**Why:** 1,091 multi-location groups create fewer, higher-value accounts and potential enterprise ACV. Existing group data provides a service-led proof before expensive enrichment is built.
**Commercial test:** one manual evidence-backed group/territory report and monitoring prototype; require paid or procurement-qualified demand before building dossiers or predictive models.

### Wedge 3 — Quality and compliance movement (third priority)

**Buyers:** compliance consultancies, training providers, workforce/governance technology and turnaround specialists.
**Product:** RI/Inadequate/not-yet-inspected cohorts and rating-change alerts, filtered by service and geography.
**Why:** 2,904 RI and 20,989 Not Yet Inspected records are materially larger than the new-provider cohort.
**Commercial test:** validate which signal predicts a legitimate need and whether buyers will pay for recurring monitoring rather than one-off lists.

### Service layer — permission-led introductions

Qualified introductions should sit above the data subscription. They can generate learning and premium revenue but should not be the sole economics. Provider authorisation, objective qualification and conflict controls are mandatory.

### Secondary line — provider visibility

Free claims, £99 Pro and £149 sponsored listings offer a separate provider-paid model. It could monetise the stock market, but value depends on family/referrer traffic, enquiries and measurable outcomes. Sponsored placement creates trust/conflict risks and must remain clearly labelled and separate from objective ratings. The field is already crowded: carehome.co.uk and homecare.co.uk advertise free claimed profiles, paid enhanced tiers, reviews, enquiries and performance tracking, with Lottie and Autumna also established in discovery. Do not prioritise this line until CareGist can evidence differentiated traffic, claim demand, enquiry value and acceptable customer-acquisition cost.

## Competitive reality and defensibility

Raw CQC access is not a moat. CQC itself supplies an API and downloadable files under the Open Government Licence.

Direct and adjacent competition observed on 30 July 2026 includes:

- **Medical Scout:** its public page was inspected through the browser DOM on 30 July 2026. It displayed daily new-CQC-registration alerts, contact/enrichment claims and £45/month regional / £95/month full-UK prices. Performance, coverage and compliance claims were observed but not independently validated.
- **VantageData:** its healthcare and pricing pages were inspected through the browser DOM on 30 July 2026. They displayed a 56,826-record CQC register for £49, 51,967 healthcare contacts for £59, £99–£149 annual/bulk packs and £29/£79/£149 monthly subscription tiers. These current-page observations were not purchase-tested or independently validated. They nevertheless create apparent price pressure on static datasets and generic API/search access.
- **CQC:** free API and prepared data downloads; therefore customers can build internally if CareGist adds insufficient workflow value.
- **LaingBuisson, Carterwood and CSI Market Intelligence:** established healthcare/care market intelligence and advisory providers. Carterwood's public bespoke-advisory page, inspected on 30 July 2026 (`https://www.carterwood.co.uk/our-advisory-expertise/bespoke/`), advertised demand, supply, demographics, staffing, fees, funding mix, operational-cost data and sector-specialist interpretation.

CareGist therefore cannot defend itself with “we have 55,000 CQC records” or “we alert on new registrations.” Potential defensibility must come from a combination of:

1. broader event coverage—registrations, rating movements, group expansion, inspection recency and status changes;
2. reliable sub-cycle change detection with auditable effective/observed timestamps;
3. provider/location/group identity resolution and deduplication;
4. operational delivery through saved workflows, signed webhooks, API and CRM integration;
5. buyer-specific scoring and segmentation that is validated, explainable and lawful;
6. historical event data that supports trend and account-movement analysis;
7. service and support integrated into customers’ recurring commercial process;
8. eventually, lawful enrichment that demonstrably changes buyer action.

Current £99–£499 plan pricing may still be defensible for workflow/API value, but it is not defensible against static-data competitors without measured customer outcomes. Pricing remains an unapproved hypothesis.

## What not to pursue now

- Do not attack every service type or buyer niche simultaneously.
- Do not contact 55,000 providers.
- Do not build Companies House/property/job-board enrichment before a buyer commits to the underlying decision.
- Do not publish predictive provider risk/survival scores without valid methodology, bias/error review, explainability, dispute/correction processes and legal assessment.
- Do not treat Not Yet Inspected or stale inspections as evidence of poor quality or urgent buying intent.
- Do not make the consumer directory, provider listings and supplier lead generation indistinguishable; conflicts must be visible and controlled.
- Do not use the 56,742 count externally without definition/date/source/deduplication notes.

## Revenue capacity — provisional, blocked for external use

This arithmetic uses deployed advertised GBP prices only as scenario inputs. It does not approve pricing, VAT language, contracts or revenue recognition. Those remain blocked pending the verified UK Country Pack, entity/VAT confirmation, Finance review and Henry's pricing gate.

### Plan-only mathematics

To recognise £1m excluding VAT from customers present for a full 12 months would require approximately:

- 1,701 Alerts Pro customers at £49/month;
- 842 Data Starter customers at £99/month;
- 419 Data Pro customers at £199/month;
- 167 Data Business customers at £499/month;
- 842 Provider Pro locations at £99/month;
- 560 sponsored locations at £149/month.

Under an even customer ramp across 12 months, required month-12 counts rise to about 3,140 Alerts, 1,554 Starter, 773 Pro, approximately 309 Business, 1,554 Provider Pro or 1,033 sponsored locations respectively.

At Enterprise ACVs, £1m equals 100 contracts at £10k, 67 at £15k, 40 at £25k, 20 at £50k or 10 at £100k. Current evidence does not establish one such contract.

### Illustrative bounded year—not a forecast

A year ending with 12 Business, 24 Pro and 50 Provider Pro accounts, plus four £15k enterprise contracts and twenty £500 lead packs, would recognise about £172k under an even-ramp assumption. Even this requires validated acquisition and retention that do not yet exist.

### Specialist portfolio scenarios

Finance/Admin modelled the whole current and proposed portfolio using a linear recurring-revenue ramp plus explicitly assumed one-off prices. The outcomes were:

| Scenario | Year-end MRR | Exit ARR | Recognised revenue in year |
|---|---:|---:|---:|
| Evidence-constrained | £13.1k | £157.7k | £110.0k |
| Founder-led base | £43.7k | £524.3k | £335.6k |
| Aggressive stretch | £108.2k | £1.299m | £806.9k |

The stretch case already assumes 100 Alerts, 180 Starter, 70 Pro, 30 Business, 380 paid provider-listing locations, three modelled enterprise retainers and substantial one-off work. It still falls about £193k short of £1m recognised revenue. Its one-off prices and £5k/month enterprise retainer are assumptions, not approved offers.

Provider visibility is mathematically attractive: approximately 842 Pro locations or 560 sponsored locations maintained for a full year equal £1m ARR at current displayed prices—about 1.5% or 1.0% of the March row base. But this is not the recommended first wedge because claim conversion, traffic, enquiries, churn and acquisition cost are unobserved, while established directories already hold audience and review-network advantages.

### Mathematical £1m mix—not a credible current forecast

A model containing 60 ending Business accounts, 120 ending Pro accounts, 12 £25k enterprise contracts, 250 ending Provider Pro locations, 75 ending sponsored locations and £170k of lists/reports/introductions produces approximately £1.05m under simplified even-ramp assumptions. It requires hundreds of customers across two-sided markets, enterprise procurement, functioning self-serve payments, support and high retention. No evidence currently makes that a responsible 12-month commitment.

## Commercial sequencing — internal preparation only

The sequence below authorises no outreach, publishing, pricing communication, data sharing, contract, spend or billing. Those actions remain blocked pending the verified UK Country Pack, qualified review and explicit human approval.

### Phase A — evidence cleanup and product truth

- Publish no new claims.
- Determine whether CareGist is legally operated by H-Kay Limited (as the deployed footer states), N Dumane, or another entity; then confirm Companies House status, contracting authority, VAT status and ICO/controller registration for that entity.
- Define provider/location/event counts and source methodology.
- Reconcile the 91-record 90-day view against the historic 340/month claim, verify the maximum effective/observed dates, test daily ingestion freshness, and remove or correct any public claim that fails.
- Create live/coded/roadmap capability register.
- Verify Stripe purchase paths, entitlement enforcement, exports, webhooks, monitoring and support without accepting unapproved commercial commitments.

### Phase B — three buyer problem tests

- Market-movement intelligence: 8–12 suppliers across software, recruitment/equipment and compliance.
- Group/account intelligence: 5–8 national suppliers, brokers, investors or groups.
- Quality/compliance movement: 5–8 consultants/training/governance vendors.

Require evidence of workflow, current alternative, frequency, budget owner, decision process, desired signal, data fields and concrete next step. Internal persona WTP is not evidence.

### Phase C — paid proof, one wedge at a time

For the first wedge that passes discovery, offer one bounded paid proof after Henry approves price, terms, privacy/data use and publication/outreach. Measure activation, export/API use, weekly return, signal-to-action rate, support cost, renewal intent and cash collection.

### Phase D — expand only from observed pull

- Add another signal only when buyers use the first.
- Add enrichment only when it changes a buying decision and has a lawful, sustainable source.
- Add enterprise reporting only with a named budget and procurement path.
- Add provider visibility only when traffic and enquiries create demonstrable value.
- Add introductions only with provider authorisation and viable labour economics.

## Decision gates and kill criteria

Continue a wedge only if:

- at least three buyers independently describe the same recurring job;
- at least two identify a credible budget and buying route;
- at least one accepts a paid or procurement-qualified proof;
- the current data fields are sufficient to create an action;
- delivery has positive contribution without free founder labour;
- no unresolved Critical/High compliance, security or claims finding remains;
- buyer usage recurs after initial curiosity.

Stop or redesign if:

- buyers only want a cheap one-off CSV;
- the signal arrives after the commercial decision;
- no budget owner exists;
- provider/contact quality is insufficient;
- customers require unapproved personal-data enrichment or scraping;
- manual fulfilment dominates revenue;
- the product depends on unsupported predictive or CQC-endorsed claims;
- provider trust or directory neutrality is compromised.

## Current decision

- **Is there a real asset?** Yes: a deployed provider graph, change ledger, group layer and delivery infrastructure.
- **Is the business proven?** No.
- **Are the 55k providers exploitable?** Yes as segmented, change-driven intelligence—not as one outreach list.
- **Should the company abandon CareGist?** No; validate the broader intelligence platform.
- **Should it scale now?** No.
- **Is £1m recognised revenue in the next 12 months a credible forecast today?** No.
- **Could the architecture support a £1m+ business eventually?** Yes, if recurring self-serve subscriptions and several higher-ACV enterprise contracts are validated. That remains a hypothesis.

## Recommended founder decision

Approve internal preparation of three separate proof briefs—market movement, group/account intelligence and quality/compliance movement. Do not approve live outreach or pricing yet. After independent QA, choose one wedge for controlled customer discovery; do not attempt all three concurrently.
