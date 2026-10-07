# CareGist: three products for first revenue and durable repeat business

## 1 October follow-up: Territory Brief readiness correction

Read-only production checks and served-release source inspection are saved in
[TERRITORY_VERDICT_CHECK.md](TERRITORY_VERDICT_CHECK.md). The three product families
below remain research priorities, not immediately executable offers. All 34,332
`rating_changed` rows lack effective dates, so zero recent matches cannot establish
no rating movements. The exact 115-location London RI sample has no stored rating
publication in the last 12 months. The paid generator still reads raw NDJSON at
the served release and ranks locations without provider deduplication; its
fulfilment outputs PDF/CSV, not XLSX. These are specific acceptance blockers.

London homecare has 35 distinct provider IDs with registration entries in 90 days,
but only 21 pass the URL/hash/date metadata screen; national social care has 302,
of which 147 pass that preliminary screen. This supports qualification of broader
registration-focused scopes, not a current rating-change claim, paid demand or
release acceptance. A Postgres adapter alone will not fix rating-history semantics,
organisation counts or output promises. Latest scheduled main smoke and watchdog
runs passed; checkout and delivery remain closed.


**Research date:** 1 October 2026. **Horizon:** remainder of 2026, 2027 and 2028.
**Verdict:** research recommendation; not commercial release approval.

Lead with **regional care-market monitoring**, use **Territory Opportunity Briefs** to earn larger individual fees, and develop a **licensed intelligence feed** only when a buyer funds a specific integration. These are three product families serving different customer jobs. They can share the same evidence system without requiring three separate platforms.

CareGist has useful underlying assets. It does **not** yet have evidence of three immediately sellable, recurring, market-validated products. The current founder catalogue permits two one-off offers; ongoing monitoring and the feed would require new commercial decisions. No research or model can establish guaranteed future sales.

## 1. What was actually examined

- Repository operating loop, latest catalogue, product configuration, source/event services, database schema, territory generation and fulfilment, legal drafts, buyer research and sales samples.
- Live public health, directory, release, pricing, terms, source-status and territory-scoping pages. Probe started at 14:48 UTC / 15:48 BST.
- Neon database through the repository's existing connection helper, with `transaction_read_only=on`, aggregate queries only and a 20-second statement timeout. No customer-level extracts or production writes.
- Stripe Projects resource inventory. The existing Projects plugin needed an update from 0.39.1 to 0.45.0 because the service rejected the old version. Projects authenticated successfully. Its resource metadata should not be treated as a fresh provider-plan audit.
- Direct read-only Stripe account/subscription/charge checks failed because the default CLI API key has expired. Bank payments and live Stripe balances are not verified.
- Relevant connected Gmail searches. No Fulcrum buyer thread was found in that connected mailbox. Local prepared correspondence is a possible follow-up lead, not independently verified buyer demand. Other mailboxes were not available through this connector.
- Current primary-source competitor offers, CQC data and regulator changes, and consultancy service descriptions.
- Jev 1.13.0 comparison against a public-source-only evidence packet. Private database and commercial aggregates stayed local.

The database scale agrees with the live health response. A one-organisation difference between the API and SQL counts appeared during the separate observations; do not present them as one atomic snapshot. Neither is a count of prospective customers for CareGist.

## 2. The assets and limits that change the recommendation

| Observation | Evidence and commercial implication |
|---|---|
| 59,108 stored CQC location rows; 57,205 active | Includes dental, primary medical and other healthcare. This is not a 57,205-company adult-care market. |
| 30,591 active `Social Care Org` locations; 18,103 distinct provider IDs within that subset | This is the more relevant initial market universe. Provider IDs still do not establish legal ownership groups or buyer budgets. |
| 14,430 social-care locations include domiciliary care | Useful homecare territory coverage. Service categories overlap; do not add domiciliary and care-home counts as separate organisations. |
| 236, 129, 216, 185, 108 and 156 social-care locations carry April–September 2026 registration dates | The stored register shows movement across six months. These counts do not prove new businesses, newly opened services, or buying intent; the query includes stored active and inactive rows. |
| September social-care registrations involve 87 distinct provider IDs | A location-level list can substantially overstate independent accounts. Deduplicate an account shortlist by provider ID, and label ownership uncertainty. |
| 312 recent-effective registration events across all CQC sectors; 308 have URL, snapshot hash and effective date | A comparatively usable starting signal. Each item still requires acceptance checks; the four incomplete-provenance events are excluded from customer output. |
| Social-care recent registration subset: 156 locations | Regional supply is uneven: North West 45 locations/13 organisations; London 18/18; South East 20/17; North East 1/1. Volume is not the same as independent buyer opportunity. |
| 401 `rating_changed` entries observed over 30 days, with zero grade-to-grade transitions | Every observed pair includes null or a non-grade label. Effective dates are unpopulated. They do not substantiate a stream of upgrades or downgrades. This does not establish that no genuine changes happened at CQC. |
| 25,997 `rating_status_changed` entries in the same window | Classification and missingness movements must not be marketed as 25,997 commercial opportunities. |
| 59,117 lifetime `new_registration` ledger entries include effective dates back to 2010 | Historical/bootstrap entries are not newly opened businesses. Filter by source-effective date and preserve observation date separately. |
| Zero active directory email addresses | A territory pack is account research, not an email-ready contact product. Phone availability is not outreach permission. |
| No CRM deals, paid application subscriptions, territory orders, event actions or customer outcomes | The system does not establish paying demand or retention. Unrecorded manual sales remain possible. |

