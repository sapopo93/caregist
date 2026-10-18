# CareGist: detailed 30-day operating blueprint

Prepared 11 October 2026 for Henry and Sibongile. Operating window: **Monday 12 October–Tuesday 10 November 2026**. Combines the supplied red-team assessment, manual runbook and Claude Hybrid Operating Model, with the corrections below.

**Decision:** validate one £745 supplier-facing Territory Opportunity Brief through a controlled hybrid service. Sibongile owns the customer process; automation preserves scope and prepares evidence; named people approve scope, money, factual review and release. The first outcome is a complete, independently reviewed rehearsal. Paid work follows only after the named gates pass.

This is a blueprint, not permission to contact prospects, merge, deploy, charge, refund, migrate production data or activate gates. Actual gate receipts and the repository's independent challenge remain required. Dates reserve work; they do not waive a gate.

## 1. What this month must establish

By 10 November, Henry should have evidence to answer four questions:

1. Can CareGist deliver the exact agreed shortlist, executive brief and CSV reliably from an approved source?
2. Will a supplier with a real territory decision request a scope at £745 and pay after suitability is established?
3. Does the buyer use the pack to make a specific decision, rather than merely compliment it?
4. Can all labour, including unsuccessful acquisition, independent review and recovery, fit a sustainable price?

**Planning target:** two paid, buyer-accepted Briefs; a third only if gates, demand and measured capacity permit. The earlier two-to-four range is an aspiration, not this month's workload commitment. Zero sales is possible. Keep no more than two paid orders active at once, and accept the second only when both delivery and reviewer slots are reserved.

**Output inventory:** one defined offer; completed restricted operator record; one full rehearsal and recovery record; approved scope contract; one permitted prospect cohort; weekly evidence dashboard; exact final files and reviewer receipts for each order; a continue/change/stop decision. No real buyer records belong in Git.

## 2. Current evidence and corrections

Latest read-only public check for this blueprint: **11 October, 08:43 BST / 07:43 UTC**. These are service-reported facts, not independent reprocessing of the entire CQC source.

| Claim | Evidence now | Operational consequence |
|---|---|---|
| Source freshness improved | Health reports 7 October edition; reconciliation at 06:10:43 UTC today; 57,129 checked, 57,127 successful, two failures; fresh status | Do not repeat the earlier 433-hour-stale claim. Record the two exceptions and assess whether they affect the chosen scope. |
| Commercial readiness remains closed | checkoutReady=false; shadowCoveragePassed=false; deliveryEnabled=false | Freshness alone cannot authorise a sale or manual delivery. |
| Poll history is insufficient | 14 total/14 completed polls in a rolling seven-day window; minimum 24 total and success ratio at least 0.90; current ratio 1.0 | Observe actual history after the separately reviewed scheduling repair. More cron slots are an intervention, not proof of future success. |
| Local and production source differ | Public release 0fda3cac8b670ed3dddb31ac3c45644ca430e387; local HEAD c17d1df9b6214664d650274ac12e9f181fcf5ad7; production object unavailable locally | Pin deployable source and recheck changed behaviour on that exact release before relying on local findings commercially. |
| Coverage counts locations | Local getTerritoryScopeCoverage uses COUNT(*) over care_providers; generator deduplicates by CQC provider ID | Fix labels/counts, then prove eligibility parity. A distinct-provider count alone does not prove the generator can deliver that many eligible rows. |
| Scope mapping is incomplete | Local generator supports service_type and qualification questions, but checkout request/mapping omits service_type and generator scope lacks the picker's signal category | Reuse completed work. Preserve the selected category and service taxonomy through the pilot contract; reject unsupported combinations. |
| Excel-workbook promise is unsupported | Neither live /pricing nor /pricing/territory, nor their saved 11 October captures, contained Excel/workbook wording in this review | Withdraw the artifact's specific pricing-page allegation. Promise PDF, CSV and manifest for this pilot. Audit any example/other surface before quoting it; do not add an Excel build solely because of that allegation. |
| CRM code exists; operating use is unproven | Contact/deal/task/suppression and screening routes exist locally; live health reports CRM enabled and TPS automation disabled | Prove account access, roles, import, screening freshness and suppression enforcement. Do not mistake available endpoints for completed operations. |
| Screening import is not tracker import | /phone-screenings/import takes screening-result columns phone_e164,status,screened_at | A10 needs a separate contact/deal/task mapping and import/reconciliation path. It cannot import arbitrary revenue-tracker rows through the screening endpoint. |

