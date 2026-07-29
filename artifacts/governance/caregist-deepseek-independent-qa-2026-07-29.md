Read all three files. Now performing the independent cross-examination against all 13 acceptance criteria. I'll cite exact file/line evidence throughout.

---

# QA & RED TEAM REPORT — CareGist UK Support/QA Operating Design

## 1. DELIVERABLES REVIEWED

| # | Deliverable | Producer | File |
|---|------------|----------|------|
| 1 | Customer Support & QA Operating Design | Customer Success & Support (OpenAI Codex GPT-5.6 Sol) | subagent-summary-0 |
| 2 | UK Legal, Risk & Compliance Screening | Legal, Risk & Compliance (OpenAI Codex GPT-5.6 Sol) | subagent-summary-1 |
| — | Task Brief (reference) | — | caregist-qa-support-task-brief-2026-07-29.md |

## 2. REVIEWER INDEPENDENCE

| Role | Provider | Model |
|------|----------|-------|
| Producer (both handoffs) | openai | codex-gpt-5.6-sol |
| Reviewer (this report) | deepseek | deepseek-v4-pro |

**INDEPENDENCE: PASS** — Different provider organisations, different model families and architectures, no shared infrastructure.

---

## 3. ACCEPTANCE CRITERIA TABLE

| # | Criterion | Verdict | Key Evidence |
|---|-----------|---------|--------------|
| 1 | Practical for first revenue/low pilot; safe role combinations | PASS WITH CONDITIONS | subagent-0:76-83 defines 6 roles with permitted combinations; Independent QA separated. But one-person QA has no secondary reviewer (self-reviews unaddressed). |
| 2 | Covers all journeys: search, Free, Alerts/Data, export, claims, enterprise, onboarding, corrections, billing, complaints, privacy, incidents, cancellation, retention | PASS | subagent-0:121-143 covers 23 journey stages; subagent-1:35-53 covers 16 compliance stages. No gaps. |
| 3 | Separates CQC-source, CareGist-derived, provider-submitted | PASS | subagent-0:47-51 three-way classification rule; subagent-0:146-149 data-correction rule per source class. |
| 4 | Prevents CQC affiliation, guaranteed outcomes, unsupported claims | PASS | subagent-0:52-55 five cross-journey principles; subagent-1:146-162 sixteen forbidden actions. |
| 5 | Identity/authority checks for provider claims; payment not proof | PASS WITH CONDITIONS | subagent-0:54,130 payment≠proof principle strong; subagent-1:43 badge not automatic. But actual verification method undefined — "proportionate" is aspirational, not operational. |
| 6 | Auditable support, correction, entitlement, export, incident records | PASS | subagent-0:196-218 minimum support record with 22 mandatory fields; subagent-1:202-218 evidence package. |
| 7 | Separates line support, DQ, engineering, QA, privacy, finance, founder/legal | PASS | subagent-0:99-113 RACI with all seven roles; subagent-0:273 QA reports outside Support line. |
| 8 | UK GDPR/DPA/PECR as provisional controls, not legal conclusions | PASS | subagent-1:170-196 B2B classification/suppression; subagent-1:87-107 privacy and incident paths; explicit "screening draft only" caveat at :18. |
| 9 | VAT/pricing/subscriptions/refunds without legal conclusions or money action | PASS | subagent-1:45-46,129-138; both handoffs state financial decisions are human-gated. |
| 10 | Headcount, sampling, RACI internally consistent and feasible | PASS WITH CONDITIONS | subagent-0:63-72 pilot assumptions explicit; subagent-0:263-269 sampling percentages defined. But SO role overloaded (A/R for 6+ processes), and IQA has zero backup. |
| 11 | Tests fail-open hook, archived support, export token, unselected helpdesk | PASS | subagent-1:295-307 identifies all four: hook fail-open, support archived, token conflated with lead form, no approved helpdesk. |
| 12 | No personal/customer/prospect/claimant data sent to AI | PASS | subagent-0:90,275; subagent-1:157,164,281. Prohibition stated in both handoffs. No evidence of violation. |
| 13 | Distinguishes design from operational/launch readiness | PASS | subagent-0:18 "ready for independent review, but not ready for launch"; subagent-1:18 "cannot establish legal approval or launch readiness." |