The most recent live source is the 23 September directory, retrieved 30 September and reconciled at 12:28 UTC. All 57,139 source locations were checked with zero failures. Health reports fresh under the existing SLA. That means fresh against CareGist's source process, not real-time knowledge of the market.

The live frontend and backend both report release `b2f519aa8aaebe33197076bd8f2fed6f60a56595`. Commercial health remains `checkoutReady=false`: 15 completed seven-day polls versus 24 required, with delivery disabled. No gate was changed during this research.

## 3. Product one: regional care-market monitoring

**Priority:** first commercial validation and strongest near-term repeat workflow.

**Buyer:** owner, commercial director or consultant at an England care consultancy with ongoing provider relationships, an active market-development task and a defined territory. Select firms supporting providers after registration, rather than firms whose only service is preparing registration applications: a completed registration can arrive too late for that latter sale.

**Customer job:** know which relevant accounts warrant review this week, check the official evidence quickly and maintain a record of what the team did next.

**Initial offer:** the existing £150 pilot: one agreed England region, four reviewed weekly digests, no automatic renewal. Start with independently checked registration entries. Include any rating movement only when comparable before/after evidence for the same service supports it. Label first rating publication separately. A register cancellation or archived location is not proof of a business closure.

**Proposed recurring version:** a personalised monitoring service, initially testing £150/month with explicit opt-in. That price is a research hypothesis, not an approved recurring catalogue or demonstrated willingness to pay. Historic Radar prices of £299/£799 do not prove today's buyers will accept them.

**Reason to stay:** a saved account/client list, buyer-selected relevance, weekly review, source history, and recorded follow-up outcomes. Personalisation should remove work from an existing task. More notifications alone do not establish value. A quiet week must be described honestly, with the source window and any useful review of the existing account list; do not manufacture changes.