The backup workflow must reach the default branch to take effect as a scheduled workflow. GitHub also documents that scheduled runs can be delayed or dropped. The stronger claim that the coverage gate is mathematically impossible to pass without this particular fix is not established: the requirement is the actual valid poll history, not a named commit. [GitHub scheduling documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## 3. One offer and one buyer hypothesis

**Working segment:** care-sector training suppliers already selling to adult social care providers, with a decision-maker considering one England territory. Select the region where Henry and Sibongile have the strongest legitimate access; West Midlands is an example, not a validated optimal region.

**Customer job:** decide which provider organisations to investigate first, and what to ask to qualify their relevance. A low rating does not establish training demand. A registration does not prove a new physical opening or an unspent procurement budget.

**Proposed positioning:** “An evidence-linked research pack for your agreed territory and account criteria, so your team can choose which organisations to investigate and why.” Use externally only through the approved communications route after the relevant permissions/gates.

| Contract element | Pilot definition |
|---|---|
| Price | Published £745 one-off offer; Henry confirms tax treatment, approved payment amount and any exceptions before quoting. Do not assume £745 is net revenue. |
| Geography and customer population | One agreed England region or local authority; canonical service types, factual category, exclusions and account-grouping policy written into the scope. |
| Shortlist | Exact agreed number within the published 25–50 organisation range. Start with 25 if appropriate and accepted. Distinct CQC provider IDs are the baseline; disclose any additional commercial-group roll-up. No padding. |
| Files | CRM-ready CSV; executive brief targeting three to five pages; labelled evidence appendix if needed; attribution/source manifest README. Confirm the actual final file inventory in the agreement. |
| Every shortlisted entry | Provider/location IDs, checked source URL, dated fact, scope-fit explanation, useful qualification question and explicit uncertainty. |
| Timing | Explicit calendar target based on the operative terms: three working days after written scope confirmation and source-path check, excluding English public holidays. Resolve late payment by an agreed revised date. |
| Exclusions | No inferred staffing shortage, budget, future inspection date, guaranteed sale, compliance opinion, contact enrichment or exclusivity. |
| Acceptance | Agreed recipient can retrieve and open files; fields/counts match the written scope; buyer confirms usable receipt or raises a specific defect. Silence is not acceptance. |

Defer bespoke Weekly Digest, provider rescue/mock inspections, adviser/lender/property expansion and API work. Internal use may test relevance but is recorded separately from external sales. A later Digest needs a shared scope, approved terms, four sequential editions and missed-week recovery proof.

**Concrete attribution check:** the independent reviewer checks CQC/Open Government Licence v3.0 attribution, the licence link, and source edition/date in the rendered PDF and approved accompanying CSV manifest/README. Include that manifest in the actual delivery inventory and final SHA-256 record; do not add attribution prose as fake CSV data rows that break import. [CQC data licensing guidance](https://www.cqc.org.uk/about-us/transparency/using-cqc-data)

## 4. People, capacity and the operating record

| Role | Owns | Must be confirmed on 12 October |
|---|---|---|
| Sibongile | Inbox, qualification, scope draft, source preparation, production coordination, delivery after approval, feedback and recovery cases | Five working days, five hours/day; restricted tool access; backup handover procedure |
| Henry | Commercial exceptions, terms/tax/payment decisions, technical prioritisation, gate approvals and 10 November decision | Actual engineering/founder hours and spending ceiling; merchant authority; approval availability |
| Independent reviewer | Every shortlisted record, rendered PDF, CSV, scope fidelity, attribution and final verdict | Named person; relevant competence; reserved slots; separate from producer/producing model |
| Backup operator | Inbox/deadline cover and approved recovery handover | Name, access, availability and rehearsal |
| Technical/source owner | Release identity, source completeness/freshness, scope mapping, file generation and failure handling | Henry or a separately named owner; escalation cover |

Use the existing [operator-record template](../../strategy-review/2026-10-11/OPERATOR_RECORD.md) in a **restricted operational store**. Preserve incoming email, buyer wording, accepted scope version, gate receipts and file hashes. CRM is the preferred single register only after its pilot workflow is proven. Until then, one approved restricted register is the fallback; avoid maintaining competing editable records. Keep separate payment, work, delivery and remedy statuses.

**Scope record minimum:** enquiry/order IDs; schema version; region/authority; service taxonomy; selected factual category; status-versus-change definition; evidence/time window; exclusions; shortlist target; candidate location count; distinct-provider count; source edition/retrieval time/checksum; checked-at time; buyer objective; agreed fee/terms/date/recipient; versioned approvals. Commercial and personal fields stay in restricted storage.

The enquiry scope code links to this record or carries a canonical validated public scope payload. A plain checksum detects accidental corruption; it does not establish authenticity. Treat buyer-supplied counts as informational and recalculate them from the approved source. Any changed scope requires a new version and acceptance before production.

**Daily routine, within the five-hour allocation:** check the inbox and exceptions at the start and end of the day; review source/gate status before each consequential step; record time by task/order; assign every open item an owner and next action; hand over anything due during absence. The tables below reserve 0.5h daily for these operations, except Day 1 where setup contains them.

## 5. Gates and the receipts that close them

Record each gate as CLOSED, evidence-ready awaiting independent review, or approved with receipt/version/date. This table adds pilot checks without replacing the repository's named gates.

| Gate | Evidence required | Owner / reviewer | What remains stopped until it passes |
|---|---|---|---|
| G0 — staffed operation | Named roster; real account/role access; monitored inbox; restricted register; backup handover and reviewer slots | Henry and Sibongile; reviewer confirms availability | Accepting a paid delivery commitment |
| G1 — source and release | Exact deployed code identity; approved production source accessible to generator; edition/hash and freshness/completeness predicates; material exceptions resolved; actual shadow coverage/latency gates pass for any signal-based offer | Technical/source owner plus prescribed independent challenge | Unsupported claims, source/export activation and affected commercial steps |
| G2 — scope fidelity | Same contract/taxonomy/window throughout coverage, feasibility and generation; distinct-provider deduplication; exclusions; expected eligible set reconciled before shortlist truncation; rejects unsupported scopes | Technical owner; independent source/output reviewer | Quoting a guaranteed shortlist or taking payment for an unproducible scope |
| G3 — authorised outreach | Actual recipient business type/contact source/relevance; privacy basis and information; opt-out/suppression; fresh TPS/CTPS evidence for calls; campaign-specific approval | Henry / qualified reviewer where needed | Discovery messages/calls and campaigns |
| G4 — terms and money | Approved operative terms/tax/fee/date; merchant configuration; order-reference matching; synthetic payment, duplicate, mismatch, cancellation/refund and replay receipts | Henry/authorised merchant operator plus independent review | Payment request, live order activation and production work before confirmed payment |
| G5 — full rehearsal and delivery | Full-sized synthetic pack; rendered-file review; real authorised controlled-inbox/private-storage retrieval; wrong-recipient denial; bounce/link failure and source failure; recovery receipts; capacity measured | Sibongile coordinates; independent reviewer and Henry approve route | Paid service release and improvised manual attachments |
| G6 — each order's release | Accepted scope; matched merchant-confirmed payment; every-row QA; corrected version re-reviewed; exact final hashes; approved recipient/route; attribution manifest included | Independent reviewer PASS, then authorised delivery operator | Sending the pack |

The prescribed loop remains: Grok 4.6 xhigh investigation (maximum 120 turns) → checkpoint the four warroom files → Codex gpt-5.6-sol named fix → Grok customer-path retest → DeepSeek V4 Pro frozen-evidence challenge → Hermes next bounded step. If a required provider/reviewer is unavailable, keep that review uncompleted and affected gates closed; agreement among models is not approval.

For outreach, corporate email consent rules differ from sole traders and some partnerships; personal-data obligations still apply. ICO allows consent or a qualifying soft opt-in for individual subscribers, so “sole traders always need fresh consent” is too broad. For new cold prospects, do not assume a soft opt-in. Screen live marketing calls against both TPS and CTPS and existing objections. [ICO B2B guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/business-to-business-marketing/)

## 6. Henry's technical queue: build foundations before connections

The artifact's 55h is a rough backlog estimate, not a measured commitment. Its 17h phase-one total adds correctly, but assumes a reusable scope contract and proven CRM path that do not yet exist end to end. Do not reserve 55h automatically. Confirm Henry's availability and approve one bounded item at a time after investigation.

| Sequence | Item / relationship to original backlog | Deliverable and observable acceptance | Scheduling / estimate |
|---|---|---|---|
| T0 | Source/release and backup-poll repair | Locate/review exact deployed source; independently review c17d1df's scheduling change; once separately authorised and merged, verify default-branch workflow and actual rolling-window outcomes. Do not lower thresholds. | Week 1 priority; estimate after investigation, outside the original 55h |
| T1 | A1 plus minimum A3 contract definition | One versioned schema and explicit supported-category semantics; count distinct nonblank CQC provider IDs, show locations separately; 3 locations under 1 provider means 1 organisation; test category/service/window/exclusion parity and missing IDs. | Week 1 first bounded product task; A1's original 2h excludes full parity work |
| T2 | A2 scope transport | Scope code round-trips the contract without retyping; reject malformed/version-unsupported input; recheck source/counts server/operator side; corruption cannot silently change scope. No personal/payment data in public code. | Week 1 after T1; original 3h provisional |
| T3 | A4 approved run wrapper | Accept only supported scope versions and approved source; check edition identity, hash, freshness and material completeness; refuse stale/unavailable/conflicting input; output PDF, CSV, manifest and run log; zero unsupported filler. | Week 1–2 after T1/T2 and source proof; original 8h provisional |
| T4 | A7 working-day dates | Versioned English public-holiday calendar, Europe/London dates; Friday confirmation → Wednesday without holidays, Thursday with Monday holiday; handle year boundary and late-payment re-agreement explicitly. | Week 1; original 2h provisional |
| T5 | A10 one register and screening | Map tracker fields into contacts/deals/tasks through suitable routes; preserve history and suppression; deduplicate; compare source/import/rejected totals; retry safely; prove permissions and campaign blocking. Import TPS/CTPS results separately. | Week 1–2; original 2h likely incomplete until investigation |
| T6 | Remaining A3 persistence/mapping | Carry service type/category and scope version through stored orders and generation. Coverage returns the candidate universe; generation may rank/truncate it, but cannot add out-of-scope providers. Additive migration only; rehearse rollback/recovery and keep dormant checkout closed. | Week 2 if required by selected route; original full A3 estimate 12h, partly overlaps T1; do not count it twice |
| T7 | A9 read-only payment reconciliation | Match order ID, merchant payment/session ID, amount, GBP currency, status and refund state; duplicate and £745.01 example flagged against approved £745 fee; unmatched payment does not start work. No Stripe writes. | Before first paid slot if automated; original 4h provisional; verified manual matching can be interim approved control |
| T8 | A5 review assistant | Flag planted rating/status/date drift and missing attribution; preserve frozen edition versus later live-check differences; do not silently overwrite evidence; reconcile PDF/CSV and run language guard. Independent reviewer still checks every row. | Week 2–3 only if foundational path works; original 12h provisional; manual full review is the interim control |
| T9 | A6 and A8 follow-ups/dashboard | Sent creates +1/+5 working-day tasks once; retries create no duplicates; seeded dashboard matches register/orders with explicit statuses and denominators. | Week 4 only after two accepted deliveries or demonstrated repeated admin need; original 6h + 4h |

**Timestamp/hash correction:** freeze the actual generation timestamp once per approved run. Replay with the same source, scope, renderer version and frozen timestamp must reproduce the expected deterministic artifacts; check PDF metadata too. A new run receives a new timestamp and hashes may change. Runtime logs may differ and are not part of byte-identical replay acceptance. Record each final file's SHA-256 regardless.

**Source correction:** “same edition as live” is insufficient. Require approved source identity, checksum, accessible input, freshness and completeness checks, plus explicit exception handling. An older event date is not the same as an old snapshot. Resolve the current generator's missing default file/fixed dry-run timestamp through the approved wrapper; do not use the raw dry-run CLI for paid production.

## 7. Daily blueprint: 12 October–10 November

Each weekday below allocates **five Sibongile hours**, including preparation, notes, recovery and buffer. Reviewer/engineering/founder time is separate. Weekends have no scheduled Sibongile work; agreed backup coverage is required for any time-sensitive obligation.

### Week 1 — establish one reproducible service (12–16 October; 25h)

| Date | Sibongile's five-hour allocation | Henry / separate reviewer | End-of-day evidence |
|---|---|---|---|
| Mon 12 | 0.5h roster/inbox setup; 1h offer and buyer question; 1h scope draft; 1.5h source/candidate audit; 1h restricted register | Name backup/reviewer/source owner; reserve time; set pilot cost ceiling; begin T0/T1 investigation | Roster, gate register, source/version record and one proposed scope. No assumed 25-entry promise. |
| Tue 13 | 0.5h operations; 2h eligibility/deduplication checks; 1h category/exclusions; 1h prepare rehearsal record/files; 0.5h buffer | T1 contract/count work and independent verification; start T2/T4 if appropriate | Location count, distinct-provider count, eligible set and written exclusions; supported scope or explicit shortfall. |
| Wed 14 | 0.5h operations; 3h timed synthetic production; 1h review handoff; 0.5h issue log | Reviewer inspects draft against original scope/source; T3 source preflight | Full draft inventory, actual production minutes and defects. If pack not complete, report incomplete rather than substituting a tiny sample. |
| Thu 15 | 0.5h operations; 2h controlled recovery rehearsal; 1.5h reviewer corrections; 0.5h calendar-date checks; 0.5h buffer | Authorised merchant/inbox/file tests only through agreed route; reviewer rechecks corrections | Source failure, rejected scope, payment mismatch/duplicate, wrong-recipient/link/bounce and refund/replay evidence; simulated cases clearly labelled. |
| Fri 16 | 0.5h operations; 1h final pack/register reconciliation; 1h operator/backup handover; 1h dashboard/costs; 1h gate meeting; 0.5h buffer | Independent rehearsal verdict; Henry chooses proceed with discovery, repair, or pause commercial work | Rehearsal PASS or bounded defects; measured labour; named next action. Uncompleted external tests remain open. |

If source/technical access prevents a full rehearsal, use the same hours for internal verification and repairs. Discovery may proceed only under its own approval; no claim that the service is operational follows from preparation.

### Week 2 — test the buyer's decision and willingness to proceed (19–23 October; 25h)

| Date | Sibongile's five-hour allocation | Henry / separate reviewer | End-of-day evidence |
|---|---|---|---|
| Mon 19 | 0.5h operations; 2.5h research first supplier cohort; 1h eligibility/privacy/suppression; 0.5h interview preparation; 0.5h buffer | Clear G3 for actual cohort/channel; resolve T5 access/import gaps | Researched organisations with evidence of fit and permitted contact route; no invented email list. |
| Tue 20 | 0.5h operations; 2.5h finish research towards 20 suppliers; 1h screening and permitted invitations/scheduling; 0.5h approved sample preparation; 0.5h buffer | Review sample/output permission and proposed quote template; T6 if needed | Research ledger and actual communications receipts where authorised; invited is distinct from spoken to. |
| Wed 21 | 0.5h operations; 2h conversations/scheduling; 1h verbatim notes; 1h feasibility for strongest buyer question; 0.5h buffer | Source owner checks scope; reviewer reserves first potential slot | Buyer decision, present method, missing evidence, authority, £745 response and concrete next step. |
| Thu 22 | 0.5h operations; 2h conversations/scheduling; 1h notes; 1h sample/offer refinement; 0.5h buffer | Resolve terms/date/tax and merchant route; T7 or approved manual control | Revised scope version and objections; any sample change reviewed before external sharing. |
| Fri 23 | 0.5h operations; 2h conversations/scheduling; 1h notes; 1h funnel/gate review; 0.5h buffer | Henry permits at most one first paid slot only after G0–G5 and required independent approvals | Up to ten substantive conversations; learning checkpoint; at most one written first-slot offer. Payment is conditional, not scheduled by calendar. |

**Interview prompts:** What territory/account decision is happening now? How do you research it? Which facts would change account priority? Which accounts/service types are excluded? Who approves £745? What is a realistic deadline? What would make the sample unusable? Ask for an actual next step and record objections in the buyer's words.

**Learning threshold:** after ten substantive conversations, seek at least three concrete scope/quote requests with a stated use at the published price. If fewer, change the segment/question or stop outreach expansion. If fewer than ten conversations occur, report insufficient discovery; do not declare the threshold passed from invitations. This small sample is a practical learning rule, not statistical proof.

### Week 3 — deliver the first controlled order (26–30 October; 25h)

| Date | Sibongile's five-hour allocation | Henry / separate reviewer | End-of-day evidence |
|---|---|---|---|
| Mon 26 | 0.5h operations; 1h buyer acceptance; 1h merchant evidence/order match; 1.5h final feasibility/source check; 1h schedule/recipient record | Issue payment request only through approved route; confirm reviewer and delivery slot | Accepted scope, date and terms; real payment evidence or UNPAID; start only when eligible. |
| Tue 27 | 0.5h operations; 3h production; 1h review handoff; 0.5h buffer | Reviewer checks every row and rendered files | Draft files, source manifest and time log; no release before PASS. |
| Wed 28 | 0.5h operations; 1.5h corrections; 1h discovery/follow-up; 1.5h next potential scope; 0.5h buffer | Reviewer rechecks corrected version; Henry considers second slot only within capacity | Frozen first-order review receipt or defect list; second scope feasibility without premature charge. |
| Thu 29 | 0.5h operations; 1h final recipient/route check and approved release; 1h second-order administration; 1.5h feedback/discovery; 1h recovery/buffer | Authorised delivery after G6; no second payment without reserved capacity | Send, inbox/access and customer responses recorded separately; Thursday is an example target only if Monday confirmations made it applicable. |
| Fri 30 | 0.5h operations; 1h next-working-day access check; 1.5h second-order preparation; 1h dashboard/costs; 1h weekly decision/buffer | Review timeliness, actual labour and defects; authorise continuation or stop | First-order access result; second order controlled or deferred; honest weekly dashboard. |

If gates or payment are late, move the order date by explicit agreement and use the allocated hours for rehearsal, repair and discovery. No first-paid-order deadline is guaranteed. The second order may finish in Week 4; that is preferable to an unreviewed rush.

### Week 4 — finish delivery and measure usefulness (2–6 November; 25h)

| Date | Sibongile's five-hour allocation | Henry / separate reviewer | End-of-day evidence |
|---|---|---|---|
| Mon 2 | 0.5h operations; 3h second-order production; 1h review handoff; 0.5h buffer | Reviewer slot and source check; verify calendar after UK clock change | Second draft against its own accepted scope; no reuse of first buyer's private research. |
| Tue 3 | 0.5h operations; 1.5h corrections; 1.5h usefulness interviews; 1h reusable internal template improvements; 0.5h buffer | Independent corrected-file review; T8 only if justified | Review verdict and customer evidence in their words; reusable public-source content kept separate from buyer information. |
| Wed 4 | 0.5h operations; 1h approved second delivery; 1.5h third-scope/capacity check; 1h costs; 1h recovery/buffer | Henry approves third only if it can meet agreed date with reviewer capacity | Second release receipts; third accepted, refused or deferred. Avoid taking payment for a slot outside available capacity. |
| Thu 5 | 0.5h operations; 1h access check; 1.5h +5-working-day usefulness follow-up where due; 1h funnel analysis; 1h recovery/buffer | Consider T9 only after two accepted deliveries; verify financial evidence | Supported decision/action, missing evidence and willingness to repeat; no assumed acceptance from silence. |
| Fri 6 | 0.5h operations; 1.5h outstanding production/corrections; 1h pilot cost review; 1h dashboard/decision draft; 1h buffer | Reviewer clears remaining defects; Henry decides whether to allocate final two days | Four-week results, open obligations and explicit extension/budget decision. |

Follow-up dates are anchored to actual delivery. Example: Thursday 29 October delivery gives Friday 30 October access check and Thursday 5 November usefulness check. The current official calendar lists no English bank holiday during this pilot; recheck it when confirming dates. [GOV.UK bank holidays](https://www.gov.uk/bank-holidays) Daylight-saving time changes on 25 October; use Europe/London for calendar deadlines and UTC for evidence timestamps.

### Days 29–30 — decision and handover (9–10 November; up to 10h extra)

The four weeks above consume **100 operator hours**. A 30-calendar-day window also includes Monday 9 and Tuesday 10 November. Reserve **up to ten additional operator hours only if Henry approves continuation and cost**; otherwise complete the decision materials on 6 November and hold the 10 November founder decision without extra operator work. Do not hide these ten hours inside the 100-hour budget.

| Date | Optional five-hour allocation | Final output |
|---|---|---|
| Mon 9 | 0.5h operations; 1.5h remaining buyer interview/access case; 1.5h final defects/approved delivery; 1h financial reconciliation; 0.5h buffer | Every obligation resolved or assigned with date/owner; actual pilot receipts, hours, fees/refunds and open cases |
| Tue 10 | 0.5h operations; 1.5h decision pack; 1h Henry/reviewer review; 1h next-month or stop handover; 1h buffer | Signed/recorded continue/change/stop decision, next single bounded task, and updated checkpoints; no automatic commercial expansion |

## 8. One order's execution and recovery rules

| State | Entry evidence | Next action / exit evidence |
|---|---|---|
| ENQUIRY_RECEIVED | Actual inbox message and received time | Owner/ID/next-working-day acknowledgement; no order inferred from website click |
| QUALIFYING | Buyer objective and authority | Versioned scope draft, relevance and exclusions |
| FEASIBILITY_CHECKED | Approved source and eligible candidate set | Exact deliverable quantity supported; no padding; reviewer capacity |
| SCOPE_ACCEPTED | Buyer accepted exact version/date/terms/recipient | Reserved slot and approved payment request |
| PAYMENT_PENDING / PAID | Merchant-confirmed ID, status, amount/currency and order match | Begin only when confirmed paid and all applicable gates remain approved; exceptions stay open |
| IN_PRODUCTION | Approved source/scope and payment | Draft PDF/CSV/manifest, evidence and time logs |
| QA_REVIEW | Original scope, source records and exact draft | Independent every-row/rendered-file PASS or defect list; corrections re-reviewed |
| SENT / ACCESS_CONFIRMED | Approved final hashes and actual delivery reference | +1-working-day retrieval/open check; distinguish send from receipt |
| ACCEPTED / FOLLOW_UP | Explicit usable-file acknowledgement | +5-working-day decision interview; no sales-uplift claim |
| RECOVERY / CLOSED | Issue, due date and remedy owner | Correction/revised agreement/refund evidence; stop further sends or new orders when material risk remains |

**Exceptions:** insufficient scope before payment → rescope by agreement or refuse; late payment → re-agree date; source failure after payment → stop and escalate under operative remedy terms; duplicate/wrong payment → merchant owner resolves before production; wrong recipient → stop/revoke access where possible and escalate; bounce/link failure → verify entitlement and repair via approved route; refund requested is not refund completed. A cancelled/refunded order cannot be regenerated and resent through replay without fresh authorisation and entitlement checks.

## 9. Economics, budget and Friday dashboard

The following reproduces the supplied assumptions; it is not measured margin, an assertion about wages, or tax advice. Treat £745 as usable revenue only for this illustration. Henry must recompute using actual VAT/tax treatment, merchant fees and refunds before approving economics.

| Scenario | Arithmetic | Interpretation |
|---|---|---|
| Mature manual Brief | £745 − 8h×£30 − £25 = £480; 64.4% | Includes allocated acquisition/admin/review; possible repeatable-order contribution |
| Hypothetical hybrid Brief | £745 − 5h×£30 − £25 = £570; 76.5% | Three-hour saving is unmeasured; prove via comparable rehearsal/order logs |
| 60% contribution floor | (£745×0.40−£25)/£30 = 9.1h | Total labour cap including review and allocated unsuccessful acquisition; trigger commercial review, never skipped QA |
| Original phase-one estimate | 17h×£30 = £510; £510/£90 saving = 5.67 Briefs | About six Briefs only if the scope is complete and three-hour saving materialises |
| Original full backlog | 55h×£30 = £1,650; £1,650/£90 = 18.33 Briefs | More than 18; **19 whole Briefs** to recover this cost in labour savings; excludes scope additions/maintenance |
| Four-week pilot, two Briefs | 2×£745−100h×£30−2×£25 = −£1,560 | Before separately reserved reviewer/founder/engineering/fixed costs |
| Four-week pilot, three Briefs | 3×£745−100h×£30−3×£25 = −£840 | Same exclusions; zero sales means −£3,000 illustrative operator cost |
| Four-week pilot, four Briefs | 4×£745−100h×£30−4×£25 = −£120 | Sensitivity scenario only; not the scheduled target |
| Optional final two operator days | 10h×£30 = £300 extra | Subtract from whole-pilot result if all ten hours used |

Use **either** per-order allocated labour for contribution **or** the entire operator allocation for whole-pilot economics; do not deduct the same operator time twice. Add actual separate reviewer, founder and engineering hours once. Track cash paid and economic labour cost separately. Booked capacity is not automatically hours consumed.

**Monday 12 October budget decision:** Henry records maximum cash spend, maximum operator allocation, separate engineering/reviewer hours, acceptable validation loss and escalation threshold. If unaffordable, shrink the experiment before committing. A suggested initial planning allocation is up to 17 engineering hours to investigate/build the most necessary foundations, not a promise that all five original phase-one items fit. Re-estimate after T1; later builds require observed need and separate capacity.

Every Friday publish a restricted dashboard from the single register, initially manually reconciled if automation is unproven:

- Eligible suppliers researched; actually authorised/sent invitations; substantive conversations; explicit scope requests; written offers; merchant-confirmed paid orders; independently reviewed deliveries; explicit buyer acceptances.
- Gross receipts, VAT/tax treatment, merchant fees, refunds and other costs; actual operator/reviewer/founder/engineering hours; unit contribution and whole-pilot cost separately.
- Source edition/release, actual rolling poll counts/ratio and gate states; overdue tasks, reviewer capacity, shortfalls, factual defects and recovery cases.
- Buyers naming a decision/action; repeat orders/referrals; reasons lost/refused; next owner/action/date. Use raw counts and explicit denominators; internal usage is not revenue.

## 10. Continue, change or stop on 10 November

| Decision | Evidence | Next bounded action |
|---|---|---|
| Continue cautiously | Required gates approved; no unresolved material defects; two accepted packs and at least two buyers naming supported decisions; costs within approved budget; measured all-in repeatable labour reasonably supports the margin target | Reserve a small next cohort; review actual price/scope/capacity; fund only the next proven bottleneck |
| Extend validation | Safe delivery but fewer than two accepted orders/interviews, or labour evidence too thin | Agree a smaller dated extension and budget; no declaration of product-market fit |
| Change offer/segment | Conversations identify another concrete job or common monitoring scope; fewer than three scope requests after ten substantive conversations | Revise one hypothesis and test it; Digest remains gated until its separate terms/edition/recovery proof |
| Stop commercial progression | Material factual/contract/source defect; uncompleted required challenge; missing reviewer/backup; unapproved route; budget exceeded; unpaid/mismatched order; unresolved recipient/access incident | Protect existing obligations, resolve remedies and checkpoint next repair; no expansion or improvised bypass |

A late schedule alone is not a failure of demand, and a fresh health endpoint is not proof of paid service delivery. Distinguish readiness failure, missing discovery, buyer rejection and operator capacity.

## 11. First 30 minutes on Monday

Henry and Sibongile complete the restricted operator record: name reviewer and backup; confirm hours/access and pilot cost ceiling; choose one buyer question/region; list each gate's current receipt or CLOSED status; reserve the full rehearsal. The technical/source owner then begins one bounded investigation of **scope eligibility from coverage to final output**, while the poll-history/release repair proceeds through its own authorised review path.

## 12. Sources and review boundaries

- [Claude CareGist Hybrid Operating Model](https://claude.ai/artifact/9yTh43J4rZrZ8weELDqSU7#092a092b-83bc), read in the authenticated browser on 11 October.
- Supplied red-team assessment, prepared 11 October; local [PLAN](../../strategy-review/2026-10-11/PLAN.md), [MANUAL_RUNBOOK](../../strategy-review/2026-10-11/MANUAL_RUNBOOK.md), [OPERATOR_RECORD](../../strategy-review/2026-10-11/OPERATOR_RECORD.md), [EVIDENCE](../../strategy-review/2026-10-11/EVIDENCE.md) and earlier [independent document review](../../strategy-review/2026-10-11/INDEPENDENT_REVIEW.md).
- [Public health](https://caregist.co.uk/api/v1/health), [pricing](https://caregist.co.uk/pricing), [Territory Brief](https://caregist.co.uk/pricing/territory) and [terms](https://caregist.co.uk/terms), read-only HTTP checks today.
- Local code at c17d1df: directory-db.ts, TerritoryScopePicker.tsx, territory-scope.ts, territory_brief.py, billing.py, generate_territory_opportunity_brief.py, crm.py, crm_extended.py and health.py. Local findings do not establish deployed code contents.
- [CQC using-data guidance](https://www.cqc.org.uk/about-us/transparency/using-cqc-data); [ICO B2B guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/business-to-business-marketing/); [GitHub scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

This blueprint does not independently reconcile all CQC records, test authenticated CRM access, contact prospects, execute payments/refunds, send files, rerun the application suite, or satisfy the prescribed production challenge. Source counts are observations; demand, labour savings and engineering hours are hypotheses/estimates. Document-quality review is recorded separately and cannot open an operating gate.
