# CareGist: red-team assessment and 30-day operating plan

Prepared 11 October 2026. Decision support, not commercial activation or legal approval.

**Recommendation: test one supplier-facing Territory Brief as a manually operated research service. Use Sibongile's confirmed 25 hours a week to establish reliable delivery and buyer value. Defer a bespoke Weekly Digest, direct provider rescue services, and API expansion.**

This recommendation changes if qualified buyers consistently want a shared regional monitoring edition instead of bespoke account research. The two offers solve different jobs; a Digest-to-Brief upgrade is a hypothesis, not an established funnel.

The user identified Sibongile as the operator and confirmed 25 hours per week. The timetable below assumes five five-hour working days. Henry's founder/merchant responsibilities and a separate reviewer are proposed assignments; their availability and the reviewer's identity remain unconfirmed. No customer contact, order, payment, refund, gate activation, deployment or production write was performed for this review.

**1. What the evidence actually says now**

I inspected the live homepage and Territory Brief flow in a browser, including a real free coverage calculation and its email fallback. Public pages and health responses were captured at approximately 06:48–06:49 UTC / 07:48–07:49 BST. The public frontend and backend reported release `0fda3cac8b670ed3dddb31ac3c45644ca430e387`. Local checkout HEAD was `c17d1df9b6214664d650274ac12e9f181fcf5ad7`; that reported production object was unavailable locally. Local code findings are therefore not proof of the deployed implementation.

| Claim or proposed action | Evidence and red-team finding | Decision |
|---|---|---|
| 1,000 new registrations; 2,285 Requires Improvement | Live browser showed 998 and 2,279. These are displayed location counts, not independently validated market size, changes this week, or purchase intent. | Date every observation; do not use these totals to forecast sales. |
| Inadequate: 35 must be wrong because it looks low | Live browser showed 35. Size alone proves no defect. Service-level versus location-level ratings, population and source edition matter. | Check the relevant cohort and official record before use; do not inflate the number. |
| No published rating: 0 means no unrated locations | Live card explicitly refers to an exact rating label. Local SQL tests the literal `no published rating`; it does not include blank/null ratings. The earlier nightly report measured a different blank/null population. | Remove the zero-as-unrated argument. A future UI fix should distinguish exact sentinel, absent overall rating, never inspected and not applicable. |
| The source is still 433 hours old with 104 active-status defects | That was the saved 01:00 report, before a later reconciliation. Current public health reports the 7 October edition reconciled at 06:10:43 today, fresh, 57,129 checked, 57,127 successful and two failed detail lookups. | Supersede the earlier current-state claim. Do not claim the historical 104 defects remain, or claim independently that every one was resolved. |
| Fresh source means ready to sell signals | Live health still reports `checkoutReady:false`, `shadowCoveragePassed:false`, `delivery.enabled:false`. Shadow coverage is 14 completed polls against a minimum of 24. | Freshness has improved; commercial and signal-history gates remain closed. |
| Enough locations means 25–50 organisations can be delivered | West Midlands + new registrations + Homecare Agencies returns 21 matches. Local coverage SQL uses `COUNT(*)` on location rows; a provider can have multiple locations. Live wording calls them organisations. | Verify distinct CQC provider IDs and scope fidelity before promising a shortlist. This tested scope cannot justify a 25-entry minimum. |
| Qualification questions and service filtering are still absent | Local commit history records a repair. The generator now has both; five targeted tests passed in this review. However the inspected checkout request mapping still omits service type, and generator scope does not capture the picker's signal group. | Do not redo the completed generator-field work. Verify the full input-to-output mapping and actual delivery artifact. |
| Re-inspection rescue can be offered immediately | A low/old rating is not a verified deterioration, inspection appointment, budget, or need for a particular service. CareGist's delivery capability for mock inspections was not established. | Do not launch this as CareGist's first service. A qualified partner would need its own offer and delivery proof. |
| More inspection activity proves urgent demand | Clyde & Co supports a historical November 2025/November 2024 comparison. CQC's indexed December update describes assessments; these measures should not be casually interchanged. | Historical context only. It does not establish an individual provider's next inspection or supplier purchasing urgency. |
| New framework implementation is due at year-end | The cited RLDatix page now says national rollout next spring; CQC's March page describes draft sector frameworks and piloting. A current definitive launch date was not established. | Remove the year-end deadline from the sales case. Do not replace it with an unverified firm spring deadline. |
| Apify proves $8 per 1,000 is the current market price | The supplied actor page could not be verified through the web tool. CQC itself makes data available through API and downloads. | Remove the precise price until verified. Compete on useful research and evidence, not a record-price comparison. |
| Using signals in own products costs nothing | RegIntelia/Tender Risk Assurance readiness, capacity, fit, consent arrangements and conversions were not evidenced here. Qualification and follow-up still consume time. | Internal evaluation may teach relevance; record its labour and avoid counting internal usage as external demand or CareGist revenue. |
| Free directory earns the visitor's email | The directory is accessible without signup; a separate subscription form is visible. Submission, receipt and marketing permission were not tested. | Visits are not leads. Measure received, permitted enquiries separately. |