---

## 4. NO-TOUCH BOUNDARY RESULT

**PASS.** I read only the three specified files. No other files, no network, no credentials, no production systems, no customer/prospect data, no code modifications. No-touch boundaries intact.

---

## 5. SECURITY/PRIVACY RESULT

**FAIL — BLOCKED.** Six blockers directly relate to security or privacy:

- No approved personal-data purpose map, lawful-basis register, or DPIA (subagent-1:95, 269-270)
- No approved processor/sub-processor terms or transfer mechanisms (subagent-1:280, 335-337)
- CG-LRC-14 (no personal data to AI) lacks technical enforcement — it's a policy statement with no system guard (subagent-1:281)
- The quality hook hard-codes `schemaValid=True` and `hiddenFieldViolations=0`, meaning it cannot detect hidden-field data exposure (subagent-1:301-302)
- No approved retention schedule; deletion/anonymisation untested (subagent-1:279, 338)
- No approved incident runbook; 72-hour ICO window has no operational backing (subagent-1:107)

The handoffs correctly identify these issues. The fact that they are identified is good design hygiene; the fact that they remain unresolved is what blocks operational use.

---

## 6. LEGAL/CLAIMS/COMMERCIAL RESULT

**FAIL — BLOCKED.** Multiple unresolved legal foundations:

- CQC reuse: source terms, licence, field inventory, recipients, and "90-day" rule all undefined (subagent-1:39, 269, 319-321)
- Provider "verified badge" has no verification standard (subagent-1:43, 277, 326-328)
- "All prices exclude VAT" may violate consumer law if any buyer is B2C; B2B/B2C classification not determined (subagent-1:45, 284-285, 327-329)
- "Cancel anytime" is commercially ambiguous and legally untested (subagent-1:46, 331-332)
- IP/company-use chain unresolved — H-Kay cannot commercialise code it doesn't evidence ownership of (subagent-1:288, 337-338)
- No approved terms, privacy notice, or contract exists (subagent-1:268)

The compliance screening (subagent-1) correctly flags all 22 controls as VB/CU/BLOCKED. The openness is commendable but the conclusion is unambiguous: legal readiness does not exist.

---

## 7. FINDINGS — GROUPED BY SEVERITY

### BLOCKER (6 findings — each independently prevents operational acceptance)

**B1 — Governance foundation absent**
- Evidence: task brief :17-25; subagent-1:37, 268
- Impact: No founder intake, no Gate 1, `first_project_eligible=false`, four open risks (UK-004, UK-005, PORT-001, IP-001). The product has no approved existence as a company project.
- Correction: Founder must complete setup intake; Gate 1 must be recorded with scope, entity, brand and portfolio decision; open risks must be closed or accepted with conditions.

**B2 — No approved support platform exists**
- Evidence: subagent-0:437 "No approved helpdesk, CRM, metrics platform, fallback ledger or support retention schedule"; subagent-1:306-307 archived support service not active
- Impact: The entire operating design (ticket taxonomy, support record, QA sampling, severity ladder, service targets) presumes a system that does not exist. Support operations cannot begin without a system of record.
- Correction: Select, security-review, processor-approve, and configure a helpdesk/CRM before any support intake. The archived repository must not be reactivated without full review.

**B3 — Quality hook is structurally unreliable**
- Evidence: subagent-1:298-304; source: `support_quality_hook.py:18-20,38-62,111-122,125-184`
- Impact: `schemaValid=True` hard-coded; `hiddenFieldViolations=0` hard-coded; skips with exit 0 when config/report absent; network errors become warnings. This hook cannot serve as a QA gate — it will silently report success for any failure condition.
- Correction: Rewrite hook as a blocking gate: require config, require report, compute schema validity and hidden-field violations from actual data, fail on any error, emit a retained verdict. Until rewritten, remove it from any automated pipeline that could imply QA approval.

