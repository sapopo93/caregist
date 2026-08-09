# CareGist Master Strategy

**Status:** Authoritative product, market, promise, and launch strategy
**Version:** `2026-08`
**Effective date:** 9 August 2026
**Owner:** Founder
**Review cadence:** At every catalogue or release-gate decision

This document replaces the following drafts from `files234.zip`:

- `CareGist_Master_Strategy.md`
- `CareGist_Pricing_Strategy_Enhanced_Gap_Analysis.md`
- `CareGist_Use_Cases.md`

Those files remain research inputs only. They must not be used to set prices,
write public claims, qualify a release, or direct outreach.

---

## 1. Decision authority and conflict resolution

When two CareGist documents disagree, use this order:

1. The founder-approved **CareGist CQC Signal Intelligence — Production
   Delivery Plan** supplied in the current implementation task.
2. This master strategy, which reconciles that plan with the proof-first
   go-to-market decision.
3. `deploy/stripe-price-manifest.json` for exact commercial objects, prices,
   intervals, lookup keys, sale channels, and archive status.
4. `artifacts/governance/2026-08-09-cqc-signal-intelligence-initiative.md`
   for current release-gate state and human approvals.
5. Implemented product configuration and tests for what the software currently
   enforces.
6. Older plans, analyses, use-case libraries, lead lists, and pitch materials.

The Stripe manifest is digest-locked by the offline release verifier. A new
commercial decision requires a new catalogue version; it must not be introduced
through website copy, an ad hoc Stripe object, or a sales exception.

### Locked does not mean validated

Catalogue `2026-08` is locked so the company can run one coherent launch
experiment. It does **not** mean the market has validated £299, the ICP, or the
positioning. CareGist has no paying customers or case studies yet. Willingness
to pay must be demonstrated through the controlled pilot described below.

---

## 2. The company strategy in one sentence

CareGist helps compliance and quality-improvement firms see verified CQC changes
in their market, understand the supporting evidence, and act through a repeatable
workflow—without asking them to trust an unsupported prediction or maintain a
monitoring pipeline themselves.

CareGist sells **traceable decisions and workflow-ready signals**, not access to
a provider directory or a repackaged public dataset.

---

## 3. Starting position and asymmetric advantage

CareGist begins with zero customers, no borrowed brand trust, and a strong free
alternative. CQC publishes an API, directory files, ratings, and reports under
the Open Government Licence. A buyer can obtain raw facts without CareGist.

The company therefore cannot justify its price through data access alone. It
must demonstrate value through:

- continuous monitoring across approved CQC sources;
- stable entity identity and deterministic change history;
- source-dated evidence a sceptical buyer can verify independently;
- relevance to a buyer's region, service types, and provider lists;
- delivery into a saved, repeatable workflow;
- measured operational outcomes, not invented revenue claims.

Being small becomes an advantage when every claim shows its work. CareGist does
not ask a prospect to trust its brand; it lets the prospect verify each signal
against the official source.

---

## 4. Launch ICP decision

### Primary launch ICP

**Compliance and quality-improvement firms serving CQC-regulated providers.**

This is locked for the first controlled cohort because these firms:

- already monitor registrations, ratings, inspections, and remediation needs;
- value evidence traceability more than a generic contact database;
- can apply a rating or registration event without CareGist inferring a vacancy,
  closure, distress event, or guaranteed sales opportunity;
- can recover £299 from one typical engagement if the signal contributes to a
  qualified conversation;
- fit the launch signals—`new_registration` and `rating_changed`—without
  requiring named-contact enrichment or predictive modelling;
- have shorter procurement paths than insurers, lenders, commissioners, and
  regulated enterprise buyers.

### What remains unproven

Compliance-first is an execution choice, not a factual claim about lifetime
value or conversion. It must be reviewed after the first ten qualified proofs.
The review compares activation, relevance, conversion, sales-cycle length, and
retention intent—not opinions about which segment sounds most exciting.