**Evidence of buyer relevance:** [Fulcrum](https://fulcrumcareconsulting.com/) and [CQC Consultants](https://cqc-consultants.com/) describe ongoing governance, mock inspection or retained support. [Delphi](https://delphi.care/our-services/cqc-consultancy/) provides another relevant consultancy example. These are prospective buyer shapes, not CareGist customers or endorsements.

**Paid validation:** after release acceptance, seek three paid pilots. For each, record actual use, time saved, relevance, an attributable qualified action and willingness to buy the next defined period. Continue the recurring experiment only if at least two explicitly buy another period and the workload is economic. Opens, compliments and sample requests do not meet that standard. Then require three paid cycles before describing retention as demonstrated.

**Main uncertainty:** the current registration-only evidence may be too sparse or too late for a consultancy's actual job. If the pilot fails that relevance test, change the buyer scope or stop; do not solve it by promising unsupported rating, vacancy or distress signals.

## 4. Product two: Territory Opportunity Brief and repeat territory research

**Priority:** larger near-term fees; lower confidence in continuous renewal than monitoring.

**Buyer:** sales director or owner at a care-sector supplier or specialist staffing business making a real territory or account-prioritisation decision. The brief must use that buyer's supported service/geography criteria. A staffing buyer cannot receive asserted staffing vacancies from CQC registration alone.

**Customer job:** decide where to focus the next sales period and which organisations merit research first.

**Initial offer:** existing £745 one-off brief, with a scoped market map, organisation-deduplicated shortlist, stated inclusion reasons, source and observation dates, and a practical prioritisation report. The code already includes deterministic generation, rendering and fulfilment components; their existence is not acceptance of the production customer journey.

**Proposed repeat purchase:** a fresh quarterly decision brief, separately accepted at the same £745 test anchor. Four purchases would total £2,980/year per buyer. That is potential repeat research revenue, not present MRR, an approved subscription, or four forecast sales. Renewal requires meaningful new evidence, a new territory or a new decision; sending the same CSV again is insufficient.

**Reason to stay:** the report helps an active sales team revisit accounts and territories as its own results and the source change. Include the buyer's permitted outcome feedback only after the relevant data-processing terms are agreed. This feedback can improve prioritisation more than adding unverified external enrichment.

**Differentiation requirement:** [CareHomeData](https://www.carehomedata.co.uk/pricing) advertises a £199/year dashboard. Its quality, subscriber base and independence have not been audited. Nonetheless, CareGist must make the difference between a £745 decision brief and generic account access concrete: a buyer-specific decision, checked shortlist and usable reasoning.

**Paid validation:** deliver three accepted briefs economically. Ask buyers what decision changed. Do not count an attractive PDF as proof. Continue repeat research only when at least two buy a second brief for a stated decision.

**Main uncertainty:** territorial research may be occasional. Treat it as a cash-generating service until repeat orders prove otherwise. Jev also rated its recurring workflow below monitoring and feeds; the recommendation includes it because it is already a current paid offer and can reuse existing assets.

## 5. Product three: scoped licensed intelligence feed

**Priority:** strongest potential for embedded annual revenue; slowest and least validated route to first cash.

**Buyer:** a care-software vendor, specialist CRM/workflow vendor or sufficiently large multi-client consultancy with a specific system that needs maintained provider identity and verified changes.

**Customer job:** keep its operational system current without building and maintaining the entire source-monitoring, evidence and replay process.

**Offer to validate:** one named integration, one agreed geography and initially one verified signal. Stable IDs, traceable history, documented schemas, source timestamps, deduplication, replay, correction handling and observable delivery matter more than a broad API feature list.

**Price research anchor:** the historical £6,000/year Feed Pilot was a hypothesis and is currently retired. It can inform a new scoped proposal, but must not be quoted as available or validated. Price setup separately if the integration's work demands it; the exact setup fee should follow a concrete paid scope, not be invented here.

**Reason to stay:** a buyer's real operational workflow depends on continued reliable maintenance. Retention should come from value and dependable service, with usable exports and contractual exit provisions. Avoid artificial lock-in.

**Competition:** [CQC itself](https://www.cqc.org.uk/about-us/transparency/using-cqc-data) offers an API. A technically capable customer may prefer to maintain that connection directly. CareGist must show its maintained history, reliability and support cost less than the customer's alternative for the agreed job. Do not sell simple pass-through access as a moat.

**Paid validation:** require a buyer-funded integration before expanding the product. Accept one source-scoped build only after reopening the stopped product and passing the relevant legal, security, reliability and delivery gates. Record real weekly use, avoided maintenance effort and renewal evidence. No API roadmap build merely because a prospect says it sounds useful.

**Main uncertainty:** no integration buyer or annual licence is verified in this review. Prefer software or consultancy design partners before insurers, lenders, councils or ICB procurement. This product may remain an experiment through 2027; reaching 2028 does not itself validate it.

## 6. What to sell in each year

| Product family | Remainder of 2026 | 2027, conditional on paid evidence | 2028, conditional on renewals |
|---|---|---|---|
| Regional monitoring | Validate £150 four-week pilots after the named gates pass | Sell a defined opt-in ongoing service to the segment that actually renews | Expand regions and client-list workflows when use supports it |
| Territory research | Validate £745 briefs against real buyer decisions | Sell repeat quarterly research where buyers reorder | Standardise repeat briefs without allowing custom analyst workload to consume the margin |
| Licensed feed | Research a specific paying integration partner; do not count licence revenue | Implement one buyer-funded integration after reopening and acceptance | Expand maintained annual licences only from demonstrated integration use and renewal |

Do not replace the entire product each year. Improve the evidence history and the recurring job. Do not simultaneously open three outbound campaigns: monitoring first, briefs as a separately qualified offer, feed only for a funded integration need.

## 7. Economics: what the returns could mean

These are explicit **sensitivity calculations**, not measured costs, margin forecasts or promised revenue. Labour is assumed at £30/hour; no independent labour, acquisition or infrastructure costing has been supplied.

| Unit | Revenue assumption | Illustrative incremental delivery cost | Contribution before shared costs, acquisition and tax |
|---|---:|---:|---:|
| Four-week digest pilot | £150 | 2 hours £60 + £10 tools/fees | £80 / 53% |
| Territory brief | £745 | 5 hours £150 + £15 tools/fees | £580 / 78% |
| First-year licensed feed | £6,000 | 10 setup hours £300 + 24 support hours £720 + £300 tools | £4,680 / 78% |

The pilot's two hours must include the buyer's allocated share of common compilation and checking, not just sending an email. At four hours and £10 tools, its contribution falls to £20. Capacity must therefore be measured before scaling. Shared source engineering, independent review, legal work, incidents, selling time and customer acquisition can materially reduce all three figures.

For buyer value, £150/month requires 3.75 hours saved at an assumed £40/hour merely to match the fee on time savings alone. One hour saved each week is about 4.33 hours/month, but this saving must be observed in the buyer's workflow. Never promise an engagement or sale as a guaranteed return.

An illustrative mature combination is 20 monitoring clients at £150/month, five buyers each purchasing four £745 briefs per year, and two annual feeds at £6,000:

- Monitoring: £36,000/year.
- Repeat briefs: £14,900/year, dependent on four separate purchases each.
- Feeds: £12,000/year, dependent on licence acceptance and retention.
- Total: **£62,900 annual revenue**, averaging £5,241.67/month before costs.
- The subscription/licence portion is **£48,000 annual recurring run-rate**, or £4,000/month equivalent. Brief revenue is not included as MRR.

There is no demonstrated conversion rate, CAC, churn rate or fulfilment capacity to turn that example into a forecast. Annual prepayment is cash collection; it is not twelve months of immediately earned revenue or profit.

## 8. Why the other candidates are not the first three

| Candidate | Decision |
|---|---|
| Raw directory, bulk CSV or contact lists | Free CQC alternatives and low-priced dashboards weaken differentiation. CareGist has no provider email coverage. |
| Paid/sponsored listings | No audited consumer traffic-to-enquiry conversion supports provider spending. Directory size is not proof of audience. |
| Pure CQC rating benchmarking | [LaingBuisson](https://go.laingbuisson.com/care-quality-benchmarks) advertises a £599+VAT annual personalised monthly package. Current CareGist movement evidence does not support a premium monitoring claim. |
| Direct inspection readiness or policy packs | Requires qualified practitioners and provider internal evidence. An older cross-project plan is not proof of a CareGist service. [CQC's changing assessment approach](https://www.cqc.org.uk/about-us/improving-how-we-work/0626-update) adds maintenance demands. |
| Guaranteed appointments, recruitment leads, distress or vacancy scores | Public registration/rating data cannot establish those claims. The named lead, claim and export gates remain closed. |

Established paid data categories provide supporting market evidence: [LaingBuisson's data store](https://www.laingbuisson.com/shop-category/data/) lists CareSearch at £1,655–£3,150/year and its care-home database at £3,999/year. These are advertised competitor prices, not verified CareGist buyer budgets or proof its proposed price is correct.

## 9. Jev's contribution and limits

Automatic approval review rejected transfer of the private internal evidence packet. The successful run used only public webpages and generic candidate descriptions, saved in `jev-public-evidence-packet.json`. It used Jev 1.13.0 and 3,068 input / 446 output tokens.

- First-cash 2026 selection: regional monitoring.
- Recurring workflow 2027 selection: regional monitoring.
- 2028 durability selection: licensed feed, narrowly over monitoring. Its distribution was 0.52 versus 0.48 with confidence 0.43, so the result was close and uncertain.
- It did not find public evidence establishing repeat paying CareGist customers.

These distributions describe the model's comparative judgement, not probabilities of commercial success. Jev did not inspect the private database, interview buyers, independently certify the product or approve a gate. The internal database findings informed this report separately.

## 10. The next bounded step toward money

Prepare **one independently accepted current-source Digest pilot pack** for one clearly supported consultancy scope. Reopen the delivery copy, verify every included event, ensure the order wording and £150 terms agree, and prove the approved manual payment-to-delivery path. This is the next bounded step; a broader dashboard or third product build is not necessary to make it reviewable.

Once those named gates and founder decisions are recorded, the commercial experiment is to offer that concrete pack to the qualified cohort and seek three paid pilots. Verify any local Fulcrum sample request in the actual sales mailbox before treating it as a warm prospect. No outreach, invoice, payment link or sale was issued during this research.

After four deliveries, ask for a separate paid continuation and measure why the buyer says yes or no. Continue the monitoring line only on those results. Territory briefs can be sold as an individually scoped second offer when a buyer has that job. A feed waits for funded integration demand.

Unfinished commercial work is distinct from completed research: source-event acceptance, legal alignment, payment/delivery acceptance, poll coverage, actual buyer payment, repeat purchases and independently reviewed release decisions all remain open.

## Evidence files

- [Aggregate SQL and results](database-aggregates.json)
- [Live health probes](live-health-probes.json)
- [Live pricing](pricing-live.txt), [live terms](terms-live.txt), [live territory journey](pricing-territory-live.txt)
- [Stripe access limitation](stripe-readonly-summary.json)
- [Private local evidence packet, never transmitted](jev-evidence-packet.json)
- [Public Jev input](jev-public-evidence-packet.json) and [Jev output](jev-results.json)
- Repository authority: `deploy/stripe-price-manifest.json`, `frontend/lib/caregist-config.ts`, `.warroom/`, `docs/weekly-digest-pilot-measurement.md`, `docs/weekly-digest-pilot-terms-draft-FOR-SOLICITOR-2026-10-01.md`.

Existing user edits and output packs were preserved. Stripe CLI operations synchronised its managed local state files; those files were not hand-edited. No product code, production data, commercial flag, catalogue, deployed site or external communication was changed. This report's author has not independently approved its own work.
