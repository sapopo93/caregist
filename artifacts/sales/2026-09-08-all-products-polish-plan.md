# CareGist product range: accurate content and delivery design plan

Objective: bring every current CareGist product and roadmap presentation to the same clear, polished, evidence-backed standard. This expands the £495 plan across the catalogue. Planning is complete; implementation and commercial release are separate work.

9 September update: apply the [adapted product Definition of Done](/Users/user/CareGist/artifacts/sales/2026-09-09-product-definition-of-done.md) to implementation and acceptance. It preserves the supplied quality intent while correcting forced timestamps, missing-field labels and unsupported research/signature claims. No product checks are passed by this planning update.

## Catalogue and status

Primary authority is the 7 September founder decision, reconciled with the current local `PRICING_LADDER` and preparation manifest. Local copy is evidence of what is written, not proof of working capabilities or live deployment.

| Product | Documented price / public treatment | Design and deliverable target | Required proof before capability claims |
|---|---|---|---|
| Free Directory | £0 | Search, useful provider/location profiles, source dates, exact official links and factual issue reporting. | Search/filter results match records; provider/location identity and missing ratings are represented correctly; no inferred compliance or intent. |
| Market Movement Report | £495 one-off, launch preparation | Dated 20–35 page edition, supported movement findings, useful regional comparisons, source evidence and proposed supporting workbook. | Compatible source editions, reproducible event ledger and a completed checked edition. “Immediate” only after actual availability and delivery testing. |
| Territory Opportunity Brief | £745 one-off, lead launch preparation | Buyer scope, 25–50 distinct organisations with meaningful reasons, territory Excel/CSV and 3–5 page executive brief. | Criteria agreed with buyer; every selection sourced; files and schema checked; delivery start/date agreed. Existing 25-provider sample is a starting point, not proof of buyer fit. |
| Existing Radar founding-buyer pilot | £150 for existing four-week offer | Clear scope and edition dates, four weekly digest deliveries as agreed, evidence links and accurate delivery record. | Verify the promised cadence/data route before accepting payment. Preserve terms for the three recorded contacts. No new pilot sends without a fresh decision. Do not rename it a one-provider or five-provider audit. |
| Radar Regional | Request access, no paid checkout. £299/month exists in manifest, not approved for current sale. | Regional event feed, evidence details, view saving and delivery settings matching capabilities actually proven. | Verified ingest/diff history, truthful freshness status, deduplication, delivery checks, regional boundaries, tested limits and access control. |
| Radar National | Request access, no paid checkout. £799/month exists in manifest, not approved for current sale. | Consistent national view with regional filters, evidence, exports and onboarding. | National coverage and history, scope consistency, permissions, promised limits and reliable delivery. Not established by a regional sample. |
| Strategic Territory Intelligence Assignment | Roadmap, documented future starting price £3,500 | Scoping document, research question, method, milestones and agreed outputs. | Evidence/history gate and product admission; buyer-specific scope, capacity, method and review. No invented investment advice or standard outputs. |
| Founding Intelligence Membership | Roadmap, documented future £4,500/year, cap three | Clearly defined continuing service, schedule, capacity and scope limits. | Evidence/history gate, explicit service definition, repeatable delivery and sustainable capacity. Frequency and response promises remain undefined. |
| Intelligence Feed Pilot | Roadmap. £6,000/year appears in manifest, not validated for sale. | Example schema, event semantics, versioning, delivery/error behaviour and integration guide. | Tested API/auth, actual signing and verification, replay/idempotency, cursor stability, rate/usage terms, monitoring and agreed service scope. |
| Embedded Enterprise | Roadmap, no current quote or checkout | Accurate scope discovery and a future proposal structure for embedding, access and support. | Technical/security/procurement review, tenant boundaries, contractual terms and explicit deployment/support scope. Do not imply these exist because they appear in copy. |

Free listing correction/claim presentation is part of the Directory, subject to existing claim gates. A verified claimant is not a CQC quality endorsement. Historical paid Provider Pro, sponsored listings, Starter/Pro/Business and other archived products remain compatibility/support records. Do not resurrect them or alter existing entitlements during polishing. This covers the current catalogue, in-flight pilot and archived-product boundary; it does not create additional SKUs.

## One shared presentation standard

Use the supplied editorial style across product pages, previews, PDFs and workbooks: warm off-white surfaces, Source Serif 4 headings, Inter body, dark primary actions and restrained semantic colour. Resolve the conflicting token values in DESIGN-caregist.md into one source of truth before implementation.

Every product presentation must answer:

1. Who is this for and what decision or task does it support?
2. What exactly does the client receive, in which formats and scope?
3. What is included, what is excluded and what is still unknown?
4. Which source period and checks support the example?
5. What is the documented price, tax treatment, delivery basis and next action?