### Deferred segments

Recruiters, training providers, suppliers, property specialists, franchisors,
investors, insurers, lenders, and commissioners remain valid research segments.
They are not the first outbound cohort.

- Recruitment and supplier use cases risk pulling the product back towards
  commodity lead-list positioning and contact enrichment.
- Insurers, lenders, local authorities, and commissioners require procurement,
  security, data-processing, and contractual maturity CareGist has not yet earned.
- Property, ownership, group-expansion, and territory-density use cases need
  additional verified signal types or entity relationships.

These segments may be reopened through an explicitly approved experiment after
the compliance cohort produces evidence.

---

## 5. Locked catalogue `2026-08`

| Product | Price | Intended buyer/use | Included commercial boundary |
|---|---:|---|---|
| Free Directory | Free | Provider discovery and trust acquisition | Search, profiles, source dates, official links, free correction/claim request; no Radar workspace or API |
| Radar Regional | £299/month | Compliance firms covering one England region | 2 users, new registrations, rating changes, email/in-app delivery, 10 saved views, 90-day event export; no API, webhooks, extra seats, or cross-region access |
| Radar National | £799/month | National compliance and business-development teams | 5 users, all England, 50 saved views/provider lists, 365-day event export, onboarding; no API or webhooks |
| Intelligence Feed Pilot | From £6,000/year | Customers integrating one scoped signal into an operational system | One region and one signal at base scope, canonical API, signed webhooks, cursors, replay, delivery health; private and sales-assisted |
| Embedded Enterprise | Annual quote | White-label, customer-owned provider lists, or regulated enterprise use | Custom scope, procurement/security/data-processing review, contracted SLA and support; quote and invoice only |

Radar Regional and Radar National do not include an API. Additional seats are
not sold separately at launch. Customers upgrade or request an enterprise scope.

The **Change Ledger** is a shared Radar and enterprise capability. Opportunity
Briefs are role-specific delivery templates, not independent products.

### Explicitly removed from sale

- Full Dataset and regional/static data packs
- Data Starter, Data Pro, and Data Business
- Alerts Pro
- Provider Pro Listing and Sponsored Listing
- Extra Seat
- Premium Compliance Suite
- quarterly or annual snapshot/update products
- predictive, vacancy, distress, closure, or unsupported opportunity scores

Existing historical entitlements may remain in compatibility code. They must
never reappear as a public offer.

### Pricing interpretation

£299 is the list price being tested, not an instruction to demand blind payment
from an unknown prospect. CareGist will reduce purchase risk through proof, not
through a permanent £49 or £99 commodity tier.

---

## 6. Proof-to-paid commercial motion

### Decision

Do not launch Radar as cold self-serve checkout. Run a qualified, founder-led
evaluation called **Radar Proof** before asking for £299.

Radar Proof is a sales motion—not a product, free tier, Stripe price, or promise
of indefinite access.

### Radar Proof scope

- 21 days, no payment card, no automatic conversion.
- One compliance or quality-improvement firm.
- One England region, one user, and one documented job to be done.
- A day-one evidence pack covering up to 90 days of available canonical history.
- Live `new_registration` and `rating_changed` events during the proof.
- Evidence links, stable CQC location IDs, source dates, and observed timestamps.
- In-app and/or manually controlled email delivery.
- No API, webhook, bulk provider dataset, predictive score, or named-manager signal.
- A scheduled value review and explicit decision at the end.

The historical pack prevents a quiet market from making the trial appear empty.
It does not imply that a minimum number of future events is guaranteed.

### Qualification requirements

A prospect enters Radar Proof only when it:

- serves CQC-regulated providers in a defined England region;
- names the service types or provider list it cares about;
- identifies the user who currently monitors CQC changes;
- agrees to record saved, dismissed, contacted, meeting-booked, won, and
  not-relevant outcomes where applicable;
- attends onboarding and the end-of-proof value review;
- has a plausible budget for £299 if value is demonstrated.

