# Independent adversarial document review

11 October 2026. Reviewed PLAN.md, MANUAL_RUNBOOK.md, OPERATOR_RECORD.md and EVIDENCE.md against the original seven-play request and Sibongile's confirmed 25 hours/week. This is document review only; it is not the prescribed Grok/DeepSeek challenge, source approval or commercial activation.

**Verdict: no critical factual or gate-bypass defect found. Pass with limits after the two bounded clarifications below.**

## Findings

1. **P2 — Show month-one economics alongside hypothetical mature-order contribution.** PLAN.md section 4 says “Brief, disciplined process … £480 / 64.4%” and then proposes two to four sales against a 100-hour operating allocation. The unit arithmetic is correct and assumptions are explicitly labelled, but the plan never computes the cash/economic result of its actual first-month allocation. At the same £30/hour assumption, if all 100 operator hours are used, operator labour alone is £3,000. Two orders yield £1,490 less £3,000 and £50 other variable costs = **−£1,560**; four yield £2,980 less £3,000 and £100 = **−£120**, before separately reserved reviewer/founder/engineering costs. This is an illustrative economic cost, not an assertion about wages paid. Correction: add this range and explain that setup/learning is an investment; the 64.4% scenario is not the month-one margin. Separate repeatable fulfilment economics from all-in pilot economics. Acceptance: reader cannot mistake £1,490–£2,980 gross for a profitable first month, and actual hours are charged only once.

2. **P2 — Make export attribution a checklist item.** MANUAL_RUNBOOK.md's production/review checklist and OPERATOR_RECORD.md's deliverables fields capture source metadata but omit the explicit CQC/Open Government Licence attribution check. Saved terms.json section 9 expressly says exports must retain supplied CQC/OGL attribution and source metadata. This matters particularly for manually produced files, where automated templates may be bypassed even on an approved route. Correction: require the agreed CQC/OGL attribution and source metadata in both the PDF and CSV (or their approved accompanying manifest where appropriate), and include this in independent review. Acceptance: the operator record has an attribution check referencing the exact final artifacts. This is checking an existing published requirement, not a new legal opinion.

## Independently checked

- health.json reports 7 October source, 57,129 checked, 57,127 successes, two failures, 06:10 reconciliation, fresh predicates, 14/24 shadow polls, checkout false and delivery disabled. The documents correctly supersede the 01:00 stale-source claim without claiming all historic defects resolved.
- home.json supports 998 / 35 / 2,279 / exact-label zero; data-status.json explicitly distinguishes source publication, retrieval and reconciliation and discloses the two 404 exceptions.
- coverage.json confirms the chosen West Midlands/new_90/Homecare Agencies query returned 21 with checkout false. Local frontend/lib/directory-db.ts counts location rows with COUNT(*), supporting the separate-provider warning. Local exact-label predicate was checked in directory-query-clauses.ts.
- Local api/routers/billing.py scope mapping omits service_type; api/services/territory_brief.py TerritoryScope includes service_type but no signal category. Saved targeted test output reports five passed and 36 deselected. Documents do not turn these local observations into deployed-code proof.
- Saved terms support advance payment, cancellation before work, source-failure remedies, three-working-day target after scope/source confirmation, and 25–50 organisations with CSV and a 3–5-page executive brief. The proposed written-date handling is sensible and identified as an agreement requirement.
- Per-unit arithmetic, shared Digest arithmetic, original target arithmetic, 120–220-hour range, 9.1-hour contribution threshold and each weekly 25-hour allocation recompute correctly.
- The runbook covers enquiry receipt, eligibility, scope acceptance, payment evidence, independent review, access, explicit acceptance, failure, refund and operator absence. Unstaffed specialist roles are openly identified, rather than assigning all of them to Sibongile.
- All seven plays are challenged. The preferred buyer segment and targets are explicitly hypotheses. The own-product conflict/non-exclusivity point is useful.

## Limits

No production call, merchant action, outbound communication, source reprocessing, actual buyer pack or rendered PDF/CSV was exercised in this review. External market-source pages were not independently reopened by this reviewer; their retrieval boundaries are recorded in EVIDENCE.md. Browser interaction claims rely on the producer's record plus saved page/query evidence. No customer demand, actual labour cost, staffed reviewer or functioning commercial service is established. The plan should remain a proposed operating experiment with gates closed.

## Recheck disposition — 11 October 2026

Re-read the final changed paragraphs and template fields. **Both P2 findings are resolved. Final document verdict: PASS WITH LIMITS for the proposed strategy and manual operating plan.**

- PLAN.md now explicitly computes the −£1,560 to −£120 pilot result at the stated assumptions, excludes separately reserved specialist/fixed costs, distinguishes economic cost from actual cash pay, warns against double-counting operator hours, and requires an acceptable pilot cost ceiling. The numbers recompute correctly.
- PLAN.md, MANUAL_RUNBOOK.md and OPERATOR_RECORD.md now require CQC/OGL attribution and source metadata in the final PDF and approved CSV manifest/README. The runbook preserves importable CSV structure, requires delivery of that manifest and includes it in the final hash record. These changes meet the document-review acceptance test.

No critical document defect remains within the inspected scope. All original review limits continue to apply: this is not execution of the manual service, buyer validation, source certification, legal approval, production readiness or the prescribed commercial independent-review gate. No commercial gate is opened by this verdict.
