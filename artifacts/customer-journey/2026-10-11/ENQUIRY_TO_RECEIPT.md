# CareGist: enquiry to confirmed product receipt

Prepared 11 October 2026 for Henry and Sibongile, with an invited **Principal Growth Product Manager subagent**. This is a role-based analytical review, not an external human appointment. Scope: the £745 Territory Opportunity Brief from actual enquiry receipt through usable customer access. No enquiry, payment or delivery was submitted during this assessment.

**Finding:** CareGist has a public enquiry-preparation route and local fulfilment components. A complete, staffed enquiry-to-customer-receipt service remains unverified. The largest journey risks are unowned waiting, scope changes between stages, an ambiguous delivery clock and treating a prepared/sent pack as customer receipt. Faster generation alone will not resolve them.

**Recommendation:** establish one accountable concierge journey now, preserving one accepted scope and showing the customer the next action and date at every handoff. Prove it with a timed, authorised synthetic rehearsal before taking paid orders. Add structured intake once it can preserve the same controls and confirm actual receipt; retain independent review and release approval.

## 1. What was observed, and what remains an assumption

Fresh public reads saved alongside this report in health-public.json, territory-public.json and terms-public.json. Each file contains its own UTC capture time.

| Evidence | What it establishes | What it cannot establish |
|---|---|---|
| Current public Territory Brief page | £745 fixed fee, “No VAT added”; online ordering unavailable; coverage followed by scope email; delivery target after scope/source checks | A submitted/received enquiry, staffed mailbox, accepted order, merchant settlement or delivered pack |
| Current public terms | Written scope identifies buyer/factual criteria; scope and source checked before payment link/payment; full payment before work; three-working-day target after scope/source confirmation | Operational timing, legal approval of a different route, or an automatic delivery date reset after payment |
| Current public health | checkoutReady=false, shadowCoveragePassed=false, deliveryEnabled=false; reported release 0fda3cac8b670ed3dddb31ac3c45644ca430e387 | Permission to charge/send manually or proof of completed customer delivery |
| Local picker at c17d1df | Prefilled mailto, copy fallback and click event named territory_scope_request | Whether the buyer sends the email or it arrives in CareGist's inbox |
| Local generator/fulfilment/download code | Scope processing, generation/upload, entitlement and queue components | Deployed implementation contents or an independently approved pack actually retrieved by the buyer |
| 9 October buying audit | Historical browser and local/synthetic journey checks, with explicit external-service/staff gaps | Current completed staff/payment/inbox/private-file receipts |
| 11 October runbook/blueprint | Proposed owners, eight-hour labour model, 25 operator hours/week and required receipts | Staff access/capacity, measured service durations, conversion rates or gate approvals |

No enquiry cohort with real received/acknowledged/paid/access timestamps was supplied or inspected. Therefore actual median/p90 time, stage abandonment and customer satisfaction are **unknown**, not zero. This report separates observed capability from proposed service targets.

## 2. Define the beginning and end properly

**Beginning, T0:** a legitimate buyer enquiry actually reaches the monitored inbox or a durable accepted intake record. Retain its original content and received timestamp, assign an enquiry ID and owner. A scope-check result, CTA click, copied message or opened email composer precedes T0; none is a received enquiry.

**End, Taccess:** the agreed recipient confirms that the required PDF, CSV and attribution/source manifest are accessible and openable. Keep supporting access evidence where the approved route provides it. A redirect or token consumption is weaker than successful file retrieval; a download does not by itself establish comprehension or acceptance.

Measure product acceptance and usefulness separately: “I can open the files” is receipt; “the files meet the agreed scope” is acceptance; “we used the pack to prioritise these accounts” is an outcome. Neither silence nor an email tracking pixel establishes acceptance.

```mermaid
flowchart LR
    A[Received enquiry] --> B[Qualification]
    B --> C[Scope and source feasibility]
    C --> D[Written scope accepted]
    D --> E[Payment verified]
    E --> F[Production]
    F --> G[Independent review]
    G --> H[Approved release]
    H --> I[Customer access confirmed]
```

An unsupported scope exits before payment. A defect exits to a recovery case with owner/date; it cannot silently become a completed sale.

## 3. Stage-by-stage service design

