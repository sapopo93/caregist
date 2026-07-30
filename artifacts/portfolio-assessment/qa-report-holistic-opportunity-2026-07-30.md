# QA REPORT — CareGist Holistic Opportunity Assessment

**QA report ID:** QA-2026-07-30-001
**Deliverable reviewed:** `artifacts/portfolio-assessment/caregist-holistic-opportunity-assessment-2026-07-30.md`
**Producer model/provider:** Codex (exact provider unknown — assessment does not declare producer)
**Reviewer model/provider:** DeepSeek v4 Pro / DeepSeek
**Independence check:** PASS — reviewer provider differs from any plausible Codex/OpenAI producer

---

## Acceptance criteria results

| Criterion | Result | Evidence |
|---|---|---|
| Test factual consistency with live app and repo data | CONDITIONAL | 56,742 conflation (see H-1); rest consistent |
| Live vs roadmap classification accuracy | PASS | Roadmap concepts correctly flagged as unverified |
| 55k locations vs organisations correctly distinguished | PASS | Assessment distinguishes provider graph from location count |
| Buyer and niche completeness | CONDITIONAL | Missing dental/GP buyer language (see M-4); otherwise adequate |
| Competition assessment | CONDITIONAL | Medical Scout/VantageData pricing unverified (see M-2) |
| Revenue arithmetic | PASS | All calculations independently verified (see below) |
| Legal/data/claims risks identified | CONDITIONAL | Country Pack blocker self-identified but UK conclusions drawn (see H-2) |
| Prioritisation logic internally consistent | PASS | Wedge ordering follows evidence and kill criteria |
| Continue/pivot/stop conclusion follows evidence | PASS | Conclusion correctly derived from stated evidence |

---

## Revenue arithmetic verification

All unit calculations independently verified:

- **Plan-only maths (lines 159–166):** All six plan counts × price × 12 months = £1,000,000±300. PASS.
  - 1,701 × £49 × 12 = £1,000,188 ✓
  - 842 × £99 × 12 = £1,000,296 ✓
  - 419 × £199 × 12 = £1,000,572 ✓
  - 167 × £499 × 12 = £999,996 ✓
  - 842 × £99 × 12 = £1,000,296 ✓
  - 560 × £149 × 12 = £1,001,280 ✓

- **Even-ramp month-12 counts (line 168):** Verified using sum-of-months formula (M12 × 6.5 × price = £1m). PASS.
  - Alerts Pro: £1m / (£49 × 6.5) = 3,140 ✓
  - Data Starter: £1m / (£99 × 6.5) = 1,554 ✓
  - Data Pro: £1m / (£199 × 6.5) = 773 ✓
  - Data Business: £1m / (£499 × 6.5) = 308.3 → 309 (acceptable rounding)
  - Provider Pro: 1,554 ✓
  - Sponsored: £1m / (£149 × 6.5) = 1,033 ✓

- **Illustrative bounded year (line 174):** 12 Business + 24 Pro + 50 Provider Pro (even-ramp) + 4 × £15k enterprise + 20 × £500 lead packs = £38,922 + £31,044 + £32,175 + £60,000 + £10,000 = £172,141 ≈ £172k. PASS.

- **Mathematical £1m mix (line 178):** 60 Business + 120 Pro + 250 Provider Pro + 75 Sponsored (all even-ramp) + 12 × £25k enterprise + £170k lists/reports = £194,610 + £155,220 + £160,875 + £72,638 + £300,000 + £170,000 = £1,053,343 ≈ £1.05m. PASS.

---

## No-touch boundary check

The assessment is a read-only document. No files outside `artifacts/portfolio-assessment/` appear to have been modified. PASS.

---

## Security/privacy results

PASS — no secrets, credentials, or personal data exposed in the assessment. Internal token names referenced (HERMES_INTERNAL_TOKEN, SUPPORT_INTERNAL_TOKEN) in the discovery manifest are names only, not values.

---

## Legal/claims/IP results

CONDITIONAL — see findings H-2, M-5.

---

## Mobile rendering results

N/A — text document with no visual surface.

---

## Defects and severity

### HIGH

**H-1: Provider count conflates event-ledger rows with provider rows (lines 9, 21)**
- **Quoted text:** "The current deployed product reports 56,742 active CQC providers tracked" and "56,742 active CQC providers shown as tracked."
- **Evidence:** The discovery manifest (`docs/event-intelligence/discovery-manifest.json`, generated 30 June 2026) shows:
  - `trusted_event_ledger`: 56,742 rows
  - `care_providers`: 56,743 rows
- **Finding:** The assessment uses the trusted_event_ledger row count (56,742) as the "active CQC providers" count. The correct provider count from the same manifest is 56,743 `care_providers` rows. The event ledger count and provider count are different things. The assessment conflates them.
- **Required correction:** Either use 56,743 as the provider count (citing `care_providers` table), or explain why 56,742 is the correct active-provider count. If the ledger count is being used as a proxy, state this explicitly with justification. Throughout the document, ensure the reader understands when a number refers to care_providers rows, trusted_event_ledger rows, or active-subset-of-providers.

