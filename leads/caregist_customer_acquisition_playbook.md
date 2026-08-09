# CareGist — Caller-Ready Supply and Demand Prospecting Playbook

**Prepared:** 29 July 2026  
**Purpose:** Turn 100 supply-side and 100 demand-side public-source prospects into organised, warmer call queues without mass spam or unapproved outreach.

> **Operational status: PREPARATION ONLY / LIVE OUTREACH ON HOLD.** The repository does not contain the required `company-os/role-registry.yaml`, approval register, risk register, or a verified UK Country Pack. The enrichment is safe research and caller preparation. Do not dial, email, upload to a sender, publish, spend, or share lead samples until the missing governance and channel controls are verified and the applicable human approval is recorded.

## Task brief

- **Project / Country Pack in force:** CareGist / UK; required Country Pack not found or verified.
- **Objective:** Enrich both prospect lists, group them by location and type, and make every row easier for a caller to action.
- **Audience:** Henry or an authorised VA/founder-led caller.
- **Deliverable and format:** Two enriched CSV call queues plus this operating playbook.
- **Constraints:** Zero spend; public-source business research only; no live outreach or publication; no CQC endorsement claims; no guaranteed enquiries or revenue; current pricing must be checked before it is quoted.
- **Acceptance criteria:** 100 rows remain in each CSV; every row has a priority, queue, warm trigger, tailored opener, discovery prompt, objection response, next action, verification status, and hold status; queues are sortable by location and type.
- **No-touch boundaries:** No prospect contact, sender activation, CRM upload, deployment, pricing change, contract, secret access, or new private-data enrichment.
- **Deadline:** Current working session.
- **Reviewer:** Independent QA / Red Team; human review for governance and live outreach.

## What changed in the lead files

### Supply CSV

`caregist_supply_prospects_100.csv` retains all original fields and adds:

- `location_group`, `service_group`, and `organisation_group`
- `caller_contact_route`, `caller_priority`, `call_queue`, and `queue_order`
- `call_reason`, `warm_angle`, and `caller_goal`
- `tailored_opener`, `discovery_question`, `likely_objection`, and `caller_response`
- `next_best_action`, `verification_status`, and `caller_hold`

### Demand CSV

`caregist_demand_prospects_100.csv` retains all original fields and adds:

- `type_group`, `contact_location_signal`, and `coverage_to_confirm`
- `recommended_plan_status`, which marks every inherited plan recommendation as either legacy/do-not-quote or verify-before-quoting
- `caller_priority`, `call_queue`, and `queue_order`
- `sample_provider_type` and `recommended_sample_location`
- `warm_trigger`, `ten_lead_sample_brief`, and `tailored_opener`
- `discovery_question`, `likely_objection`, and `caller_response`
- `next_best_action`, `commercial_route`, `verification_status`, and `caller_hold`

A phone-area signal is only a routing clue. It is **not** evidence of headquarters, operating territory, or national coverage.

## Start here: the caller’s 90-second row workflow

1. **Stop if `caller_hold` is unresolved.** Confirm the verified UK Country Pack, suppression process, applicable TPS/CTPS screening, channel rules, and outreach approval.
2. **Open one queue, not the whole list.** Sort `call_queue`, then `queue_order`.
3. **Verify the row on the day.** Open the CQC/source link and website/contact page; confirm the organisation, public business number, current buyer/manager route, and any CareGist profile.
4. **Write one proof point.** Supply: one specific profile gap. Demand: one relevant provider type and sample territory.
5. **Use the tailored opener as a scaffold.** Do not read it mechanically or imply that CareGist is CQC.
6. **Ask the discovery question and listen.** Do not pitch a paid plan before need, territory, ownership, and permission are clear.
7. **Take one next action only.** Supply: permission to send a verified free-claim/profile-check route. Demand: permission to prepare or send a verified 10-lead sample.
8. **Log the outcome immediately.** Include opt-out/suppression before moving to the next row.

## Supply-side call queues

### Group first by location

The supplied list currently groups as follows:

