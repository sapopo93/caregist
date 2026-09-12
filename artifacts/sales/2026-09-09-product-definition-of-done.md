# CareGist product Definition of Done

Reference: CG-DOD-2026-V1 implementation adaptation, 9 September 2026.

Purpose: apply the supplied quality standard across the product-polishing plan without inventing evidence, timestamps, qualifications or product capabilities. This is an implementation acceptance checklist, not a legal opinion, certification or product release approval. The original attachment is preserved unchanged.

## Corrections to the supplied checklist

| Supplied requirement | Implementation rule |
|---|---|
| Every ingestion timestamp is 04:00 UTC | Record the actual capture time. Store scheduled time separately. A successful daily reconciliation claim requires run evidence, not a clock label. |
| Zero commentary on CQC latency | Exclude speculation, but retain relevant limitations explicitly published by CQC. Do not conceal source-quality limitations. |
| Every record has a company number and ICB | Require identifiers appropriate to the record. Company numbers need a supported entity match. Geography needs a verified mapping/version. Mark unavailable or inapplicable fields honestly. |
| Missing narratives and scores become Unrated | Preserve source rating terminology. Use “Not stated in reviewed source” for absent narrative, “Not reviewed” where no review occurred, and “Not applicable” where appropriate. |
| SHA-256 proves forensic verification | Hashes identify file integrity. They do not prove factual accuracy, authorship, regulatory compliance or a digital signature. Store full hashes, with short displays expandable. |
| Zero Hallucination Flag / Verified Unmodified | Record the specific checks, source reference, result and reviewer. A boolean assurance flag is not evidence. Normalised values need a transformation record. |
| Every £795 workbook includes distress, breach and decision-maker dossiers | Treat these as requested enrichment requiring primary research and scope reconciliation. They are not present capabilities of the current Brief. Do not fill tabs with inferred allegations or empty assurance labels. |
| Lead Healthcare Regulatory Analyst digital signature | Use a real reviewer, their actual role, review time and version accepted. Claim a cryptographic signature only when a real signing/verification system is used. Never invent a title or person. |
| Zero unmapped IDs in every source batch | Reject unresolved identities in published events. Retain source exceptions and disclose material coverage gaps; do not hide or drop them to produce a zero. |

## Shared acceptance checks

Each applicable check needs PASS, FAIL or NOT VERIFIED, an evidence path, check date and responsible reviewer. N/A requires a reason and must not excuse a promised feature. No boxes below are asserted passed by creating this document.

### Identity, attribution and licensing

- [ ] Display the requested statement without clipping: “CareGist is an independent intelligence provider and does not represent the Care Quality Commission (CQC). Contains public sector information licensed under the Open Government Licence v3.0.”
- [ ] No official emblems, affiliation claims or unsupported professional credentials.
- [ ] Consumer/provider views link to the verified official CQC concern/contact route. Check the phone number before publishing it.
- [ ] Paid deliverables identify the contracting entity when an actual order exists; examples say “Sample” instead of inventing a buyer.
- [ ] Licensing terms distinguish original CareGist analysis from upstream information. Named-person reuse receives its own assessment; OGL is not a blanket licence for personal data.

### Evidence and accurate content

- [ ] Exact source URLs, edition/retrieval dates and source scope are recorded.
- [ ] Publication, inspection, registration, capture and verification dates remain distinct. Unknown dates stay unknown.
- [ ] Displayed events have stable identity, relevant before/after evidence and a defensible event classification.
- [ ] Rating comparisons use compatible service/rating levels. Missing records do not become closures. Registration changes do not become acquisitions without evidence.
- [ ] Every aggregate reproduces from included evidence rows and states coverage/denominator where needed.
- [ ] CareGist interpretation is visibly separate from the public fact. No unsupported staffing, financial, clinical or buying-intent claims.
- [ ] Source hashes match retained files; the same frozen edition drives page, PDF and workbook.
- [ ] Unverified records and material coverage gaps are handled explicitly. No “all clear” when the source failed.

### Deliverable-specific requirements

| Product | Additional completion requirement |
|---|---|
| Free Directory | Accurate search/profile identity, source status, official links, truthful missing values and tested correction paths. |
| £495 Report | A completed 20–35 page edition supported by comparable source evidence; useful findings, limitations and matching supporting files. No immediate-delivery claim before release and delivery are tested. |
| £795 Brief | Agreed buyer criteria; 25–50 distinct organisations with specific reasons; territory Excel/CSV and 3–5 page brief; actual delivery date agreed. |
| Existing £150 pilot | Original four-week scope preserved, dated digest evidence and credible weekly delivery route. No new pilot product implied. |
| Radar Regional/National | Actual history, coverage, ingest/diff, access, export and delivery tests for the promised scope. Request-access remains until release conditions pass. |
| Assignment/Membership | Explicit scope, qualified review where needed, capacity, delivery obligations and product admission. |
| Feed/Enterprise | Schema, authentication, real signing where promised, replay, failure handling, security and contracted scope tested. |

### £795 workbook adaptation

Retain the useful four-tab organisation, but align tab content with the contracted product and evidence:

1. **Selected organisations:** IDs, distinct provider/location names, relevant geography/service information, observed fact, reason under buyer criteria, qualification question and uncertainty. Capacity only when sourced and meaningful to the service.
2. **Territory dataset:** the existing promised export, with all qualifying locations and reproducible filtering. Do not drop it to make space for new dossiers.
3. **Research findings:** source-backed additional inspection or entity research actually performed and included in scope. Mark review coverage. Do not title this a breach matrix or decision-maker dossier unless it contains verified work of that kind. Preserve a useful methodology/selection explanation if enrichment is outside scope.
4. **Sources and checks:** record/event ID, CQC IDs as applicable, source URL and exact locator, source edition/publication date if known, actual capture time, hash reference, transformation/check performed, result, reviewer and review time.

The supplied breach matrix, director links and named-manager research remain an enrichment backlog. Before promising them at £795, complete a sourced example, assess personal-data handling and production effort, and reconcile the exact scope. An absent breach finding must never imply the provider is compliant or non-compliant.

### Design and functional checks

- [ ] Shared warm surface and ink palette; actual text/background combinations pass contrast checks. Status is not communicated only through colour.
- [ ] Source Serif 4 headings, readable body text, true monospace for IDs/timestamps/hashes. Preserve characters and allow full values to be copied. Note: the application currently loads DM Sans and Playfair Display (`frontend/app/layout.tsx`, `frontend/app/globals.css`), so this is a sitewide font change affecting every existing page, not a scoped product-component change. The supplied design reference names its `label-mono` step as Inter, which is not a monospace; this requirement overrides it.
- [ ] Test 390px, 768px and 1280px widths, zoom, keyboard operation, labels and visible focus.
- [ ] Sticky bars and safe-area padding adapt to actual bar height. Footers, controls and disclaimers stay reachable and unobscured; a fixed padding class alone is not a pass.
- [ ] All final PDF pages are visually reviewed. Saved workbook values/formulas, hyperlinks and CSV schema are checked from the exported files.
- [ ] No placeholder source links, invented counters, fake order success, unavailable downloads or unsupported “delivered” badges.
- [ ] Existing permissions, paid-file protection and archived entitlements remain intact. Roadmap products cannot initiate payment.
- [ ] **CONF-1 — no purchasable price exists for a product held closed.** The disabled control on the pricing card is not sufficient on its own. Live Stripe product and price IDs exist for Radar Regional (£299/mo), Radar National (£799/mo) and Intelligence Feed (£6,000/yr), and `deploy/stripe-price-manifest.json` sets `checkout_enabled: true`. Passing requires either those prices archived, or every route into `/api/v1/billing/checkout` audited and shown to reject closed products. Founder decision required; not resolvable by presentation work.

## Completion and release record

Use distinct states: Draft → Evidence checked → Built and tested → Independently accepted → Released. State the actual achieved state. A visually complete mockup is still a draft; a producer test result is not independent acceptance.

The frozen review packet contains scope, claim register, source manifest, final file hashes, test results, limitations and exact candidate version. Follow `.warroom/PIPELINE.md` for independent re-test/challenge. Record a real person's/model's actual role truthfully; do not substitute “clinical analyst” for a software review.

Before external release: confirm legal copy/Terms, VAT/final amount, approved scope, payment and delivery route, then obtain the exact authorization required by the user's existing restrictions. Nothing in the uploaded DoD authorizes sending, publishing, billing activation or production changes.

## Handoff

Objective: incorporate the uploaded DoD into the all-product implementation plan accurately.

Files changed: this adapted checklist and a reference added to the all-products plan. Original attachment and product implementation unchanged.

9 September, later revision: added the CONF-1 acceptance checkbox, recorded the current font stack against the typography check, and revised the exact next action to point at the register built on 8 September. No checkbox was marked passed by this revision.

Checks: read the full attachment; reconciled it with the existing product plan and project operating instructions; distinguished proposed research from verified current deliverables. Official CQC/OGL pages were checked on 8 September in the preceding review; refresh attempts on 9 September returned HTTP 403, so no new legal-source verification is claimed.

Unresolved: enriched regulatory/entity research scope, reviewer identity/signing mechanism, per-product evidence gates, and existing commercial release conditions. All product checkboxes remain unassessed until actual acceptance work.

Exact next action (revised 9 September): the shared claim register already exists at `artifacts/product-polish/claim-register.json` (17 claims, 3 conflicts) alongside `catalogue-evidence.json` and `DESIGN.md`; extend those rather than creating a second register. Next is mapping each £795 preview field to the existing pack and building the local preview with sourced fields, leaving proposed enrichment outside the offer until verified. Continue the £495 comparable-source assessment as the separate report prerequisite. CONF-1 above needs a founder decision in parallel, and the Source Serif 4 / Inter requirement is a sitewide swap from the current DM Sans and Playfair Display.

Sources: [user DoD](/Users/user/.codex/attachments/9b68de50-8c13-4925-9119-b26f91c92b58/pasted-text.txt), [all-product plan](/Users/user/CareGist/artifacts/sales/2026-09-08-all-products-polish-plan.md), [current pack](/Users/user/CareGist/artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/pack-data.json), [operating pipeline](/Users/user/CareGist/.warroom/PIPELINE.md), [CQC source guidance](https://www.cqc.org.uk/about-us/transparency/using-cqc-data), [OGL v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

COMPLETE: no escalation needed. The planning adaptation is complete; this does not mark any product or release Done.