**H-2: UK-specific commercial conclusions drawn while Country Pack remains unverified (lines 5, 90, 119, 143)**
- **Quoted text:** "binding country-specific conclusions remain blocked pending a verified Country Pack and qualified review" (line 5), yet the assessment proceeds to make binding UK-specific conclusions about pricing tiers (£49/£99/£199/£499), VAT status ("excluding VAT"), competitive positioning against UK competitors, data-protection posture, and commercial sequencing.
- **Finding:** The assessment self-identifies the Country Pack blocker correctly but then draws UK-specific conclusions that a Country Pack would be required to validate — entity registration, VAT treatment, data controller registration, lawful basis for data processing, and advertising compliance. These conclusions are provisional but are not consistently flagged as blocked.
- **Required correction:** Add a prominent caveat before each section that makes UK-specific commercial or legal conclusions: "This conclusion remains blocked pending a verified UK Country Pack and qualified legal/accounting review." Alternatively, restructure the document so that all UK-specific conclusions sit in a clearly demarcated "provisional — blocked" section.

### MEDIUM

**M-1: "Active" qualifier unverified for the 56,742/56,743 count (lines 9, 21)**
- **Quoted text:** "56,742 active CQC providers"
- **Evidence:** The discovery manifest reports 56,743 `care_providers` rows. The `care_providers` table has a `status` column (observed values include 'ACTIVE'). The manifest does not state whether the 56,743 count is filtered to `status = 'ACTIVE'` or includes all statuses.
- **Finding:** The assessment asserts "active" but provides no evidence that a status filter was applied. The investor report explicitly states "55,818 active care providers" — a different number entirely. If 56,742/56,743 is the unfiltered count, the "active" label is misleading.
- **Required correction:** State whether the count is filtered to `status='ACTIVE'` and provide the filter condition. Reconcile with the investor report's 55,818 active-provider count.

**M-2: Medical Scout and VantageData pricing not independently verifiable (lines 127–128)**
- **Quoted text:** "Public pricing was £45/month for one region and £95/month for full UK" (Medical Scout); "£29/month Starter, £79/month Growth … £149/month Pro" (VantageData).
- **Evidence:** Live review of medicalscout.co.uk on 30 July 2026 shows pricing tiers (Free Trial, Regional, Full UK) but does not display specific GBP amounts without sign-up. VantageData pricing pages could not be extracted. The assessment honestly caveats Medical Scout claims as "observed, not independently validated" but does not apply the same caveat to VantageData pricing.
- **Finding:** Competitive pricing analysis — central to the "severe price pressure" conclusion on line 128 — rests on unverified numbers. The assessment does not state how or when these prices were observed.
- **Required correction:** Add date and method of observation for both competitors. Flag both as "observed, not independently validated." If the VantageData prices came from June 2026 pages (as stated), note they may be stale.

**M-3: "91 providers on 30 July 2026" — evidence is dated 30 June 2026 (line 22)**
- **Quoted text:** "91 providers shown in the live rolling 90-day list on 30 July 2026."
- **Evidence:** The discovery manifest was generated 30 June 2026. The task brief (`caregist-holistic-opportunity-task-brief-2026-07-30.md`) references "Current /search?opportunity=new_90 view showed 91 providers." The brief is dated 30 July 2026 and may reflect a live check on that date.
- **Finding:** The closest independently verifiable evidence is the 30 June manifest. A 30 July live check is plausible but not independently reproducible by this reviewer without authenticated dashboard access. The assessment should clarify whether the 91-provider count is from the 30 June manifest, a 30 July live dashboard check, or another source.
- **Required correction:** State the exact date and method of the 91-provider observation. Distinguish manifest-derived counts from live-dashboard observations.