The response times below are **proposed internal pilot targets**, not observed performance or new published promises. Henry must agree staffing and the relevant route before using them externally. Existing operative terms and individually accepted dates take precedence.

| Stage | Customer experience / question | CareGist action and owner | Proposed service control | Exit evidence |
|---|---|---|---|---|
| 1. Received enquiry | “Did you get my request?” | Sibongile records original message/scope, ID, owner and due action; backup covers absence | Check inbox at start/end of each working day; acknowledge by next working day | Received timestamp plus actual acknowledgement, reference and next step |
| 2. Qualification | “Can this help the decision I need to make?” | Sibongile asks for objective, deadline, supplier/service fit, exclusions and buying authority | Use prefilled scope; ask only missing questions. Offer a 15–20-minute call if needed; do not require one for a complete straightforward written enquiry | Buyer's own objective and qualification decision; unresolved questions identified |
| 3. Feasibility | “Will you deliver the number and type of organisations I need?” | Source/technical owner supports Sibongile; reviewer checks source/criteria; verify distinct provider IDs, evidence window and capacity | Target a suitability answer within one working day after complete inputs and available reviewer/source capacity; otherwise give reason and next-update date | Supported eligible set, shortlist quantity and edition; accept, explicit rescope or refuse |
| 4. Written agreement | “Exactly what am I buying, when will it arrive, and what if it fails?” | Sibongile drafts one version; Henry approves terms/price/exceptions; buyer accepts | One document states objective, criteria/exclusions, quantity, files, fee, source limitations, recipient, calendar target and remedy reference. Record scope version; avoid another round of retyping | Accepted version and timestamp, approved source check, reserved production/reviewer slots |
| 5. Payment | “Where do I pay, and did it work?” | Authorised merchant operator issues approved request; Sibongile reconciles authoritative merchant evidence | Send only after required scope/source/commercial checks. Include order reference, amount/currency and agreed date. Confirm verified payment by next working day; unresolved status means do not request duplicate payment | Payment/session ID, actual status, GBP amount/order/payer match; confirmation or exception case |
| 6. Production | “Is work underway, and will it arrive on time?” | Sibongile produces PDF/CSV/manifest from the frozen scope and approved source; records work start | Customer gets one payment/start update with agreed date and next contact. No need for daily routine messages if on track; material risk is raised before the agreed date | Exact draft inventory, source identifiers, scope version, hashes/time record |
| 7. Independent review | “Can I trust these entries?” | Named reviewer checks every shortlisted organisation, scope, source support, questions, rendered PDF, CSV and attribution; producer fixes defects | Reserve review slot before taking the order. Corrections are re-reviewed. No release to save time or meet a date | PASS on exact final files, reviewer identity/time and hashes; or open defects/revised-date process |
| 8. Release | “Where are my files and how do I use them?” | Authorised operator verifies agreed recipient and entitlement, then releases through approved route | Send only reviewed version. Include PDF, CSV, manifest, source edition, short use instructions, actual route-specific expiry/access terms, support/order reference | Final file inventory, recipient, send/route receipt and hash-to-review match |
| 9. Confirm receipt | “Can I actually open everything?” | Sibongile checks bounce/link/access failures and asks recipient to confirm usable files | Access check by next working day after release; respond to access problems by next working day and assign a resolution date. A fix deadline depends on the issue | Agreed recipient explicitly confirms PDF/CSV/manifest are accessible and openable. Successful retrieval is supporting evidence; without acknowledgement, confirmed usable receipt remains pending |

Every customer update should answer four questions: **what has happened, what happens next, who acts next, and by what date**. Internal gate/model/config names do not belong in customer-facing status text. Give a plain reason when blocked and an actual next-update date; do not conceal a material limitation behind “processing”.

## 4. The elapsed-time analysis

There are three separate clocks:

1. **Customer elapsed time:** Taccess − T0, including CareGist queues, weekends, customer replies/payment and recovery. Report both calendar elapsed time and working-day elapsed time.
2. **CareGist-controlled waiting:** received→acknowledged; complete inputs→suitability response; approved scope→payment request; paid→work start; draft→review; review PASS→release; reported access issue→resolution. Label intervals by blocker/owner and avoid double-counting overlapping intervals.
3. **Labour:** actual minutes worked by operator, reviewer, founder and engineering. Record this independently of elapsed time. Seven hours of work cannot be advertised as seven-hour delivery.