| Location group | Prospects | Caller use |
|---|---:|---|
| London | 17 | Run community and residential queues separately; confirm borough/service area. |
| South East | 17 | Split community providers from residential homes; use county/local-authority language. |
| West Midlands | 14 | Prioritise Birmingham/Warwickshire clusters and no-website independents. |
| East | 12 | Confirm the actual local-authority coverage before describing the territory. |
| North West | 12 | Separate independent community services from group/multi-location operators. |
| East Midlands | 10 | Handle the four Knights Care records as one group conversation, not four cold calls. |
| Yorkshire & Humberside | 9 | Separate community, residential, and franchise/group routes. |
| South West | 5 | Use local-authority-specific profile checks; do not assume wider regional coverage. |
| North East | 3 | Small, focused batch; verify location because company and service geography may differ. |
| Region unclassified — verify | 1 | Resolve the missing region before contact. |

### Then group by service and organisation type

| Service group | Prospects | Primary need hypothesis | First call goal |
|---|---:|---|---|
| Home care / community support | 64 | Accurate local coverage, services and contact route in public search | Confirm operating areas and win permission to send a free profile check |
| Residential care | 35 | Clear admissions/service information before first inspection and enquiry cycle | Confirm admissions/profile owner and one visible listing gap |
| General social care — verify service model | 1 | Service model is not specific enough in the supplied snapshot | Confirm service type before tailoring any message |

| Organisation group | Caller treatment |
|---|---|
| Independent — no website recorded | **A1.** Highest-friction public-presence gap; free accuracy/claim conversation only. |
| Independent — website present | **A2.** Compare CareGist listing with the website and name one inconsistency or missing field. |
| Group / franchise / partnership | **B1/B2.** Identify central versus local ownership; avoid duplicate calls. |
| Enterprise / multi-location | **C1.** One head-office profile audit; never approach every location as unrelated. |

### Supply opener structure

> Hello, may I speak with **the registered manager or the person responsible for your public profile**? I’m Henry from **CareGist, an independent care directory using public CQC information**. I’m checking the profile for **[provider]** after its **[registration date]** registration. **This is not a call from CQC.** Is now a bad time for a 60-second accuracy check?

Start role-first. The supplied manager name remains source evidence, not a default personalisation token; use it only if necessary, same-day verified, and permitted by the approved outreach controls.

Then use the row’s `warm_angle` and ask its `discovery_question`.

### Supply micro-plays

**Independent, no website recorded**

- Warm point: “The source snapshot does not show a website, so the public profile may be the quickest place to confirm services and contact details.”
- Ask: “Which local areas and care types are you ready to accept enquiries for?”
- Close: “May I verify the listing and send the free claim/profile-check route?”

**Independent, website present**

- Warm point: name one mismatch or missing field only after checking the live pages.
- Ask: “Who keeps your website and public directory details accurate?”
- Objection: “We already have a website.”
- Response: “That helps; the aim is to make the independent listing consistent with it, not replace it.”

**Group, franchise, or multi-location**

- Warm point: avoid inconsistent or duplicate location records.
- Ask: “Are public profiles managed centrally or by each location?”
- Close: request the central owner and permission for one group-level audit.
- Do not quote bespoke group terms; that requires a scoped commercial decision.

## Demand-side call queues

### Type groups

| Type group | Prospects | Registration-trigger hypothesis | Sample type |
|---|---:|---|---|
| Recruitment & workforce | 20 | New services may need managers and frontline staff | All provider types |
| Compliance & professional services | 16 | Registration can trigger policy, audit and inspection-readiness work | All provider types |
| Training & learning | 15 | New teams need induction, Care Certificate and mandatory learning | All provider types |
| CareTech & software | 11 | Providers may select systems before workflows become embedded | Match home-care or all-provider fit |
| Furniture & care equipment | 9 | New residential settings may need opening/refurbishment packages | Residential care |
| Facilities, laundry & hygiene | 9 | New sites can create installation and recurring-service demand | Residential care |
| Nurse-call, monitoring & safety | 8 | Residential settings may require safety and call-system projects | Residential care |
| Supplies & procurement | 7 | Opening stock and recurring consumables can be early needs | Residential care |
| Pharmacy services | 3 | New residential providers may need medicines-service onboarding | Residential care |
| Care-sector marketing | 2 | New community providers may need first-enquiry visibility | Home care / community support |

### Location treatment for demand prospects