Unqualified visitors use the Free Directory and public sample evidence.

### What the value review must show

The review reports observed facts:

- number of events in scope;
- number and percentage considered relevant;
- time to first relevant historical signal;
- opened, saved, dismissed, or requested-detail actions;
- customer-reported contacts, meetings, engagements, and not-relevant outcomes;
- customer-estimated manual research time avoided;
- delivery and source health during the proof.

CareGist must not convert these into invented revenue, guaranteed ROI, or causal
claims. Break-even uses the customer's own engagement value and assumptions.

### Price-validation threshold

Run ten qualified Radar Proofs before enabling broad self-serve acquisition.
The initial validation target is:

- at least 8 complete onboarding;
- at least 6 confirm genuinely relevant signals;
- at least 5 take an observable workflow action;
- at least 3 explicitly convert at £299/month;
- at least 2 permit a publishable, evidence-based case study.

If usage is weak, fix relevance and workflow before changing price. If usage is
strong but price is the consistent, evidenced loss reason, the founder may
approve a separate pricing experiment and new catalogue version. Sales must not
invent discounts or replacement SKUs during the cohort.

---

## 7. Positioning and messaging sequence

### Market category

The long-term category is **CQC signal intelligence**. The first sale should not
depend on a stranger accepting that category claim.

### First-touch message

Lead with a specific, checkable result:

> See what changed in your region before you subscribe.

Supporting message:

> CareGist builds a source-linked record of recent CQC registrations and rating
> changes in your market, then runs the same monitoring live for 21 days. Continue
> at £299 only if the evidence proves useful to your workflow.

### Positioning statement

For compliance and quality-improvement firms that need to know when a regulated
care market changes, CareGist Radar is an evidence-linked CQC monitoring workflow
that turns source events into traceable, prioritised account review. Unlike
manual CQC checks, static exports, or generic provider databases, every event is
stable, source-dated, explainable, and measured through the customer's outcome.

### Proof hierarchy

1. Official CQC source link and immutable source metadata
2. Stable event/entity identity and change history
3. Public sample event or territory evidence pack
4. Measured customer actions and relevance
5. Named case study
6. Broader category and ROI claims

No higher layer substitutes for a missing lower layer.

---

## 8. Product promises and non-promises

### Launch signals

- `new_registration`
- `rating_changed`

Each event must preserve entity level. A location or service event must not be
presented as a provider- or group-level conclusion without corroborating evidence.

Every canonical event records source publication/check/observation timestamps,
source URL, licence, snapshot checksum, evidence, and explanation status.

### Raw-event guarantee

If report retrieval, evidence extraction, explanation generation, or evaluation
fails, the verified raw event may still ship. A failed narrative must never delay
or contaminate the factual event.

### Claims that are not launch-ready

- predicted rating changes, closure, expansion, distress, or opportunity scores;
- leadership turnover or staffing need;
- manager absence described as a vacancy;
- deregistration described as a closure or vacant property;
- rating movement described as proof of a commercial need;
- group expansion without stable provider relationships;
- a delivery-time promise before measured production evidence exists.

---

## 9. Claim and capability gates

| Capability or claim | Current status | Evidence required before use |
|---|---|---|
| New-registration raw event | Private-pilot scope after source trust | Stable CQC ID, source snapshot, deterministic event, Gate 1 source checks |
| Rating-change raw event | Private-pilot scope after source trust | Direct CQC evidence, correct entity level, deterministic replay |
| Evidence-grounded narrative | Disabled | 100-report gold set; 100% factual citation coverage; zero unsupported factual claims; fact/interpretation separation; hostile-report safety; human approval |
| “Target delivery within 90 minutes” | Not marketable | Seven-day shadow run, ≥99% scheduled poll completion, 24-hour rolling sweep, p95 source-to-ledger ≤45 minutes for fast signals, and Gate 3 p95 source-to-customer <90 minutes |
| Named-manager change | Excluded | Separate DPIA and lawful-basis decision, data-minimisation design, approval, and dedicated tests |
| Manager absence | Later privacy-reviewed beta at most | Use only the public absence date; never label it a vacancy; separate approval |
| Predictive scores | Gated R&D | Historical backtesting, calibration, DPIA review, documented thresholds, and explicit approval |
| Provider-group expansion | Later work | Stable and corroborated provider relationships; entity-level accuracy tests |
| Deregistration/archived signal | Later work | Source-faithful language; no closure, vacancy, or property inference |
| Intelligence Feed | Gate 4 pilot | Replay, signature rotation, idempotency, delivery SLO, restore drills, security/DPA/SLA material |
| Embedded Enterprise | Quote-only, not launch-ready | Contracted scope, procurement/security review, DPA, SLA, support, and restore evidence |

