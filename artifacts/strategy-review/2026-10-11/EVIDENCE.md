# Evidence boundaries and review record

11 October 2026. This packet supports a strategy and manual-process assessment. It does not prove commercial readiness, certify CQC facts, authorise outreach or approve a release.

**User inputs**

- The seven-play strategy and £10,450 target were supplied for red-team review, not execution.
- User nominated Sibongile and confirmed 25 hours/week (also described as five hours/day). Five working days is the schedule assumption.
- No explicit permission to send messages, charge/refund, change production or activate gates was given in this request.

**Current observations**

| Evidence | Method / time / result | Limits |
|---|---|---|
| [home.json](home.json) | Public HTTP GET; live browser also inspected. 998 new, 35 Inadequate, 2,279 Requires Improvement, exact-label no-published-rating 0. | Displayed counts; no independent location-by-location reconciliation. |
| [data-status.json](data-status.json) | GET and rendered browser inspection. 7 October edition, retrieved 10 October 18:02 UTC, reconciled 11 October 06:10 UTC; 57,129 checked, 57,127 success, 2 failures. | Public service assertions; two persistent-detail-404 exceptions disclosed; source CSV not reprocessed here. |
| [health.json](health.json) | GET 06:48:29 UTC. Source/feed fresh; checkout false; delivery disabled; shadow coverage 14/24 and false. | Health predicates are not service-delivery evidence. Latest successful run is not proof of all scheduled coverage. |
| [directory-health.json](directory-health.json) | GET 06:48:28 UTC; DB read/write; notification capability email. | Configuration/capability does not establish actual mailbox receipt or staffed inbox. |
| [pricing.json](pricing.json) | GET 200; £745 Brief / £150 four-week Digest; both enquiry routes. | Not payment, demand or approved Digest delivery terms. |
| [territory.json](territory.json) | GET 200 plus browser scope selection, free calculation and email fallback expansion. | No mailto send, enquiry submission, purchase or clipboard send. |
| [coverage.json](coverage.json) | Real public read-only calculation (POST semantics are a query). West Midlands/new_90/Homecare Agencies, 21 matches, partial, canCheckout false, latest registration/inspection 7 October. Browser result matches. | No distinct-provider reconciliation. Latest registration/inspection is not observation latency or snapshot age. |
| [terms.json](terms.json) | GET 200, v2.1, effective 9 September. Brief prepayment/scope/source/target/remedy wording present; Digest omitted, older products present. | Reading published terms does not prove legal approval or interpret enforceability. |
| Release identity | Both health endpoints and coverage report `0fda3cac8b670ed3dddb31ac3c45644ca430e387`. | This object unavailable in local Git; deployment source contents not independently pinned here. |
| Local code | HEAD `c17d1df9b6214664d650274ac12e9f181fcf5ad7`. Generator service_type and qualification_question fields; checkout mapping lacks service_type; scope lacks picker signal group; coverage COUNT(*) location rows; exact no-published-rating predicate. | Local implementation inspection, not deployed-source proof. No code edits in this task. |
| [targeted-generator-tests.txt](targeted-generator-tests.txt) | `.venv/bin/python -m pytest tests/test_territory_brief.py -q -k 'qualification_question or service_type'`: 5 passed, 36 deselected. | Only these local field/output/filter tests. Not a full suite, deployed pack review or external journey. |
| [9 October audit](../../buying-audit/2026-10-09/BUYING_PROCESS.md) | Historical paid journey, product and recovery gaps used as leads for inspection. | Older missing-field/source claims are superseded where current evidence differs. Earlier test totals were not rerun. |
| [01:00 nightly report](../../cqc-nightly/2026-10-11-report.md) | Historical before 06:10 reconciliation. | Its 433-hour freshness and 104-defect findings are not repeated as current. Cached classification limitations remain attached to that report. |

The browser also showed an existing two-item comparison selection. It was unrelated to this task and was left untouched. Browser inspection covered the current desktop enquiry flow; responsive layouts, accessibility audit, buyer-specific files and external transactions were not tested.