The supplied demand list does not reliably evidence headquarters or sales coverage. The enriched file therefore keeps location honest in two ways:

1. `contact_location_signal` uses a public phone-area clue only where available and explicitly says to verify it.
2. `recommended_sample_location` selects the strongest matching region in the current 100-provider supply snapshot:
   - **London** for community/all-provider samples.
   - **East Midlands** for residential-focused samples.

These are starting sample territories, not claims about a demand prospect’s coverage. The caller must ask which UK nations, regions, local authorities and provider types the buyer actually serves.

### Demand opener structure

> Hello, could you point me to **[recommended buyer]** or whoever owns care-sector new business? I’m Henry from CareGist. We track **public CQC registration signals**. For **[company]**, I prepared a draft sample focused on **[provider type]** in **[sample location]**, where a new registration can signal **[segment-specific need]**. May I ask two questions to check whether the sample fits before I send anything?

### Segment-specific discovery prompts

- **Recruitment:** “Which roles, provider types and branch territories produce worthwhile accounts?”
- **Training:** “Do you sell per learner, per organisation or enterprise-wide, and which new-provider stage converts best?”
- **CareTech:** “Do you focus on home care, residential care or both, and when does sales want to reach a newly registered provider?”
- **Compliance/consultancy:** “Is your strongest trigger pre-registration, newly registered, pre-inspection or after a rating issue?”
- **Furniture/equipment/nurse-call/facilities:** “Which setting types, project sizes and installation territories can your team service?”
- **Supplies/pharmacy:** “Which provider types and delivery territories fit your recurring-account model?”
- **Marketing:** “Which provider type and local market is commercially viable for your service?”

### Demand sample rule

A 10-lead sample should contain only:

- provider/company name;
- public CQC provider/source link;
- registration date and service type;
- public business contact details that were re-verified that day;
- territory/context relevant to the buyer;
- a clear note that CareGist is independent of CQC.

Do not add private personal data, infer buying intent, label a prospect “hot,” or claim the provider needs the buyer’s product. A registration is a **timing signal and hypothesis**, not consent or proof of demand.

### Common demand objection

**“We already buy or build lead lists.”**

> Understood. The useful comparison is freshness and fit. I can show ten public-source registration signals in your chosen territory, and you can judge whether any are genuinely new to your workflow.

Then ask what “new,” “qualified,” and “usable” mean to their team. Do not argue about quality before they define it.

## Priority and daily batching

### Priority codes

**Supply queues**

- **A1:** Independent provider with no website recorded in the supplied source.
- **A2:** Independent provider with a website present.
- **B1:** Group, franchise or partnership with a website/contact route present.
- **B2:** Group, franchise or partnership whose central route needs research.
- **C1:** Enterprise or multi-location lead requiring one head-office conversation. Supply does not use C2.

**Demand queues**

- **A1/A2:** Fit score 92+; A1 has a direct public contact route and A2 needs routing verification.
- **B1/B2:** Fit score 88–91; B1 has a direct public route and B2 needs routing verification.
- **C1/C2:** Fit score below 88; C1 has a direct public route and C2 needs routing verification.

### Suggested first working block after the hold is cleared

1. Pick **one location + one type**, for example `South East | Home care / community support | A1`.
2. Verify no more than ten rows.
3. Call the verified rows while the evidence is fresh.
4. Stop and review outcomes before preparing the next batch.
5. For demand, prepare a sample only after the buyer confirms territory and type.

This keeps feedback tight and avoids scaling an unproven script.

## Ten-working-day permission-led cadence

| Day | Supply | Demand |
|---|---|---|
| 0 | Verify source, live profile, phone, suppression and channel controls | Verify website/contact route, buyer, suppression and coverage hypothesis |
| 1 | Call for permission to send the free profile/claim check | Call to qualify territory/type and ask permission for a sample |
| 1 | Send only the promised verified link | Send only the promised verified sample or confirmation |
| 3 | One concrete profile gap; no generic chase | One relevant registration example; ask if sample fit is right |
| 6 | Offer help completing the free claim | Offer a 15-minute sample review |
| 10 | “Shall I close this for now?” | “Keep, change territory/type, or close?” |

Stop immediately after an opt-out, clear rejection, wrong party with no referral, or compliance uncertainty.

## Caller outcome codes