Explanation publication, source collectors, outbound delivery, and checkout have
independent kill switches. A healthy system must measure polling, source
watermark, reconciliation, and delivery backlog separately. A quiet market must
not be treated as a stale source.

---

## 10. Release sequence

### Gate 0 — catalogue safety

**Decision:** deploy a narrow catalogue-safety release now; do not deploy the
full Radar platform.

The live pricing page was verified on 9 August 2026 and still advertised the
archived Alerts/Data/Listing catalogue. Vercel returned a fresh, non-cached
response, so this is an outdated deployment rather than a browser-cache issue.

The narrow release includes:

- corrected pricing, homepage, navigation, and product positioning;
- removal or retirement of legacy product and paid-listing journeys;
- Full Dataset redirect to Intelligence Feed;
- Free Directory claims/corrections preserved;
- OGL attribution and independence statement;
- checkout visibly and technically disabled.

It excludes:

- migration `049_cqc_signal_intelligence.sql`;
- new collectors, Radar backend, outbound delivery, or explanations;
- unapproved Terms/Privacy drafts;
- Payment Links or checkout activation;
- production database or customer changes.

### Gate 1 — source trust

- Deploy fast source collectors and rolling reconciliation in shadow mode.
- Run for seven consecutive measured days.
- Require ≥99% scheduled poll completion, 24-hour rolling sweep, passing count,
  checksum, and reconciliation gates, and p95 fast-signal source-to-ledger
  latency ≤45 minutes.

### Gate 2 — private compliance pilot

- Deploy organization tenancy, Radar UI, Change Ledger, saved views, and lists.
- Admit 3–5 design partners initially; expand to ten proofs for pricing validation.
- Review at least 20 events end to end.
- Keep automatic narratives disabled; use raw events or manually reviewed
  structured findings.

### Gate 3 — paid Radar

- Pass the 100-report narrative evaluation before automatic publication.
- Pass Stripe Checkout, Portal, webhook idempotency, cancellation, refund, and
  fail-closed lifecycle tests.
- Demonstrate p95 source-to-customer latency below 90 minutes.
- Enable Regional and National one account at a time after legal approval.

### Gate 4 — Intelligence Feed and Embedded

- Release scoped API, signed webhooks, replay, cursors, dead-letter handling,
  and customer-visible delivery health.
- Complete security, data-processing, SLA, and restore materials.
- Onboard the first £6,000 annual Feed pilot.
- Keep Embedded Enterprise quote-only.

---

## 11. Founder-led go-to-market runbook

### Targeting

Build a list of 20 A-fit compliance/quality-improvement firms. Re-qualify every
lead against the current catalogue. Historical July CSVs must not be used for
outreach without re-qualification.

### Sales sequence

1. Research the firm's territory, service focus, and current monitoring method.
2. Send one relevant, source-linked event or territory observation—not a generic
   product pitch.
3. Run a 30-minute discovery and evidence demonstration.
4. Agree the Radar Proof scope and success question.
5. Deliver the 90-day historical evidence pack and 21-day live proof.
6. Hold the value review using measured outcomes.
7. Ask for an explicit £299 conversion, a loss reason, or permission for a case
   study. Do not leave the outcome ambiguous.