The runbook's **eight-hour planning model** includes one hour allocated acquisition, which precedes or spans the enquiry cohort. Removing that allocation leaves **seven direct service hours**: 0.75h triage/scoping + 2.50h research/qualification + 1.50h analysis/CSV/brief + 1.00h independent review + 0.25h payment/admin + 0.50h delivery/access + 0.50h corrections. That is roughly six operator/merchant hours and one separate reviewer hour, under the model; actual role splits and costs must be logged. It is an estimate, not measured throughput. The hybrid five-hour claim is also unmeasured and does not imply five hours from enquiry to receipt.

Sibongile has five hours/day across all enquiries, sales, production and recovery; the runbook's normal production block is 2.5h/day. Henry and reviewer availability are separate. A short call, a deferred merchant approval or a missed review slot can add a working day without adding much labour.

### The published delivery clock

Let **Tconfirm** be the later of written scope confirmation and source-path check. Published target: **Tconfirm + three English working days**. Payment is required before work, but it is not the stated start of that clock. Do not replace the current rule with “three days after payment” without a separately approved/accepted agreement.

When payment is late, obtain an explicit revised calendar date before starting. Record the original date, cause, revised proposal and buyer acceptance. A deadline remains unresolved until the buyer agrees or the operative remedy is followed. Source/gate readiness must hold at each relevant step; no example below authorises use of an old edition.

### Two illustrative timelines, not forecasts

These examples assume all required operating gates have passed, sufficient fresh source, complete scope and reserved capacity. They are not claims that these future dates will be operational.

| Event | Prompt, uncomplicated case | Slower case with late payment |
|---|---|---|
| Enquiry received | Monday 12 October | Monday 12 October |
| Acknowledgement / missing questions | Monday 12 October | Tuesday 13 October |
| Qualification | Monday/Tuesday 12–13 October | Wednesday 14 October |
| Written scope accepted and source checked | Tuesday 13 October | Thursday 15 October |
| Original three-working-day target | Friday 16 October | Tuesday 20 October |
| Verified payment | Tuesday 13 October | Friday 16 October |
| Date treatment | Existing target retained if capacity still supports it | Buyer explicitly agrees revised Wednesday 21 October target; it is not an automatic clock reset |
| Reviewed product released and usable receipt | Friday 16 October, if buyer opens/confirms that day | Wednesday 21 October release; Thursday 22 October access confirmation |
| End-to-end elapsed, measured at corresponding times of day | Four calendar days / four elapsed working days from Monday to Friday | Ten calendar days / eight elapsed working days from Monday to the following Thursday |

A proposed next-working-day access check can extend the first case's *confirmed* receipt to Monday 19 October if the buyer does not confirm on Friday. Never report the send date as the receipt date merely to improve a metric. An incomplete brief, unavailable source, unstaffed gate or buyer delay leaves completion time unbounded until resolved.

## 5. Principal growth risks and fixes

