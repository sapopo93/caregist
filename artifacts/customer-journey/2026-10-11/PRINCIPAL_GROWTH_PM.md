# CareGist enquiry-to-receipt review: Principal Growth Product Manager

Prepared 11 October 2026. Independent role-based analysis by an invited AI subagent; this is not a claim that an external human principal product manager has joined CareGist. Scope: the £745 Territory Opportunity Brief, from a genuine incoming enquiry to verified usable receipt. Weekly Digest is excluded because its separate terms and sequential delivery remain unverified.

**Recommendation:** run one instrumented concierge rehearsal before adding another buying surface. The largest risk to conversion is an interested buyer disappearing during an unowned wait, or paying for a scope that changes across handoffs. The growth outcome is a buyer receiving the agreed usable files and making a supported account-prioritisation decision. A checkout click, a generated PDF and an email marked sent are intermediate events.

## Evidence boundary

Read the 11 October blueprint and manual runbook/operator record/plan, the 9 October buying audit, and local picker, scope, checkout request, generator mapping, fulfilment and download-entitlement code at HEAD `c17d1df9b6214664d650274ac12e9f181fcf5ad7`. No live buyer, inbox, merchant, storage, download or status communication was exercised in this review. The blueprint's 11 October production observations are reported evidence, not newly verified here. Local code does not establish the deployed behaviour. No conversion baseline or measured processing-time distribution exists in the reviewed packet.

References:

- [Blueprint](../../blueprint-30-days/2026-10-11/BLUEPRINT.md), sections 2–8: dated readiness, scope contract, staffing, gates, technical queue and pilot sequence.
- [Manual runbook](../../strategy-review/2026-10-11/MANUAL_RUNBOOK.md): proposed staffed progression, eight-hour labour hypothesis and exception handling.
- [Operator record](../../strategy-review/2026-10-11/OPERATOR_RECORD.md): proposed restricted record and raw-count dashboard.
- [Plan](../../strategy-review/2026-10-11/PLAN.md): discovery-first strategy and capacity assumptions.
- [Buying audit](../../buying-audit/2026-10-09/BUYING_PROCESS.md): live discovery/enquiry initiation evidence, synthetic payment/delivery test limits and remaining operational gates.
- `frontend/components/TerritoryScopePicker.tsx`, `frontend/lib/territory-scope.ts`, `frontend/lib/directory-db.ts`: current local picker, enquiry transport and count semantics.
- `api/routers/billing.py`, `api/services/territory_brief_delivery.py`, `api/services/territory_brief_fulfilment.py`, `frontend/lib/territory-brief-download.ts`: local dormant order, generation, prepared-file/queue and entitlement semantics.

## Principal findings

| Priority | Finding and evidence | Buyer consequence | Product response |
|---|---|---|---|
| P0 | `territory_scope_request` is emitted on a mailto click; the buyer must still send the email. The buying audit never established actual inbox receipt. | Customer can believe the request has been made while CareGist has no enquiry. An inflated request count obscures abandonment. | Keep click as an initiation event; count received enquiries only from inbox evidence. Acknowledge with ID, owner and next action. |
| P0 | Local coverage uses location-row `COUNT(*)`, while final output groups/deduplicates provider organisations. Checkout/generation mapping carries geography, window and target but omits picker category/service selection. Generator now supports service type and qualification questions; old sample defects cannot be assumed unchanged. | A promising count can turn into a smaller or unrelated shortlist after payment. | Freeze one supported scope version and reconcile eligible distinct organisations before a quote; preserve category/service/exclusions through final QA. Stop unsupported combinations. |
| P0 | Staffing, actual inbox handling, merchant proof, independent review availability, private-file retrieval and complete recovery remain unverified in the packet. | A buyer can pay into an unattended queue or receive an unusable link. | Name operator, merchant owner, reviewer and backup; exercise controlled receipts before commercial activation. Engineering passes cannot replace these receipts. |
| P1 | The published local terms start the three-working-day target after scope confirmation and source-path checks, while payment is separately required before work. There is no measured enquiry-to-delivery commitment. | A late payment or slow scoping exchange can make a three-day promise confusing and leave the buyer uncertain. | Quote an actual calendar date and payment timing condition; re-agree a changed date explicitly. Never silently move the target when payment arrives. |
| P1 | Local `fulfilled` sets prepared file references and queues email before sending/access. A token consumption updates its count before private storage retrieval succeeds. | Dashboard can show success while the customer has received nothing; a failed retrieval can use a quota. | Track prepared, send accepted, inbox receipt, successful retrieval, buyer-confirmed opening and acceptance separately. Investigate/reissue through an approved route; do not count a token hit as usable receipt. |
| P1 | A three-to-five-page executive brief may have a longer evidence appendix; the CSV is distinct from an Excel workbook. | Buyer expecting a short total PDF or native spreadsheet may feel the product changed. | Put exact file inventory, executive/appendix distinction and required CSV import tool in the accepted scope. |
| P2 | The proposed eight labour hours do not include any observed queue or buyer-delay distribution. Twenty-five operator hours/week also cover discovery, operations and setup. | Faster rendering may save minutes while multi-day sales/review waits persist. | Record labour and wait separately at each boundary; optimise the largest observed CareGist-controlled wait before broad automation. |