**B4 — CQC data reuse has no legal basis**
- Evidence: subagent-1:39, 269, 319-321; task brief :25
- Impact: Core product proposition (directory, alerts, monitoring, exports, API) depends on CQC data that has no verified licence, no defined field scope, no recipient authorisation, and no defined "90-day" or change-event rules. Continuing development without this is building on sand.
- Correction: Obtain and review actual CQC API/dataset terms; produce a qualified reuse assessment; define field inventory, event definitions, update frequency, and permitted uses/recipients.

**B5 — Provider "verified badge" has no verification standard**
- Evidence: subagent-0:130; subagent-1:43, 277, 326-328; `pricing-snapshot.md:181-196`
- Impact: Pricing promises a verified badge to every claimed provider, but no identity/authority verification process exists. Badge could issue to unauthorised claimants. "Verified" label risks misleading the public and could attract ASA/CMA attention.
- Correction: Define and approve a proportionate identity/authority verification standard before any badge is issued. Disconnect badge issuance from payment. Remove badge promises from pricing until the standard exists.

**B6 — Personal-data-to-AI prohibition has no technical enforcement**
- Evidence: subagent-1:157, 164, 281; subagent-0:90, 275
- Impact: Both handoffs state the prohibition clearly, but without an approved support platform and data workflow, there is no system-level guard preventing a support agent from pasting customer data into an AI prompt. Policy alone is insufficient.
- Correction: Implement technical controls (field-level redaction, AI-route blocks, DLP monitoring) before any customer data enters support systems.

### HIGH (4 findings — must be resolved before operational pilot)

**H1 — Independent QA Reviewer is a single point of failure with no secondary review**
- Evidence: subagent-0:82, 273-274
- Impact: QA must not review its own work, but the design has exactly one IQA person. Who QAs the QA reviewer's sampling decisions, findings, and reports? This creates an unauditable QA function.
- Correction: Either add a second fractional IQA for peer review, or designate an escalation reviewer (with different reporting line) for IQA's own outputs. At minimum, IQA sampling methodology and blocker findings must have a second sign-off.

**H2 — Support Operations Lead is dangerously overloaded**
- Evidence: subagent-0:77, 99-113
- Impact: SO is Accountable/Responsible for: public/Free support, paid-plan entitlements, provider claim verification (A), complaint triage (R unless conflicted), product/knowledge updates, and formal complaint ownership when not conflicted. This is a bus-factor-1 role covering ~80% of customer interactions. The conflict-of-interest provision ("unless conflicted") has no named alternate.
- Correction: Split provider claims from general support or designate an explicit alternate complaint owner. Add a named deputy for SO absence.

**H3 — Subscription and cancellation terms are legally ambiguous**
- Evidence: subagent-1:46-47, 331-332; `pricing-snapshot.md:221-223`
- Impact: "Cancel anytime" could mean immediate, end-of-period, refundable, or non-refundable. UK consumer law treats unclear cancellation terms strictly against the trader. Without approved terms, every cancellation will be a dispute.
- Correction: Draft and legally approve subscription terms specifying commencement, renewal mechanism, cancellation notice period, refund consequences, and post-cancellation data access/deletion. Remove "Cancel anytime" until terms define it.

**H4 — VAT treatment and B2B/B2C classification unresolved**
- Evidence: subagent-1:45, 284-285, 327-333; `pricing-snapshot.md:47-60,193-213`
- Impact: "All prices exclude VAT" plus "+VAT" display may violate the Consumer Protection from Unfair Trading Regulations if any customer qualifies as a consumer. Sole traders and some partnerships buying provider visibility or data exports may be consumers. The classification hasn't been done.
- Correction: Obtain UK-qualified accountant advice on VAT registration, treatment, and display. Classify each product/journey for B2B/B2C applicability. If any consumer sales are possible, display tax-inclusive prices.

### MEDIUM (5 findings)