### Required sales assets

- one real sample event for each launch signal;
- a one-region, 90-day sample evidence pack;
- a “CQC alone versus Radar workflow” comparison;
- source methodology and current data-status page;
- a 30-minute demo script;
- a customer-input ROI/break-even worksheet;
- an end-of-proof value report;
- an objection and loss-reason register.

### What not to do

- Do not run broad paid acquisition before conversion evidence exists.
- Do not sell a subscription from a static pricing grid alone.
- Do not revive a cheap data pack to manufacture early revenue.
- Do not lead with “AI,” prediction, opportunity scores, or unsupported urgency.
- Do not target every use case simultaneously.
- Do not call an event a lead unless the customer makes that judgement.

---

## 12. Metrics and decision rules

### Commercial

- qualified prospects contacted;
- discovery acceptance rate;
- proof onboarding completion;
- time to first relevant signal;
- relevant-event percentage;
- proof-to-paid conversion at £299;
- stated loss reason;
- sales-cycle length;
- case-study permission;
- retention intent after the first paid month.

### Product

- poll completion and source-watermark health;
- p50/p95 source-to-ledger latency;
- reconciliation and checksum status;
- event replay determinism;
- duplicate-event rate;
- opened, saved, dismissed, exported, and requested-detail actions;
- contacted, meeting-booked, engagement-won, and not-relevant outcomes;
- explanation citation coverage and unsupported-claim rate;
- delivery retry, dead-letter, and replay health.

### Decision rules

- Strong relevance + strong conversion: retain £299 and proceed account by account.
- Strong relevance + repeated price objection: conduct a controlled pricing
  review; do not silently discount.
- Weak relevance: improve scope, matching, and workflow before changing price.
- Delivery or source instability: stop onboarding and keep checkout disabled.
- Unsupported narrative: disable explanations; continue verified raw events.
- Tenant isolation failure: stop the pilot immediately.

---

## 13. Current implementation and release state

As of 9 August 2026:

- The Stripe test and live catalogues contain the four final paid/quote surfaces;
  nine legacy live products and their prices are archived.
- Checkout remains disabled.
- The repository contains additive tenancy, event-ledger, Radar, collector,
  health-gate, and durable-delivery implementation.
- Python 3.12 validation passes; Ruff passes; 545 backend tests pass.
- 102 frontend tests, TypeScript, and the Next.js 16.2.12 production build pass.
- Migration 049 has not been applied to production.
- The corrected website is not deployed; the live pricing page remains legacy.
- Legal approval, production shadow evidence, private-pilot evidence, the
  narrative gold set, and Feed/Embedded operational evidence remain open gates.

Software completion must not be reported as market validation or release approval.

---

## 14. Governance and version control

### One-change rule

Any change to product name, price, interval, seats, API boundary, launch ICP,
signal status, or public claim must update, in one reviewed change:

1. this master strategy;
2. the Stripe manifest when commercial objects change;
3. the governance gate record;
4. website/product configuration;
5. billing and entitlement tests;
6. sales collateral and lead qualification guidance.

If all six cannot move together, the change remains a proposal.

### Supersession labels

Older documents remain available for audit, but must carry or inherit a clear
superseded/research-only label. Copying an old product ladder into a new deck,
site, task, or Stripe object is a release defect.

### Human approvals

The following cannot be satisfied by code:

- solicitor/founder approval of Terms, Privacy, and checkout wording;
- approval of the 100-report narrative evaluation;
- approval of each controlled paid account;
- Feed/Embedded contract, security, DPA, SLA, and support scope;
- named-manager DPIA and lawful-basis decision;
- any new catalogue version or pricing experiment.

---

## 15. Final strategic rule

Do not ask the market to believe a grand category claim from an unknown company.
Show one relevant, source-linked fact in the buyer's own territory; prove that
CareGist can repeat the result safely; measure what the buyer did with it; and
only then ask for £299.