## Journey design from the buyer's viewpoint

The following response targets are proposed internal pilot controls, not current public SLAs or verified performance. Use the existing daily start/end inbox checks and agreed backup cover. External wording remains subject to the approved route and operative terms.

| Stage | Buyer needs to know | Exit evidence | Owner and timing control |
|---|---|---|---|
| Enquiry received | “Did you receive it, and who will help?” | Actual incoming message; enquiry ID; owner; received/acknowledged timestamps | Sibongile or backup: acknowledge by next working day; include next action/date. Website email initiation is outside this state. |
| Qualify decision | “Will this solve my specific territory decision?” | Buyer objective, provider types, exclusions, deadline, authority, current method and sample feedback | Sibongile: offer one short call or concise asynchronous questions. Do not require a call for an already clear scope. |
| Feasibility | “Can you deliver the relevant organisations, and what are the limits?” | Eligible distinct-provider set/count, approved source edition, material unknowns and reviewer capacity | Source owner/operator: proposed next-working-day decision after complete answers; unsupported scope gets a clear refusal/rescope, not a generic sales delay. |
| Written offer and acceptance | “What exactly will I receive for £745, when, and what happens if it fails?” | Buyer accepts exact scope/version, fee/tax, files, recipient, calendar target, payment condition and remedy terms | Sibongile/Henry: present one decision-ready confirmation. Changes require a new version and acceptance. |
| Payment request and verification | “Is it safe to pay, did it work, and should I pay again?” | Approved payment route; authoritative matched merchant evidence; amount/currency/order/refund state | Merchant owner: verify before start; unmatched/duplicate payment opens recovery. A return-page URL is insufficient. |
| Production begins | “Who owns this and is the agreed date still credible?” | Work-start timestamp; supported source/scope; reserved reviewer; date reconfirmed if needed | Sibongile: one start confirmation. State the next update/date, not internal gate terminology. |
| Review and correction | “Are you checking the pack against what I bought?” | Independent every-row/files/manifest verdict; corrected version re-reviewed; exact hashes | Reviewer: reserve slot before payment; communicate any risk before the promised date. No QA reduction to protect an estimate. |
| Delivery | “Which files are included, how do I open them, and who fixes a problem?” | Approved recipient/route, exact inventory, send reference and actual access evidence | Sibongile: deliver final PDF/CSV/manifest with a short use guide, limitations and support reference. Access terms must match the selected route. |
| Confirm usable receipt | “I can open the files and use the data.” | Buyer acknowledgement that required files open; agreed fields/counts checked; issue or acceptance recorded separately | Sibongile: next-working-day check after delivery; unresolved/non-response cases remain unconfirmed, not accepted. |
| Verify value | “I know which accounts to investigate and which questions to ask.” | Buyer names a concrete decision/action, specific usefulness/missing evidence, potential repeat job | Sibongile: proposed +5-working-day interview. No unsupported sales or revenue attribution. |

Use an internal state machine with separate payment/work/delivery/remedy dimensions. In customer communications use simple labels: received, reviewing suitability, awaiting your confirmation, awaiting payment, preparing, ready, access problem, resolved. Always provide owner and next action/date. Do not require the buyer to understand source gates or transaction retries.

## How long the journey could take

Three different clocks are necessary:

1. **Total elapsed time:** inbox receipt → buyer-confirmed usable access. This includes weekends and waits; record UTC event times and display Europe/London calendar dates.
2. **Promise clock:** scope-confirmed + source-checked → quoted calendar delivery target. The published terms say three working days, with England public holidays excluded. Late payment requires explicit date re-agreement.
3. **Labour and wait:** active minutes by operator/reviewer/merchant; CareGist queue wait; customer-response/payment wait; external-service wait. A missing timestamp means unknown, never zero.