**M-4: Service-type niche list incomplete — omits dental/GP buyer language and other categories (lines 75–88)**
- **Quoted text:** The assessment correctly notes that Dentists (12,004) and Doctors/GPs (9,367) "should not be mixed casually into a 'care-provider procurement concierge'" and "require separate buyer language." It suggests a parent "CQC market intelligence" product.
- **Finding:** The assessment itself then fails to provide that separate buyer language. The dental and GP segments are the second- and fourth-largest categories by count, yet receive no dedicated buyer analysis, no identified dental/GP-specific competitors, and no dental/GP wedge proposal. The Ambulance, Clinic, and "Other" categories (785 combined in the investor report) are also omitted. This is a completeness gap given the assessment's own recommendation.
- **Required correction:** Either add a brief dental/primary-care buyer analysis (who buys, what they buy, whether CareGist's current data is fit for them), or explicitly scope dental/GP as "deferred to future vertical assessment" with a note that the current three-wedge architecture is social-care-only.

**M-5: Assessment omits direct statement of current revenue (lines 9–13)**
- **Quoted text:** "no demonstrated paying-customer evidence, repeatable acquisition, retention, validated willingness to pay or observed unit economics" (line 11).
- **Finding:** While the assessment correctly states there is no paying-customer evidence, it never explicitly states current revenue is £0. The phrase "not exploiting the whole asset commercially today" (line 11) could be misread as "some parts are commercialised." The £0 revenue fact is foundational to the "do not scale" conclusion and should be stated plainly.
- **Required correction:** Add a direct statement: "Current recognised revenue: £0." This anchors all subsequent revenue scenarios.

**M-6: Entity resolution flagged but unresolved (lines 184–185)**
- **Quoted text:** Phase A calls to "Reconcile entity, VAT, controller and contracting party."
- **Finding:** The user profile identifies two possible entities: N Dumane and H-Kay. The assessment never names either entity or identifies which one currently operates CareGist. The entity question is not tangential — it determines the legal contracting party, VAT registration requirement, data controller registration, and liability. Phase A should identify the specific entity question to resolve.
- **Required correction:** Name the entity question explicitly: "Determine whether CareGist is operated by N Dumane, H-Kay, or another entity, and confirm Companies House registration, VAT status, and ICO data controller registration for that entity."

### LOW

**L-1: Supported Living + Supported Housing arithmetic (line 81)**
- **Quoted text:** "Supported Living + Supported Housing (5,432 combined)"
- **Evidence:** The March snapshot lists Supported Living at 4,727. Supported Housing is not listed as a separate category in the snapshot.
- **Finding:** The 5,432 combined figure implies Supported Housing at 705, but this is not sourced. If Supported Housing is aggregated from another category or census field, state this.
- **Correction:** Either source the 705 Supported Housing figure or remove the "combined" total and list Supported Living alone at 4,727.

**L-2: Business plan even-ramp rounding (line 168)**
- **Quoted text:** "309 Business"
- **Finding:** The exact calculation is 308.3. Rounding to 309 is acceptable but should be noted as approximate. Given the assessment's overall precision, this is minor.
- **Correction:** Change to "~309" or "approximately 309."

**L-3: Carterwood competitiveness claim unsourced (line 130)**
- **Quoted text:** "Carterwood visibly competes on proprietary demand, supply, demographics, staffing, fees, funding mix and expert interpretation for operators and investors."
- **Finding:** No source is provided for Carterwood's specific offerings. Unlike Medical Scout and VantageData, which received live review, Carterwood's capabilities are stated as fact without evidence.
- **Correction:** Either add a source (URL, observed page, report reference) or caveat as "Reported to compete on…"

---

## Decision

**VERDICT: PASS CONDITIONAL**

The holistic opportunity assessment is substantially sound. Its core logic — that CareGist has a real asset but no commercial proof, should preserve the platform, reduce to three wedges, and demand paid evidence — follows from the stated evidence. The revenue arithmetic is correct. The competitive analysis is honest about gaps. The "what not to pursue" section is disciplined and actionable.

**Conditions for unconditional pass:**

1. **Resolve H-1 (count conflation):** Correct the "56,742 active CQC providers" claim to reflect the actual care_providers count (56,743) and explain the relationship to the event ledger count.

2. **Resolve H-2 (Country Pack blocker):** Either consistently flag all UK-specific commercial and legal conclusions as blocked pending Country Pack, or defer those conclusions to a separate gated section.

3. **Acknowledge M-1 through M-6:** The medium findings do not block the founder decision but should be corrected before the assessment is shared externally or used as the basis for Phase B customer discovery.

---

## Required human gate

This QA report does not itself require a human gate — it is an independent review of a read-only assessment. However, the assessment's own recommended founder decision (line 245: "Approve internal preparation of three separate proof briefs") requires **Human Gate 1 (go/no-go and budget)** before any briefs are issued to roles or customers are contacted.

The assessment correctly stops short of live outreach or pricing approval.

---

## Readiness for founder decision

The assessment is **ready for founder review** provided the HIGH findings are corrected first. The founder should read this QA report alongside the assessment. The conditional pass means the strategic conclusion (preserve, wedge-test, demand evidence) stands, but the document contains factual errors that could undermine credibility if presented externally.

Specifically, the founder should:
- Confirm whether the platform tracks 56,742 or 56,743 providers, and whether "active" has been verified.
- Confirm willingness to proceed with UK-specific commercial planning while the Country Pack remains unverified.
- Note that the assessment's recommendation to prepare three proof briefs internally is safe (no customer contact, no spend), so can proceed before Country Pack resolution — but any outreach, pricing communication, or data sharing with customers requires Country Pack + Gate 1 approval.