**M1 — No named backups for critical roles**
- Evidence: subagent-0:87-89 "If only one front-line person is available, sensitive claims, complaints, refunds and privacy cases remain open or blocked"; engineering backup "must be named before live service"
- Impact: Single absence blocks complaint handling and sensitive cases. Engineering bus factor is 1 until backup is named.
- Correction: Name backups for SO, IQA, and Engineering before pilot. Document absence rota.

**M2 — Service targets risk creating perceived SLAs**
- Evidence: subagent-0:243-253 "Data Pro: Priority queue — four business hours"
- Impact: While explicitly "internal pilot targets only," priority language and specific hour commitments will create customer expectations. In a dispute, a tribunal may consider these as representations.
- Correction: Remove specific-hour commitments from any customer-visible material. Frame targets as "aim to respond within" rather than "priority queue — X hours."

**M3 — QA sampling is single-threaded with no calibration**
- Evidence: subagent-0:263-269
- Impact: One person doing 100% S0/S1 + 100% first-10 + 20% routine + 10% random has no peer calibration. Scoring drift, inconsistent finding severity, or missed issues will go undetected.
- Correction: Add quarterly calibration sessions with an external reviewer or second IQA. Document severity assignment rules with examples.

**M4 — Export token conflates lead capture with entitlement**
- Evidence: subagent-1:295-296; `README.md:99-103`
- Impact: Token issues after lead-form write, not after payment/entitlement verification. A token could be obtained without payment, shared between users, or remain valid after cancellation. The `401` check is access control, not entitlement control.
- Correction: Tie token issuance to an approved order/entitlement record. Add expiry, one-time-use or recipient-binding. Add revocation on cancellation.

**M5 — Accessibility compliance not addressed**
- Evidence: subagent-0:445; only mentioned as weakness
- Impact: UK Equality Act 2010 requires reasonable adjustments. Web Content Accessibility Guidelines (WCAG) 2.1 AA is the expected standard for public-facing digital services. Support channels must be accessible.
- Correction: Add WCAG 2.1 AA conformance to the acceptance criteria. Include accessibility testing in QA sampling. Ensure support intake channels accommodate disabilities.

### LOW (3 findings)

**L1 — Pilot cadence may be excessive for volume**
- Evidence: subagent-0:303-326
- Impact: Daily huddles (3/day) plus 5 distinct weekly meetings for ~50 customers and ~10 tickets/day is administratively heavy. Risk of process overhead exceeding support delivery time.
- Correction: Consider merging daily midday and 16:00 checks. Combine weekly Wednesday/Thursday sessions.

**L2 — 22-category ticket taxonomy over-specified for pilot**
- Evidence: subagent-0:160-181
- Impact: With 10 tickets/day, many categories will see zero tickets for weeks. Fine-grained taxonomy creates categorisation overhead without analytical value at pilot scale.
- Correction: Start with 8-10 categories and expand as volume grows. Not a design flaw, just premature optimisation.

**L3 — Daily cadence hours overlap with founder's carer schedule**
- Evidence: subagent-0:71 09:00-17:00; user profile 07:00-18:00 carer
- Impact: Minor. Support is staffed, not founder-dependent. But any founder escalation during working hours faces a 2-hour overlap gap (09:00-11:00 when Henry is still caring, and 17:00-18:00 after support ends).
- Correction: Define an out-of-hours S0 escalation contact path for critical incidents regardless of support desk hours.

---

## 8. DECISION

**FAIL — 6 BLOCKERS and 4 HIGH findings prevent operational acceptance.**

The design is internally well-structured, honest about its limitations, and correctly identifies its own unresolved dependencies. But good structure does not cure missing foundations. A house with excellent blueprints but no land title, no planning permission, and no foundation cannot be occupied.

---

## 9. EXACT MANDATORY CORRECTIONS (in dependency order)

1. **Founder setup intake + Gate 1** — Entity, product scope, brand, portfolio eligibility, and launch-candidate decision recorded in the approval register. Closes or accepts UK-004, UK-005, PORT-001, IP-001 with conditions. (Unblocks governance foundation.)