Use the same component vocabulary: product/scope header, deliverables panel, sample, source details, limitations, price/status panel and next step. Tailor the client experience to the product; a report reader, account shortlist and integration guide should not all become a signal-feed screen.

Source dates and edition IDs should come from the content model. Prices should come from a controlled catalogue. Status must be explicit: free, launch preparation, existing pilot, roadmap or archived. Prevent a roadmap product from inheriting a purchase CTA. Keep VAT unknown in internal preparations until confirmed, rather than calculating a public total from an assumption.

Customer-facing language should describe the work: “Published fact”, “Why included”, “What to check next”, “Source”, “Checked on”. Remove repeated “statutory”, “forensic”, “clinical” and “audited” language unless the actual service and checks warrant it. No invented team, signature, testimonial, fulfilment status or demand metric.

## Product-specific client experiences

**Directory:** useful results and profiles. Show the right identity, service categories, geography, published rating and source/check dates. A blank rating remains distinct from Not Rated or not inspected. Do not imply current compliance from a colour badge. Claims, corrections and source status need clear explanations and tested forms before being offered as working flows.

**£495 Report:** edition overview → sample findings → report reader/downloads → evidence appendix. All chart totals and event cards derive from one ledger. Keep commentary separate from recorded change. Follow the detailed report plan linked below.

**£745 Brief:** agreed buyer scope → executive findings → 25–50 account cards → editable dataset → evidence. Reuse the completed Birmingham/Solihull pack for the prototype. Show its actual 353 locations, 329 providers and 25 selected organisations only in that exact scope. Add buyer-specific reasons before paid delivery. Do not promise bespoke analysis in the prepared £495 edition.

**£150 in-flight pilot:** dated digest with coverage, what was verified, evidence and limitations. “No verified changes” is not the same as “data unavailable”. Keep communication/history distinct from a fulfilled delivery record. Do not upgrade, discount or change existing prospect terms as part of visual work.

**Radar products:** future feed → filters → evidence detail → saved views → delivery/history. Derive all counters from results. Explicitly represent stale, partial, failed and unavailable states. Retain request-access/roadmap presentation until the capability gates pass. No fake match counters or “04:00 reconciled” badge driven only by a scheduled time.

**Assignment/Membership:** future service definition pages, with clear boundaries and no pretend dashboards. Define the actual research/continuing service before promising calls, analyses, refreshes or delivery SLAs.

**Feed/Enterprise:** developer and buyer documentation, accurate schema examples clearly marked illustrative, integration responsibilities and scoped acceptance criteria. Operational tools, signatures, security claims and uptime promises require implementation evidence before promotion.

## Implementation sequence

### Wave 1: content and catalogue foundation

Inventory product statements in pricing/config, homepage, directory, provider pages, emails/templates, samples and downloadable documents. Create a claim register: product, statement, source, verification, allowed wording, exclusion and release status. Flag stale prices and conflicting terminology. Define design tokens and a reusable product-page structure.

**Built 8 September; do not rebuild.** `artifacts/product-polish/catalogue-evidence.json` (10 products), `artifacts/product-polish/claim-register.json` (17 claims, 3 conflicts) and `artifacts/product-polish/DESIGN.md` (resolved token conflict; monospace rule corrected 9 September) now exist. Extend these files rather than creating a second register, which would diverge. Each is planning/build evidence, not an external release. Inspect nested instructions and current dirty files before choosing code edits.

**Check:** every current product is represented; archived products are excluded from new sales; no unsupported claim is silently upgraded to verified. Price/status wording aligns with the controlling decision.

**State reached: Evidence checked (producer self-assessed).** Not built, not independently accepted. The four checks above were assessed by the producer against files read in-session; no live-state, delivery or capability test was performed. Independent acceptance per `.warroom/PIPELINE.md` has not occurred.

### Wave 2: first-sale deliverables

1. Build the £745 client delivery preview around the existing real pack; resolve buyer-fit limitations explicitly.
2. Build the £495 edition only after source comparability and content sufficiency pass. Use the separate implementation plan.
3. Apply the shared visual style to both files and local product/sample pages. Demonstrate actual downloads.
4. Align the homepage around the two one-off launch products, with the Brief remaining the lead. Give visitors a clear sample-first path. Keep the free directory useful and easy to find.

**Check:** all files agree with their sample and product page; no broken source/download links; documented prices and delivery periods remain consistent; final PDFs/workbooks pass content and layout checks. If a deliverable is not complete, the page says so.

### Wave 3: catalogue-wide presentation

Polish the Directory and existing pilot format. Standardise roadmap pages for Radar, Assignment, Membership, Feed and Enterprise. Remove fake data and promises, and explain their status clearly. Apply the shared design without implementing the gated platforms or adding payment paths.