The runbook's **eight-hour all-in labour budget is a hypothesis**. One possible allocation preserving its total is: acquisition 1.00h; triage/scoping 0.75h; pre-payment source feasibility 0.50h; remaining research 2.00h; analysis/files 1.50h; independent review 1.00h; payment/admin 0.25h; delivery/access 0.50h; correction/support 0.50h = **8.00h**. The feasibility split is this review's planning allocation, not measured execution. Seven hours are non-reviewer labour; one is separate reviewer labour. Acquisition includes unsuccessful prospects and is an economic allocation, not necessarily time after this buyer's enquiry.

The three-working-day target below is counted after the confirmation day. These are **illustrative calendar scenarios**, not observed service results or promised dates. They assume no intervening England public holiday, approved gates, a supported source and reserved reviewer/backup. Customer confirmation of access can occur sooner or later than the next-day check.

| Scenario | Illustration | Enquiry → delivery | Enquiry → confirmed usable access |
|---|---|---:|---:|
| Fast, buyer ready | Enquiry Mon 12 Oct; scope/source/payment verified same day; delivery Thu 15 Oct; confirmed opening Fri 16 Oct | Approximately 3 calendar days | Approximately 4 calendar days |
| Normal staged scoping | Enquiry Mon 12 Oct; qualify Tue 13; scope/source/payment complete Wed 14; delivery Mon 19; opening confirmed Tue 20 | Approximately 7 calendar days | Approximately 8 calendar days |
| Late enquiry and payment wait | Enquiry Fri 16 Oct late; acknowledgement Mon 19; qualify Tue 20; scope/source Wed 21; buyer pays Fri 23; buyer explicitly agrees revised Wed 28 delivery; access Thu 29 | Approximately 12 calendar days | Approximately 13 calendar days |
| Material source or staffing failure | Payment/source/reviewer/access problem remains unresolved | No defensible fixed estimate | No defensible fixed estimate; named recovery owner, communication and agreed remedy required |

The third row's revised Wednesday date is an illustrative agreement, not an automatic reset allowed by the terms. Without agreement, the original scope/source clock continues to be material. Do not describe “three days from enquiry” or “instant fulfilment” from these assumptions.

With 150 minutes/day proposed for production and one independent reviewer, a four-hour operator production/correction allocation already spans approximately 1.6 protected production days, before reviewer waiting and delivery. Two concurrent paid orders can be permissible under the blueprint only if each has reserved capacity; the two-order cap is not a promise of two deliveries every three days. Actual throughput requires the rehearsal's measured minutes and case mix.

## Growth measurement that reflects the actual customer path

Use raw counts first, and distinguish unique enquiries, buyers and orders. Website sessions/CTA events and operational records need separate identifiers; do not introduce buyer personal data into public analytics. Do not claim rates that cannot be linked reliably.

| Metric | Definition | Interpretation and guardrail |
|---|---|---|
| Enquiry initiation | mailto CTA clicks or copy actions | Intent proxy only; not submitted enquiries. Local CTA event currently exists; copy-success measurement is not established here. |
| Received enquiry count | Actual messages in the monitored inbox, deduplicated | Starting denominator for the operational funnel. Record web/direct/referral source when known. |
| Qualification completion | Qualified enquiries / received enquiries in a dated cohort | Include unresolved cases and reasons rejected/unresponsive; do not mix later-cohort numerator with earlier denominator. |
| Feasibility yield | Feasible supported scopes / completed scope assessments | Low yield may reflect wrong segment or source limits; never broaden scope solely to improve this rate. |
| Offer conversion | Accepted versioned scopes / actual written offers | Buyer uncertainty, price/scope/date objections and ownership of next action explain losses. |
| Payment conversion | Matched paid orders / accepted scopes, within stated observation window | Separately report unpaid, pending, declined and mismatched; never count test payments. |
| Delivery reliability | Orders delivered by agreed date / orders due | Use versioned agreed dates; count source/review/access incidents independently. Moving dates silently cannot improve reliability. |
| Usable receipt | Orders with buyer-confirmed opening of all required files / released orders | Send acceptance, inbox appearance, token requests and byte retrieval are supporting events, not equivalent to buyer confirmation. |
| Activation | Buyers naming a supported account-prioritisation decision or action / buyers with usable receipt | One interview is evidence of use, not proof of increased sales. Record verbatim action and limits. |
| Time and effort | Stage timestamp differences, active labour and wait owners | For a small pilot, display each case and range; avoid unstable percentile claims. |
| Recovery burden | Open/overdue cases, factual defects, access failures, correction minutes, refunds | Prevent high apparent conversion masking a broken service. |