Use a controlled outcome rather than free-text alone:

- `NOT_DIALLED_HOLD`
- `SOURCE_REVERIFY_FAILED`
- `NO_ANSWER`
- `GATEKEEPER_CALLBACK`
- `WRONG_PARTY_REFERRED`
- `QUALIFIED_PERMISSION_GRANTED`
- `LINK_OR_SAMPLE_SENT`
- `FOLLOW_UP_BOOKED`
- `NOT_NOW`
- `NO_FIT`
- `OPT_OUT_SUPPRESSED`
- `COMPLIANCE_ESCALATION`

## Operational tracking fields

Keep outreach state in a controlled CRM/ledger, not by overwriting source evidence:

- owner and queue ID;
- source verification date and verifier;
- lawful-purpose/basis review reference and Country Pack version;
- TPS/CTPS or other applicable screening date/result;
- suppression/opt-out status and timestamp;
- first contact date, channel and caller;
- outcome code and notes;
- permission scope: profile link, sample, callback, or none;
- promised territory/provider type;
- next action date;
- free claim started, demo booked, trial started, paid customer;
- retention/review date.

The files contain **prospects, not customers**. Do not change status to customer until a real contract/payment state supports it.

## Compliance and quality guardrails

- Public availability does not remove data-protection or direct-marketing obligations, particularly where a named manager is involved.
- Use public business contact details only; do not enrich with private personal data.
- The live campaign must follow the verified UK Country Pack, suppression rules, applicable TPS/CTPS screening, PECR/UK GDPR controls, and qualified advice where required.
- State that CareGist uses public CQC information and is independent of CQC.
- Do not imply CQC endorsement, guaranteed placement, guaranteed enquiries, buying intent, or guaranteed revenue.
- Keep the free-claim offer genuinely free.
- Re-verify websites, phones, source links, buyer roles and CareGist profiles immediately before contact or sample sharing.
- Record opt-outs once and suppress them across future campaigns and channels as required.
- Do not upload these lists to an automated sender or dialler without a separately approved, tested suppression and one-attempt workflow.

## Pricing guardrail

The demand CSV contains 76 rows labelled `Data Growth`, while the source playbook describes current plans as Data Starter, Data Pro and Data Business. Treat `Data Growth` as a **legacy/unverified label**. Do not quote it. To prevent the inherited column being mistaken for a price list, every row now has `recommended_plan_status`: the 76 legacy rows say `LEGACY_UNVERIFIED_DO_NOT_QUOTE`, and the other 24 say `INHERITED_RECOMMENDATION_VERIFY_CURRENT_PRICING_BEFORE_QUOTING`. The inherited rows also assign no prospect to Data Business, so the CSV is not evidence of a complete current plan-to-segment model. Confirm the current published plan name, price, VAT treatment and buyer fit immediately before any commercial conversation. Changing or standardising pricing requires the founder’s explicit approval.

## Source provenance and verification boundary

- Supply rows originate from repository snapshot `cqc_new_providers_2026.csv`, derived from public CQC registration data; each row includes a CQC source URL.
- Demand rows contain public company websites/contact routes and evidence URLs recorded in the supplied list.
- The earlier check of Jacklily Home Care Ltd showed why same-day verification is necessary: the CQC record existed, while a CareGist search did not establish a live profile.
- Enrichment fields are deterministic caller guidance derived from supplied columns. They are not evidence that a company is reachable, trading, within a territory, interested, compliant to contact, or ready to buy.

## Deliverable return

- **What was produced:** Two enriched 100-row caller queues and this expanded playbook.
- **Assumptions made:** The supplied public-source rows are research inputs; location and need statements are hypotheses until verified; no live outreach is authorised.
- **Known weaknesses / open questions:** Missing verified UK Country Pack and governance registers; demand HQ/coverage is mostly not evidenced; public contact routes can change; CareGist profile presence is not proven row-by-row; legacy `Data Growth` labels need commercial normalisation.
- **Compliance flags:** Live contact, sample sharing, sender upload and publication remain blocked pending governance, channel and human approvals.
- **Data/security impact:** Existing public-source data only; no private enrichment or external sharing performed.
- **Ready for independent QA:** Yes, for artifact/data-quality review only. Not ready for live outreach.