Sources: saved [live evidence](EVIDENCE.md); [current Data Status](https://www.caregist.co.uk/data-status); [public health](https://www.caregist.co.uk/api/v1/health); [9 October buying audit](../../buying-audit/2026-10-09/BUYING_PROCESS.md); [current local generator](/Users/user/CareGist/api/services/territory_brief.py); [local checkout mapping](/Users/user/CareGist/api/routers/billing.py:747); [targeted test output](targeted-generator-tests.txt).

**2. Challenge the commercial thesis**

The strongest hypothesis is: **a supplier with an active territory-sales decision will pay to reduce the research needed to choose and qualify accounts.** The weak version is: providers have low ratings, therefore suppliers will pay for their details. Evidence for the former must come from suppliers' actual workflow, spending authority and use of the pack.

Registration can follow an ownership/legal-structure change rather than the opening of a wholly new business. Registration also occurs after some purchasing decisions have already been made. A current poor rating is a status, not proof of a recent drop. An archived registration need not mean a business closed. A regional feed must distinguish those cases; CQC explicitly explains that archived locations can re-register for other reasons. [CQC data guidance](https://www.cqc.org.uk/about-us/transparency/using-cqc-data)

The initial research cohort should be **care-sector training suppliers already selling to adult social care providers in one England region**, with a sales decision-maker and a real need to prioritise accounts. This is a proposed test segment, not a validated best market. Use the region where Henry/Sibongile has the strongest access to prospective buyers; West Midlands is the working example, not a claim that it is optimal.

Avoid making a low rating synonymous with training demand. Establish the relevance with the supplier. A credible question is “Which of these organisations would your team investigate, and what additional evidence would make that worthwhile?” Do not assert staffing gaps, purchasing budgets or inspection dates.

| Original play | Revised place | What must be true before spending more time |
|---|---|---|
| Feed own products | Small internal relevance exercise, alongside discovery | Existing products can serve the need; record separate qualified outcomes and attribution. No automatic outreach or gate bypass. |
| Weekly Digest | Later, unless discovery clearly favours monitoring | One reusable, non-exclusive regional edition; sufficient verified events; approved terms; four-delivery and recovery proof. |
| Re-inspection rescue | Park | Credible specialist delivery, independent expertise and service terms. A research pack does not establish this capability. |
| Sell signals to suppliers | First external test, packaged as a scoped Brief | Buyer has a territory decision and agrees that the sample supports it. |
| New-registration onboarding | Incorporate only a verified registration segment into the Brief | Buyer can act after registration; distinguish new location from new legal entity/transfer; no invented contacts. |
| Advisers/lenders/property buyers | Later | Separate buyer research; their diligence needs exceed registration/rating facts. |
| Data/API tier | Hold | Repeated demand for integration, reliable completeness/latency and workable support economics. Cheap rows alone do not prove an API cannot sell. |

Using the same public signals for own products and external suppliers may create channel conflict. State non-exclusivity and the actual edition/latency. Do not promise earliest access to paying buyers while quietly delaying their edition for internal advantage. Keep buyer-specific research and customer information separate from other buyers and internal campaigns.

**3. Does manual buying make sense?**

**Yes, for a small number of £745 Briefs, if manual work is structured and costed. The present public path demonstrates enquiry preparation, not a proven manually operated service.**

The website lets the buyer select a region, signal category and service type, see coverage, and prepare an email to `outreach@caregist.co.uk`. The buyer must send that email. Clicking the link creates no confirmed order; web analytics for that click cannot establish inbox receipt. The fallback exposes the text for copying. In the tested 21-match scope, the page correctly says review is needed and ordering is unavailable.

What remains unverified is who reads the email, how quickly they respond, where scope is recorded, which merchant route is used, how payment is matched, who independently checks the work, how the buyer receives/accesses it, and who resolves a defect. Existing code and an email-capable configuration are not operational receipts.

Manual operation has benefits: the buyer's objective can be clarified, unsupported scopes refused, and evidence reviewed before charging. Its costs are slower response, repetitive scope negotiation, human errors, operator absence and limits on throughput. A mailbox plus one controlled order register is sufficient for the pilot; it needs an owner, states and receipts, not a new CRM build.

| Stage | Customer does | Sibongile does | Other owner / proof needed |
|---|---|---|---|
| Enquiry | Sends scope email, including what they sell and the decision they need to make | Checks monitored inbox twice each working day; assigns enquiry ID, next action and due time | Henry provides access and backup. Proposed acknowledgement target: next working day; not yet a public promise. |
| Qualification | Explains territory, provider types, exclusions, decision, existing research and deadline | Runs one 15–20 minute scope call or equivalent email exchange; checks budget authority and practical use | Record buyer's own words. No repeated speculative free bespoke work. |
| Feasibility | Agrees any scope revision | Counts locations AND distinct provider IDs, checks source edition, exclusions, evidence and reviewer capacity | Technical/source owner and independent reviewer clear relevant gates. Never pad 21 into 25. |
| Written agreement | Accepts exact deliverables, fee and calendar date | Produces versioned scope/order record, identifies recipient and acceptance criteria | Henry approves commercial exceptions and operative terms. Both parties retain the same version. |
| Payment | Pays once through approved method | Matches merchant-confirmed payment to order, amount, currency and payer; records it | Henry/authorised merchant operator handles issuing/refunding. Payment-link creation and return-page arrival are not payment proof. |
| Research and production | Answers an exceptional clarification, if necessary | Creates pack from the approved source, times work, links every entry to its evidence, applies buyer criteria | AI/code may assist extraction and drafting. Sibongile remains accountable for the record and cannot mark independent review herself. |
| Review | No action normally | Resolves reviewer defects and freezes the final file versions | Separate reviewer checks every shortlisted entry, scope, dates, entity level and PDF/CSV agreement; records verdict/hashes. |
| Delivery | Opens both files | Uses the approved tested delivery route; verifies recipient and records send/access evidence | Operational route must be independently approved. Do not use a manual attachment as an improvised bypass of closed delivery/export gates. |
| Acceptance | Confirms usability or identifies a defect | Checks file access within one working day; schedules usefulness feedback after five working days | Separate delivery received, usable, accepted and business outcome. Silence is not acceptance. |
| Recovery | Supplies order reference and issue | Owns case, confirms entitlement, coordinates correction, revised date or refund | Henry owns money decisions; reviewer rechecks corrected work. Close only with resolution evidence. |

The current terms require payment before work starts but describe the three-working-day target as starting after scope/source confirmation. Late payment can therefore consume the delivery window. Record an explicit calendar delivery date in each approved written scope; if payment is late, re-agree the date rather than silently changing the clock. This is an operational issue for the approved agreement, not a unilateral rewrite of published terms. [Current terms](https://www.caregist.co.uk/terms)

**4. Labour economics and capacity**

These are planning assumptions, not measured margins or Sibongile's wage. Use a blended £30/hour cost for all labour, including review, and £25 other variable cost per Brief. Measure actual costs from the rehearsal. Customer acquisition includes time spent on unsuccessful prospects, allocated over sales; one hour per order below may prove optimistic.

| Scenario | Labour assumption | Gross sales | Labour + other variable cost | Contribution before fixed overhead and tax |
|---|---:|---:|---:|---:|
| Brief, disciplined process | 8 total hours, including allocated sales/admin/review | £745 | £240 + £25 | £480 / 64.4% |
| Brief, scope creep/rework | 14 total hours | £745 | £420 + £25 | £300 / 40.3% |
| Digest bespoke to one buyer | 1 hour onboarding + 4 × 1.5 hours weekly work; excludes acquisition/other costs | £150 | £210 labour alone | −£60 before the excluded costs |
| Shared Digest, 20 buyers on one identical edition | 4 × 2 hours edition production/review + 20 × 0.25 hours onboarding + 80 × 0.1 hours delivery/support | £3,000 | 21 hours × £30 = £630; excludes acquisition/other costs | £2,370 before the excluded costs |

Shared Digest economics depend on reuse, common scope and low support. They do not apply to 20 different regional/buyer-specific reports. At one buyer, the same shared-edition production model costs 8.65 hours before acquisition: the format needs enough subscribers to support its fixed research cost. Two same-edition buyers barely cover that labour alone (£300 receipts against £279 labour: 8 shared hours + 0.65 hours per buyer). Commercial viability still needs sales, overhead and other costs covered.

For a proposed 60% Brief contribution floor, allowable total labour is `(£745 × 40% − £25) / £30 = 9.1 hours`. Use this as a review trigger, not a reason to skip evidence checking. If three delivered Briefs exceed that, narrow scope, improve reusable work, change price with buyer agreement, or stop the offer.

The original £10,450 arithmetic is correct but is a sales aspiration. Ten Briefs and 20 bespoke Digests require approximately 120–220 delivery hours if Briefs take 6–10 hours and each of 80 digest deliveries takes 0.75–1.5 hours. Those assumptions exclude sales, initial setup and some support. Sibongile has about 100 hours in a four-week planning block. A shared Digest changes the arithmetic, but 20 common-scope customers are not established.

Fifty suppliers are not a sufficient funnel model. Ten Brief buyers from 50 prospects means 20% prospect-to-Brief conversion. Twenty Digest buyers means 40%; if all 30 orders were from distinct buyers, 60%. Cross-buying changes the unique-buyer denominator. Track prospects, substantive conversations, offers, paid orders and accepted deliveries separately.

**Month-one proposal: two to four paid, accepted Briefs (£1,490–£2,980 gross), conditional on gates and demand. Zero sales remains possible.** The primary success is trustworthy delivery, measured labour and evidence buyers act on the output. No revenue from internal product usage belongs in this target.

**That pilot is an investment in validation, and may lose money.** If all 100 planned operator hours are consumed and valued at the illustrative £30/hour, two orders yield £1,490 − £3,000 − £50 = **−£1,560**; four yield £2,980 − £3,000 − £100 = **−£120**. Those figures are before separate reviewer, founder, engineering and fixed costs. This whole-pilot calculation replaces the per-order labour allocation for that calculation; do not add the same operator hours again. Cash outlay depends on actual pay arrangements, while unpaid founder time still has an economic cost. The 64.4% unit scenario is a possible repeatable-order contribution, not a forecast of month-one profitability. Henry should set an acceptable pilot cost ceiling before allocating the month, and reduce the experiment if that investment is unaffordable.

**5. The next 30 days, with executable steps**

Day 1 is Monday 12 October. Dates allocate work; unmet gates stop the commercial stage rather than being waived to meet the calendar. Engineering, founder and independent-review time must be separately reserved; Sibongile's 25 hours is not an assumption that she can perform those specialist roles.

| Window | Sibongile's 25-hour allocation | Concrete output and decision |
|---|---|---|
| 12–16 October: make one service operable | 3h offer/scope; 5h input verification; 8h timed rehearsal; 4h order/recovery setup; 3h reviewer corrections; 2h buffer | One proposed buyer segment, one scope, named operator/backup/reviewer, a full rehearsal pack if scope supports it, and an evidence record. A short sample is not proof of full-pack capacity. |
| 19–23 October: test buyer value | 5h research 20 supplier organisations; 8h up to ten substantive discovery conversations plus notes; 4h sample/offer refinement; 5h initial production or further rehearsal; 3h operations | After outbound permission and applicable gates, seek up to three explicit requests for a scope/quote. Offer at most one first paid slot after independent acceptance. Conversations are a learning target, not a predicted reply rate. |
| 26–30 October: controlled delivery | 14h production/customer handling; 6h discovery/follow-up; 3h recovery/admin; 2h buffer | Aim for up to two additional Briefs within measured capacity and reviewer availability. Retain payment, QA, delivery and acceptance records. |
| 2–6 November, decision by 10 November | 7h final pilot production; 6h buyer usefulness interviews; 4h cost/funnel analysis; 4h corrections/reusable material; 4h buffer | Decide continue/change/stop. Up to one further Brief; no automatic expansion. Seek a repeat purchase or referral as evidence, not as a guaranteed outcome. |

The 8-hour total Brief model includes roughly one hour of separate review and one hour of allocated acquisition. Sibongile's weekly plan deliberately leaves time around production for sales and recovery; the reviewer's hours must be available outside her allocation. Keep at most two active paid Briefs at once initially. If reviewer capacity, source quality or recovery ownership disappears, stop accepting another order.

**The first bounded technical task:** investigate and prove the scope-to-output contract for one chosen Brief. A fixture with multiple locations under the same provider must reconcile location count and distinct organisation count. Preserve service type, selected signal category and agreed buyer criteria from the scope record through generation and output. Verify every row and question matches them; reject unsupported scope. Existing qualification-question/service-filter code should be reused. Do not enable the dormant payment route to test this.

Source-history coverage and the deployable generator source need separate named work. The local runtime still documents a mirrored NDJSON source unavailable in the serverless bundle. A controlled manual production source is possible only after its source/export/delivery gates and route are explicitly approved; it does not inherit approval because it is manual.

Follow the repository's prescribed investigation → named fix → customer retest → frozen independent challenge → orchestration loop. This strategy review and its separate document reviewer are not Grok/DeepSeek commercial approvals. Previous provider-access failures must not be relabelled as completed reviews.

**6. Acceptance and stop rules**

Before requesting payment: verified scope with sufficient distinct organisations; named operator/backup/reviewer; approved terms and payment route; measured production time; source and output review; an authorised synthetic merchant-to-inbox-to-private-file rehearsal and refund/recovery proof; required independent gates and Henry's activation approval. A Stripe test transaction proves the test route, not live configuration or bank settlement.

Before delivery: check each entry against its official source, edition and entity level; distinguish observed/effective dates; validate buyer exclusions, grouping and questions; reconcile PDF and CSV; verify CQC/Open Government Licence attribution in the PDF and the CSV's accompanying approved manifest/README; record reviewer verdict and final hashes. Do not equate a fresh snapshot with complete historical change coverage.

After ten substantive conversations: if fewer than three prospects can identify a concrete use and request a next step at the stated price, change the segment/question before increasing outreach. This is a proposed learning threshold, not a statistical market conclusion. If buyers want only names or contact emails, test that need explicitly; the present public CQC directory does not supply a ready-to-use email list.

After the first three delivered Briefs: continue only if there are no unresolved material factual/contract defects, actual total labour is compatible with the agreed margin target, and at least two buyers can identify a decision/action the pack supported. No uplift in their sales is promised. A repeat purchase/referral is stronger evidence than compliments.

For a Digest later: require a common paid-for scope, explicit non-exclusivity, approved product-specific terms, a defined no-change versus unavailable-data message, four sequential edition tests and one missed-week correction/refund rehearsal. Avoid customising the £150 product into four bespoke Briefs. Current public terms still omit Digest-specific provisions and describe older products.

For outreach, record recipient business type, contact source, relevance and suppression status. ICO distinguishes corporate subscribers from sole traders/some partnerships; personal data obligations still apply. Unknown business type does not qualify for assuming corporate-email rules. Public availability and ownership of another product are not blanket permission to share contacts or send marketing. [ICO B2B guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/business-to-business-marketing/)

**7. Ready-to-use next action**

Sibongile and Henry should spend the first 30 minutes completing the blank [operator record](OPERATOR_RECORD.md): nominate the reviewer and backup, select the supplier segment and buyer question, and reserve the first rehearsal slot. Then test whether that exact scope supports a full, distinct-provider shortlist. If it does not, obtain an explicit scope change or decline it—do not begin selling a pack whose promised contents cannot be produced.

Use the [manual runbook](MANUAL_RUNBOOK.md) for the timed rehearsal. The deliverable is a written process and evidence-backed decision plan; the actual commercial service remains unverified and closed pending the gates above.