No observed conversion percentages are supplied. The blueprint's three scope requests after ten substantive conversations is a proposed learning threshold, not a benchmark or evidence of product-market fit. Preserve raw reasons and separate readiness failure from buyer rejection.

## Concierge versus structured intake

| Approach | Why viable | Cost and failure modes | When to choose |
|---|---|---|---|
| Instrumented manual concierge | Current email path exists. Operator can resolve ambiguous decision criteria before a promise and learn buyer language. A restricted register, templates and versioned scope suffice for the first small cohort. | Email-app handoff, retyping, missed messages and inconsistent acknowledgement. Requires rota, disciplined logging and safe account access. | Recommended first, after approved route/rehearsal. Preserve picker scope verbatim, then validate and freeze it. |
| Durable structured intake + concierge | A form can persist region/category/service and buyer decision, issue an enquiry ID and send acknowledgement after actual durable receipt. Human scope/payment controls remain. | New validation, privacy, spam/duplicate, durable persistence and notification failure states. A client-side success screen without a durable record reproduces the existing measurement problem. | Build when evidence shows repeated intake loss/retyping or buyer feedback rejects email. Keep a working fallback and prove record/notification reliability before launch. |

Start structured intake with contact email, preserved public scope, buyer's decision/deadline and optional message. Collect enrichment/exclusions during qualification unless the buyer already knows them. Do not create a lengthy questionnaire or allow payment merely because the form has a candidate count. A calendar appointment can reduce scheduling exchange, but must show real availability and retain an asynchronous alternative.

As a **proposed diagnostic trigger**, two independently evidenced lost/ambiguous enquiry handoffs among the first ten intake attempts, or repeated buyer feedback that email submission is unusable, justifies prioritising durable intake. This small-count trigger is an operational judgement, not statistical proof or a conversion forecast.

## Smallest next step and acceptance

**Next bounded task: one enquiry-to-usable-receipt rehearsal using the chosen concierge route, synthetic buyer data, the restricted order record and a full supported shortlist.** Do not add checkout or increase outreach until this path's specific gates are closed. The parent review can schedule work, but this analysis does not approve live external actions.

Before the rehearsal, establish the approved inbox/merchant/storage destinations, roles, backup and independent reviewer slot. An internal tabletop can start now; it cannot count as the external receipt proof.

Acceptance evidence:

1. Received message, recorded enquiry ID/owner, acknowledgement and next-action deadline; preserve region/category/service/exclusions at every stage.
2. Supported candidate set/count and source edition; unsupported scopes rejected before any payment request; complete versioned buyer acceptance and explicit date/payment treatment.
3. Approved synthetic merchant payment matching the order, amount and currency; duplicate/unmatched evidence does not start a second production or reset the date silently.
4. Full PDF/CSV/manifest independently reviewed against every agreed entry and the original scope; corrected files re-reviewed; exact inventory/hashes retained.
5. Correct-recipient controlled inbox receipt, private-file retrieval and actual opening of all required files; unauthorised recipient denied. Sending alone fails receipt acceptance.
6. One failed-access recovery through the approved route, with named owner and closure evidence. No public attachment workaround. Source failure/cancellation/refund exercise remains required by the broader gate checklist and cannot be omitted merely because this bounded journey passes.
7. All stage timestamps and active labour recorded; every wait assigned to buyer, CareGist or external service; proposed targets exceeded produce an explicit case/action rather than a false complete state.
8. Final independent verdict states which checks were exercised versus simulated. Customer-facing activation remains subject to the prescribed Grok/DeepSeek/founder gates; this role review cannot replace them.

## Document review result

This analysis distinguishes dated observations, local code, proposals and estimates. The eight-hour allocation and dated examples reconcile arithmetically; the terms' two clock predicates, payment requirement and scope/version mismatch are traceable to the reviewed artifacts/code. The output covers enquiry, payment, prepared/sent/access states and recovery; no claim of actual customer receipt or growth lift is made.

**Analysis handoff: evidence-bounded recommendation ready for the parent reviewer. Operational journey: NOT VERIFIED end to end.** No code/blueprint changes, messages, payments, gate activation or deployment were performed. An independent review of this exact document and the parent synthesis is still required before the substantial deliverable is called complete.