| Priority | Risk in the buyer journey | Recommendation | Acceptance check |
|---|---|---|---|
| P1 | Intent disappears between mailto and inbox; current click-event name resembles a received request | Define CTA click as intent only. Give every actually received enquiry an ID/owner/acknowledgement. Preserve a reliable fallback | Controlled rehearsal ties one real inbox receipt to one enquiry record; click alone never creates a received-enquiry metric |
| P1 | Buyer agrees one scope but coverage/generation/payment carry another | Freeze one accepted contract and eligible set; reuse supported generator fields; reject unmapped categories; keep distinct-provider count separate from location count | Planted multi-location/provider case and category/service/exclusion change produce correct set or rejection before charge |
| P1 | Waiting has no next action/date, undermining trust after £745 commitment | One operator owns the journey; reserve merchant/reviewer slots; use compact milestone updates with reference/date/support | Each rehearsal state has an owner, timestamp, blocker and next update; all paid commitments have reserved capacity |
| P1 | Three-day promise is read as enquiry-to-delivery or silently reset at payment | Display/agree a calendar target after suitability; track whole elapsed journey separately; re-agree late-payment dates | Timeline reconciles original and revised dates; no buyer-facing update silently changes the clock |
| P1 | Prepared/uploaded/queued state is called fulfilled while the buyer has nothing | Keep prepared, QA approved, released, access confirmed and accepted separate; independently review the exact files | Test shows no receipt metric from database fulfilled status, email provider acceptance, redirect or tracking pixel alone |
| P1 | Dormant automated code may skip the proposed human review/release stage | Local inspected fulfilment sequence generates/uploads, marks fulfilled, issues tokens and queues email; it has no explicit human-review pause in that inspected sequence. Keep it closed for this pilot pending proven approval control, or use a separately approved controlled route | Invalid/missing/revoked review receipt prevents release of the corresponding exact artifact version; corrected files require a new PASS. Recheck deployed code before alleging deployed behaviour |
| P2 | Qualification repeats questions already supplied and adds a compulsory scheduling delay | Async-first qualification for complete enquiries; short call for genuine ambiguity or value discovery | Buyer is asked only unresolved fields; measure interactions and time-to-qualified-decision without weakening scope checks |
| P2 | Delivered CSV/PDF creates another setup task before the buyer sees value | Supply short field mapping/use instructions, source limitations and a factual example of how to inspect a row | Rehearsal recipient opens PDF/CSV/manifest and understands the next investigative step without operator screen-sharing |

## 6. Which product approach fits the pilot?

| Approach | Advantages | Tradeoffs / readiness | Decision |
|---|---|---|---|
| Structured concierge using approved inbox and one restricted register | Fast to rehearse, supports bespoke judgement, uses existing roles/tools | Mailto remains external; intake needs real receipt monitoring; staff coverage and milestone communication must be disciplined | Recommended immediate operating design; no commercial activation until its receipts/gates pass |
| Durable structured web enquiry plus the same concierge back office | Can persist validated scope and return a true enquiry reference/confirmation; reduces lost intake and duplicate questions | Needs privacy/access controls, delivery of acknowledgements, replay/deduplication and clear failure recovery; form success must follow durable acceptance, not a failed backend write | Preferred next product increment once receipt handling is proven; first inspect/reuse existing intake capability before building another endpoint |
| Full self-serve checkout/fulfilment | Potential lower staff handoff burden at volume | Current checkout/delivery closed; bespoke suitability, mapping, review/release and external journey proofs unfinished | Defer; a faster checkout cannot make unsupported scope deliverable |

Do not make a customer-facing status portal the first build. A reference and reliable milestone updates can test its value at pilot volume. Preserve technical/source gates and approved communications while making operational ownership clearer.

## 7. Metrics that describe the actual journey

Use unique enquiry/order IDs and deduplicate replies/retries. Preserve separate buyer and order counts. For stage conversion, use mature linked cohorts and report still-pending cases separately rather than treating them as lost. No baseline or conversion uplift is established here.

| Metric | Definition | What to learn |
|---|---|---|
| Receipt→acknowledgement | actual acknowledgement timestamp − received timestamp | Is the queue staffed? Track next-working-day misses per enquiry, initially as raw counts |
| Time to suitability | qualified/feasibility decision timestamp − complete-input timestamp; also track whole time since receipt | Can the buyer get a timely yes/rescope/no without repeated questions? |
| Qualified enquiry→accepted scope | accepted scopes / suitably qualified enquiries in the same matured cohort | Is the offer appropriate? Retain refusals, missing information and open cases separately |
| Accepted scope→verified payment | matched paid orders / accepted scopes in linked matured cohort | Are payment instructions, authority, amount or dates obstructing purchase? |
| Payment→work start / review queue | separate timestamp intervals | Is merchant or reviewer availability adding avoidable idle days? |
| Enquiry→usable access | Taccess − T0; calendar and working time | Primary end-to-end service metric; not an email-send metric |
| Reviewed release→usable access | access timestamp − release timestamp; separate by required file | Are links, spam filtering or file usability obstructing delivery? |
| On-time release and on-time access | compare each timestamp separately with the agreed date and definition; retain original and revised dates | Prevent hiding slow access or repeated rescheduling behind an on-time-send statistic |
| Rework and recovery | affected orders, cause, actual labour and days unresolved | Are criteria, source, output or recipient controls failing? |
| Accepted/useful product | post-delivery buyer confirmation that files meet the accepted scope; later buyer-reported decision/action | Distinguish this from pre-purchase scope acceptance. Usable access is an early activation signal; a supported decision is stronger commercial evidence |