**Check:** free paths and existing entitlements remain intact; roadmap CTAs cannot create an order or payment; each screen has honest loading, empty and failure states where relevant. No UI displays success without a successful underlying action.

### Wave 4: later capability work, only after admission

For each gated product, produce a separate evidence-backed scope and capacity estimate before feature work. Admit one bounded product at a time through the existing operating process. The broad polishing request is not authority to activate billing, publish, build Track B/spine infrastructure or start outreach.

## Engineering and design validation

Build inside the existing frontend rather than adding a second deployed app. Prefer scoped components and styles over global rewrites. Preserve unrelated worktree changes and historical compatibility logic. Candidate areas are `frontend/lib/caregist-config.ts`, `frontend/app/pricing/page.tsx`, existing product routes, and a proposed `frontend/components/product/` directory; inspect existing implementations and nested instructions before changes.

Responsive rules: bounded desktop content, readable report text, keyboard-accessible drawers, stacked mobile cards and labelled table scrolling. Keep zoom enabled and honour reduced motion. Test 390px, 768px and 1280px widths and zoom. Ensure visible focus, sensible headings, labelled inputs, adequate contrast and non-colour-only status meaning.

Meaningful tests: source identity and aggregates, event semantics, product/status CTA rules, no payment transition for roadmap products, exact file/version downloads, form success only on actual success, and preservation of existing permissions. Run the affected frontend tests/build and browser journeys. Avoid tests which only repeat the hard-coded copy.

Review the source data, final files and actual UI together. Freeze the evidence packet for the independent re-test and challenge in `.warroom/PIPELINE.md`. The producer does not approve its own release.

Later rollout requires exact authorization and passed commercial conditions. Keep rollback limited to changed product content/components, retain previous approved editions and preserve existing data/access. No live changes are included in this planning task.

## Price defence across the range

The free directory provides discovery. The £495 report adds checked comparisons and a prepared explanation. The £745 Brief adds selection against a buyer's agreed question. Future assignments, memberships, feeds and enterprise work need separately demonstrated value from their actual scope or integration. Higher prices do not justify stronger unsupported language. No current evidence establishes customer ROI or willingness to pay merely because a product is listed.

## Handoff

Files changed: this catalogue-wide plan only. The detailed £495 plan remains its implementation sub-plan.

9 September update: Wave 1 file list, Wave 1 state, and the exact next action were revised to reflect the built register. Registered conflicts and claims live in `artifacts/product-polish/claim-register.json`.

Checks performed: read current local catalogue/config and the 7 September founder decision; reconciled launch, in-flight pilot and roadmap states; retained existing manifest prices as unvalidated where appropriate; incorporated the previously inspected design and claim review. No product implementation or live-state validation is claimed.

Unresolved issues: buyer fit for the Brief, source/history sufficiency for the Report, confirmed VAT and commercial release conditions, and product-specific capability gates for recurring/enterprise products. These affect selling; they do not prevent local design/content preparation.

Exact next action (revised 9 September): the shared catalogue and claim register already exist at `artifacts/product-polish/`. Next is the £745 delivery preview, mapping each preview field to the verified Birmingham/Solihull pack and leaving proposed enrichment outside the offer, while the £495 comparable-source assessment continues. Only after those examples pass should the shared design be applied to the rest of the catalogue. Two items are prerequisites rather than polish: CONF-1 (live Stripe prices for products held closed) needs a founder decision, and the Source Serif 4 / Inter standard is a sitewide font swap away from the current DM Sans and Playfair Display, not a scoped component change. This sequence protects the first-sale focus while covering all products.

Sources:

- [Current local catalogue](/Users/user/CareGist/frontend/lib/caregist-config.ts)
- [Founder decision and pilot reconciliation](/Users/user/.hermes/profiles/ai-company-governed/company-os/chief-of-staff/decisions/2026-09-07-caregist-launch-one-off-products.md)
- [Preparation manifest](/Users/user/CareGist/deploy/stripe-price-manifest.json)
- [Detailed £495 implementation plan](/Users/user/CareGist/artifacts/sales/2026-09-08-market-movement-report-implementation-plan.md)
- [Fresh Brief evidence and price defence](/Users/user/CareGist/artifacts/sales/2026-09-08-fresh-brief-sales-handoff.md)
- [Design/content review](/Users/user/CareGist/artifacts/sales/2026-09-08-stitch-design-content-review.md)
- [User design reference](/Users/user/Downloads/DESIGN-caregist.md)
- [Operating pipeline](/Users/user/CareGist/.warroom/PIPELINE.md)

COMPLETE: no escalation needed. Applies to the expanded implementation plan, not product completion or release approval.