2. **CQC reuse assessment** — Obtain and review CQC API/dataset terms. Define exact fields, "new provider," "change event," and "90 days." Produce a qualified legal opinion on lawful reuse for each product journey. (Unblocks core data pipeline.)

3. **Provider verification standard** — Define identity/authority evidence tiers, scope/location binding, expiry/reverification rules, and the operational process for claim review. Separate from payment. (Unblocks verified badge.)

4. **Helpdesk/CRM selection and approval** — Select platform, complete security review, sign processor agreement, configure ticket taxonomy and support record schema, test access controls and data minimisation. (Unblocks support operations.)

5. **Quality hook rewrite** — Replace fail-open hook with a blocking gate that requires config/report, computes actual schema validity and hidden-field violations, fails on any error, and retains a signed verdict. (Unblocks QA automation.)

6. **Subscription terms and VAT treatment** — Draft and legally approve terms covering commencement, renewal, cancellation, refunds, and post-termination data. Obtain accountant advice on VAT registration and display. Classify B2B/B2C per product. (Unblocks commercial operations.)

7. **IQA secondary reviewer** — Name a second reviewer for IQA's own sampling, blocker findings, and quarterly calibration. (Unblocks QA independence completeness.)

8. **SO role split or deputy** — Designate an explicit alternate complaint owner. Add named deputy for SO absence. (Unblocks operational resilience.)

9. **Personal-data-to-AI technical enforcement** — Implement field redaction, AI-route blocking, or DLP monitoring in the support platform before any customer data enters it. (Unblocks data security enforcement.)

---

## 10. SAFE MINIMUM VIABLE PILOT STRUCTURE

For a pilot serving ≤50 organisations with ≤10 tickets/day, the minimum safe staffing is:

| Seat | Minimum | Notes |
|------|---------|-------|
| Support & Customer Success Lead | 1 named person + named deputy | Covers triage, onboarding, retention. Deputy handles complaints when SO is conflicted. |
| Data Quality & Claims Analyst | 1 named person (fractional acceptable) | Covers corrections, claim evidence, source classification. |
| Engineering/Security Resolver | 1 named person + named backup | Covers defects, auth, exports, incidents. |
| Independent QA Reviewer | 1 named person + escalation reviewer | Escalation reviewer (different reporting line) reviews IQA's own blocker findings. |
| Human approval functions | Founder + external advisers | Gates only; not operational staff. |

**Unsafe combinations to avoid:**
- IQA must never also be the SO or the person whose tickets are sampled.
- The escalation reviewer for IQA must not report through Support.
- Engineering resolver must not QA their own critical fixes.
- Finance approver must not be the person requesting the refund.
- Privacy/compliance must not be the person whose conduct generated the complaint.

**The 6-role model in subagent-0 is proportionally heavy for pilot but structurally sound if all "fractional" labels are honoured and the IQA escalation reviewer is added.**

---

## 11. REQUIRED HUMAN GATES IN DEPENDENCY ORDER

| Order | Gate | Approver | Depends on |
|-------|------|----------|------------|
| 1 | Founder setup intake | H-Kay founder/director | Nothing — first action |
| 2 | Gate 1: product scope, entity, eligibility, brand | H-Kay founder/director | Gate 1 above |
| 3 | CQC reuse legal opinion | UK-qualified lawyer | Gate 1 above |
| 4 | IP/company-use assignment or licence | H-Kay founder + UK IP lawyer | Gate 1 above |
| 5 | Privacy: controller/processor map, purposes, lawful bases, DPIA, notices, rights, retention, ICO fee, processor contracts, transfer mechanisms | Privacy lead/qualified adviser | CQC reuse (to map personal data fields) |
| 6 | VAT/accounting: registration status, price display, invoicing | UK-qualified accountant | B2B/B2C classification |
| 7 | Finance: PSP, billing, refund/chargeback authority, reconciliation | Authorised finance approver | VAT treatment, terms |
| 8 | Provider verification standard | Compliance lead + privacy sign-off | Gate 1 above |
| 9 | Support platform: selection, security review, processor agreement, data minimisation | Security + privacy + finance | Privacy gate above |
| 10 | Commercial terms: subscriptions, cancellation, refunds | Legal + finance + product | VAT, verification standard |
| 11 | Marketing/publishing: claims, pricing display, channel classification, suppression | Publishing approver + legal + privacy | Terms, VAT, CQC reuse |
| 12 | Security: access model, MFA, secrets, exports, API/webhooks, logs, incident runbook, backup/restore | Named security owner | Platform, privacy |
| 13 | Final launch: residual risk acceptance | Founder + all applicable owners | All above |