**External claim checks**

| Source | What it supports / does not support |
|---|---|
| [Clyde & Co, 18 March 2026](https://www.clydeco.com/en/insights/2026/03/rebuilding-oversight-cqc-announces-key-changes-to) | Reports the historical November comparison and risk-based prioritisation. It does not establish present conversion rates or an individual provider's next inspection. |
| [CQC December update](https://www.cqc.org.uk/about-us/improving-how-we-work/1225-update) | Search-index excerpt says 50% more completed assessments in November 2025 than November 2024. Direct opening returned 403; full page was not independently read. |
| [RLDatix/QCS supplied page](https://www.rldatix.com/en-uki/resources/cqc-the-shift-away-from-single-assessment-framework-and-what-it-means-for-social-care/) | Retrieved page describes up to 24 KLOEs and says rollout next spring, contradicting the supplied year-end wording. It is secondary context, not definitive current rollout authority. |
| [CQC March update](https://www.cqc.org.uk/news/our-march-update) | Primary source: four draft sector frameworks, KLOEs replacing statements, pilot/testing process. Does not establish a current definitive launch date. |
| [CQC May bulletin](https://content.govdelivery.com/accounts/UKCQC/bulletins/417f788) | Primary bulletin dated 19 May 2026; piloting and evolving timelines. Not a current launch-date announcement. |
| [CQC using-data page](https://www.cqc.org.uk/about-us/transparency/using-cqc-data) | Page updated 2 October; API/data sheets available, bulk file lacks emails, system-change delays, different rating levels, archiving not necessarily closure. |
| [Supplied Apify actor](https://apify.com/scrapesage/uk-cqc-care-provider-leads) | Could not retrieve via web tool; exact $8/1,000 claim NOT VERIFIED. No substitute actor's price used. |
| [ICO B2B guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/business-to-business-marketing/) | Corporate/individual subscriber distinction and personal-data obligations. Page says guidance is under review. The plan does not authorise a recipient list or replace review of the actual campaign. |

**Claim-to-output quality checks**

| Promised assessment | Intended reader | Source of truth | Output / pass condition |
|---|---|---|---|
| Red-team seven plays | Henry | Supplied plan, current pages, primary sources | PLAN.md addresses all seven and separates hypothesis from observed fact. |
| Current buying process | Henry and Sibongile | Actual browser flow, saved current pages and health | Record enquiry-only behaviour, payment/delivery unverified; do not infer receipt from mailto. |
| Who does what manually | Sibongile | User availability plus explicit proposed roster | Runbook assigns operator tasks, identifies unassigned reviewer/backup and separate commercial authority. |
| Feasible labour/revenue plan | Henry | User's 25h/week, transparent assumptions | Recomputable formulas, setup/sales/review/support budgets, conditional revenue and stop rules. |
| Concrete next actions | Both | Current open product/source/operational gaps | Date/owner/output/decision for four weeks, one first bounded technical task and reusable operator record. |
| No misleading readiness conclusion | Both | Project gates and current evidence limits | Report/document review never opens the commercial gates or substitutes for named reviewers. |

Independent review is recorded in [INDEPENDENT_REVIEW.md](INDEPENDENT_REVIEW.md). It identified no critical defect and requested two P2 corrections: whole-pilot economics and explicit output licence attribution. Both were added to the final documents and independently rechecked: PASS WITH LIMITS, no critical document defect remaining. The limits in that review remain operative. This is a review of the plan's correctness and usefulness, not approval of a CareGist release.

Final routine checks: all local Markdown file links resolve; weekly allocations sum to 25 hours, daily allocation to five hours, total-order allocation to eight hours; both whole-pilot calculations were recomputed. `artifact-manifest.json` pins the completed packet. No full backend/frontend suite was run because this task changed documents only; the five targeted generator tests checked whether old audit findings had been addressed locally.