With two or three orders, list individual durations, objections and supported decisions. Do not use a p90 or percentage uplift as a robust conclusion from this sample. Any intake experiment must keep scope/readiness criteria identical; no randomised discount or gate relaxation is recommended.

## 8. The next single bounded step

**Run one timed, controlled enquiry-to-access rehearsal with a synthetic buyer through the proposed real operational tools.** Internal planning can start immediately. External inbox/merchant/storage actions require their explicitly authorised destinations and approved route; this review does not supply those permissions.

1. Name the operator, merchant owner, reviewer and backup; reserve slots; identify current source/readiness receipts.
2. Deliver an authorised synthetic enquiry and prove inbox receipt; preserve its selections without retyping. Retain actual timestamp/ID/acknowledgement.
3. Qualify once; verify distinct organisations and supported criteria; freeze scope/date/files/recipient; have the synthetic buyer accept the exact version.
4. Use the authorised merchant test route; reconcile payment/reference. Separately exercise unpaid/duplicate/wrong-amount evidence without starting production.
5. Produce full agreed-sized PDF/CSV/manifest from the approved rehearsal source, clearly labelled synthetic/rehearsal; time labour and queues. Reviewer checks every row and rendered file; corrected version receives a new verdict.
6. Release through the approved test route only after PASS; prove intended-recipient retrieval/opening of every required file and denial to a wrong recipient. Store receipts, not just a mocked send result.
7. Exercise a shortfall before payment, late-payment date re-agreement, reviewer delay, failed/bounced link and cancellation/refund replay. Record simulated versus actually exercised cases.
8. Publish elapsed timeline, actual role minutes, customer interactions, all blocked intervals and residual defects. Select the next fix from the longest avoidable delay or material defect; do not fund all automation at once.

**Document/rehearsal acceptance:** every stage has evidence, owner and next action; no scope loss or unsupported promise; no paid work without valid payment; no release without review; no receipt claim without usable access. Named independent production gates remain separate. One rehearsal is operational evidence, not demand validation or a statistically measured conversion lift.

## 9. Evidence, quality checks and scope of this analysis

| Assessment promise | Source of truth | Pass condition / limitation |
|---|---|---|
| Explain enquiry→receipt for Henry/Sibongile | Current public pages, local code, runbook/audit | Clear start/end, owners, handoffs, receipt evidence; unknown staff/external steps visible |
| Explain duration | Published terms, runbook assumptions, calendar arithmetic | Distinguish clocks, conditional examples and actual absent timing data; no new SLA |
| Invite principal growth perspective | Role-specific subagent review in PRINCIPAL_GROWTH_PM.md | Independent friction/option/metric challenge; role simulation disclosed |
| Recommend a bounded change | Evidence gaps and current gates | Timed rehearsal first, dependable intake/status next; no activation by this report |

Public response files provide new observation timestamps. The local code claim about no review pause is confined to the inspected fulfilment sequence at c17d1df; public release contents were not independently retrieved. Historical application-test claims are not treated as new test results. No customer data, cohort analytics, CRM account, merchant transaction, mailbox send or private-file delivery was exercised.

Sources: [30-day blueprint](../../blueprint-30-days/2026-10-11/BLUEPRINT.md), [manual runbook](../../strategy-review/2026-10-11/MANUAL_RUNBOOK.md), [operator record](../../strategy-review/2026-10-11/OPERATOR_RECORD.md), [9 October buying audit](../../buying-audit/2026-10-09/BUYING_PROCESS.md), [current Territory Brief page](https://caregist.co.uk/pricing/territory), [terms](https://caregist.co.uk/terms), [health](https://caregist.co.uk/api/v1/health). Local evidence: frontend/components/TerritoryScopePicker.tsx, api/services/territory_brief_fulfilment.py and frontend/lib/territory-brief-download.ts. This document does not modify the existing blueprint or code.