---

## 12. DESIGN READINESS vs OPERATIONAL READINESS vs LAUNCH AUTHORITY

| State | Verdict | Evidence |
|-------|---------|----------|
| **Design readiness** | CONDITIONAL PASS | The operating model (subagent-0) and compliance screening (subagent-1) are internally consistent, honest about gaps, and cover all required journeys. They are suitable as design artefacts for planning and further work. |
| **Operational readiness** | FAIL | Cannot operate without: approved helpdesk (B2), functional quality hook (B3), provider verification standard (B5), IQA secondary reviewer (H1), SO deputy (H2), named engineering backup (M1). The design describes what operations should look like; it cannot yet be executed. |
| **Launch authority** | FAIL — NOT GRANTED | Gate 1 absent (B1). CQC reuse unapproved (B4). Subscription terms, VAT, and B2B/B2C classification unresolved (H3, H4). IP ownership unconfirmed. No customer contact, payment, publishing, or data processing is authorised. |

---

## 13. ASSUMPTIONS, KNOWN WEAKNESSES, AND COMPLIANCE FLAGS

### Assumptions made by this review
- CQC data is presumed licensable for commercial reuse — this has not been verified and may prove false.
- UK Country Pack v0.2 provisions are treated as researched baselines, not legal advice.
- The pricing snapshot reflects intent, not approved offers.
- Pilot volumes will genuinely stay at ≤50 organisations and ≤10 tickets/day.
- Henry as founder/director is available and willing to execute all human gates.

### Known weaknesses of this review
- I have not inspected the CQC API terms or licence — they were not in the permitted files.
- I have not tested any code, endpoints, authentication, or data pipelines.
- I cannot verify whether the archived support service contains personal data.
- I have not reviewed actual lead/intelligence data structures for personal-data fields.
- The legal/compliance screening (subagent-1) is itself a screening, not legal advice — my review of it inherits that limitation.

### Compliance flags (from both handoffs and this review)
- RED: Launch blocked — Gate 1 absent.
- RED: CQC reuse blocked — licence/terms undefined.
- RED: Provider badge blocked — verification standard absent.
- RED: Personal data to AI prohibited — technical enforcement absent.
- RED: Processor/transfer approval absent.
- RED: IP/company-use chain unresolved.
- AMBER/RED: Pricing/subscription — VAT and cancellation terms unresolved.
- AMBER/RED: Export/API/webhooks — purpose, recipient, security controls unapproved.
- AMBER/RED: Support platform — archived dependency and fail-open hook.
- GREEN only for: internal design review and planning without customer data or external action.

---

## 14. FINAL STATEMENT

This QA review is itself a design review. It confirms that the two producer handoffs are competent, honest, and structurally sound as planning artefacts. But it must also confirm — as the handoffs themselves do — that CareGist is not ready to operate, support customers, process data, take payment, issue badges, publish claims, or launch.

The 6 blockers are all pre-operational governance and infrastructure gaps. None is a failure of the design documents themselves. The design documents correctly identify their own limitations. But a design that correctly says "I am not ready" must be believed.

**Decision: FAIL. Do not proceed to operational pilot. Complete the 9 mandatory corrections in dependency order before re-review.**

---

*QA completed: 2026-07-29. Reviewer: deepseek-v4-pro. Next review contingent on evidence of mandatory corrections 1-4 at minimum.*
