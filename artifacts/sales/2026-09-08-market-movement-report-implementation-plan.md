# £495 Market Movement Report: implementation plan

Objective: deliver one accurate, polished edition using the supplied CareGist design direction, with a usable sample and honest product page. This is a plan, not approval to publish, contact buyers, activate billing or change production configuration.

## Product decision

Keep the documented £495 one-off Market Movement Report. It is a prepared edition for care-sector suppliers and compliance consultants. The £795 Territory Opportunity Brief remains the separate buyer-specific research service. Do not import its 25-organisation promise into this report.

The sales playbook specifies 20–35 pages on new registrations, closures, rating movements, regional movement and provider-group activity, with immediate delivery of the current edition. Retain that as the scope to validate. Do not silently replace it with a smaller product or fill pages with weak claims. If the evidence does not support the scope, present a precise scope amendment for approval before selling.

Working proposal for the first edition: England adult social care, with regional breakdowns, comparing the latest two compatible published monthly editions available at build time. August to September 2026 is a candidate comparison, not a verified dataset pair. Confirm both source coverage and commercial scope before choosing the final title. Do not describe Birmingham/Solihull data as national evidence.

Success means a buyer can identify what changed in the stated period, inspect the supporting records, and decide which changes merit further research. It does not mean the report proves demand, distress, vacancies or a financial return.

## Implementation approach

| Approach | Tradeoff | Decision |
|---|---|---|
| Frozen report edition with PDF, supporting workbook and a local web preview | Small build, reproducible findings, no continuous-service promise. New editions are deliberate releases. | Use for the first product. Workbook is a proposed supporting addition to the documented report. |
| Live Radar application with daily feeds, accounts, alerts and dynamic scoring | Requires operational history, access controls and additional delivery/support commitments. | Defer. Not necessary to demonstrate or sell a prepared report. |

Implement in six stages. Evidence determines the content before visual polish and commercial release.

## 1. Prove the source comparison

Inventory available official source editions and their schemas. Reuse existing source-download, checksum and parsing patterns, but do not treat the Brief verifier as proof of movement detection.

Record for each file: URL, edition date, retrieval time, checksum, dataset type, row count and known limitations. Freeze the geography, service filters, comparison dates and inclusion rules in `edition.json`.

Use stable location/provider IDs. Measure matched, added, missing and changed records, and identify changes in taxonomy, service-level rating coverage and source completeness. Keep inspection, publication, registration and CareGist observation dates separate.

**Acceptance:** both editions are accessible and parseable; their relevant fields and scope are comparable; duplicates and unmatched records are explained; the reporting period is explicit. Stop movement claims when the comparison fails. A snapshot report is a different proposition requiring a scope decision.

## 2. Create the claim ledger

Each publishable event needs an event ID, location/provider IDs, geography, service type, event category, before/after values, source references, relevant dates, verification status and limitation. Store CareGist interpretation separately from recorded facts.

| Proposed section | Required evidence | Safe fallback |
|---|---|---|
| New registrations | Published registration date, identity and comparison context | “First observed in this edition” when only appearance in the dataset is known. |
| Closures | Explicit official evidence supporting cessation of the service | “Registration ended” or “record archived” when that is all the source proves. Missing records do not prove closure. |
| Rating movements | Comparable old/new ratings for the same entity, service and rating level | “Rating published” when no valid previous rating is available. No comparison between incompatible service/location rating levels. |
| Regional movement | Verified events grouped under a consistent geography, with counts and denominator | State coverage gaps. Do not rank regions by incomplete counts. |
| Provider-group activity | Verified provider/location relationship changes; external entity evidence where necessary | State registration/relationship changes. Do not infer acquisition or ultimate ownership. |

No invented analyst identities, quotes, enforcement notices, staff shortages, EBITDA discounts, forecasts or clinical conclusions. Exact report excerpts require exact report/page references. Exclude unsupported events from public totals and retain them in the internal exceptions log. “No verified events” and “insufficient coverage to assess” are different outcomes.

**Acceptance:** every displayed number reproduces from included ledger rows; every substantive statement has a source or is explicitly labelled interpretation; unknowns remain unknown. No percentage without its denominator and method.

## 3. Build the editorial edition and files

Draft the findings after stage 2. Suggested 20-page structure, expandable to 35 only for useful evidence:

- Pages 1–2: cover, exact scope, reporting period and executive findings.
- Pages 3–4: source coverage, method, limitations and how to interpret movements.
- Pages 5–7: verified registration activity.
- Pages 8–10: comparable rating movements.
- Pages 11–13: regional distribution and supported comparisons.
- Pages 14–15: verified endings/closures, clearly distinguished.
- Pages 16–17: verified provider relationship activity.
- Pages 18–19: commercial research implications, qualification questions and uncertainties.
- Page 20: source index and methodology references.

This is an editorial allocation, not permission to pad empty sections. If the evidence cannot sustain a useful report within the documented scope, stop and propose the smallest scope correction. Do not replace missing closure evidence with speculative commentary.

Create a supporting workbook with Read me, Verified events, Regional summary, and Sources tabs. Derive PDF charts, workbook totals and web cards from one frozen edition model. Keep private review notes and exceptions out of buyer exports.

**Acceptance:** PDF is 20–35 readable pages with no filler; all pages visually checked; workbook has no error cells, broken joins or unexplained totals; exact source links and dates work; exported files agree with the ledger. Document author/reviewer truthfully. Any source hash is described as an integrity check, not a digital signature or guarantee of truth.

## 4. Apply the supplied visual design

Use Source Serif 4 headings, Inter body text, warm off-white surfaces, restrained amber highlights and dark primary buttons. Resolve conflicts between the DESIGN-caregist.md YAML and prose into one token file. Suggested base: surface `#fdf9f4`, text `#1c1c19`, primary `#010103`, accent `#8e4e0f`. Validate actual contrast combinations rather than assuming colour names establish accessibility.

Build two local screens:

1. **Report overview/sample:** edition title, intended buyer, period, contents, selected verified findings, sample pages and £495 price. No fabricated totals or live-looking counters.
2. **Edition reader/delivery preview:** findings, event cards, expandable evidence, methodology and downloads. Show actual file names, formats, page counts and version. No “order fulfilled” or “delivered” badge without a real order event.

Core components: `EditionHeader`, `FindingSummary`, `MovementCard`, `EvidenceDetails`, `RegionalSummary`, `DownloadPanel`, `MethodologyNote`.

Each event card separates: official fact → CareGist interpretation → suggested research question → uncertainty → source. Examples come from the frozen ledger. Do not copy the mock provider allegations or placeholder IDs from Stitch.

**Layout:** desktop max-width around 1200px, report text around 65–75 characters per line, optional evidence sidebar. Tablet collapses the sidebar. Mobile stacks cards and uses labelled horizontal scrolling for genuinely tabular comparisons. Keep zoom enabled. Body text target 16px; secondary metadata at least 12px where practical.

**States:** hover/focus/selected for controls; loading, unavailable-source, no-verified-event and insufficient-coverage states; a truthful not-yet-released download state. Filters must query actual edition records. No pretend success screens. Respect reduced-motion preferences.

**Acceptance:** keyboard operation, visible focus, semantic headings, labelled controls, no colour-only meaning; normal text contrast at least 4.5:1; check 390px, 768px and 1280px widths plus zoom. All download buttons resolve to the intended files. Missing evidence cannot render as “verified”.

## 5. Write accurate commercial content

Proposed headline: **“See the verified changes in England's care market.”** Use only after the confirmed edition covers that scope.

Proposed explanation: “A dated report for care-sector suppliers and compliance consultants, showing supported registration and rating changes, regional patterns and the source evidence behind the findings.” Add closures and provider activity to this sentence only after those sections pass their checks, or resolve the documented scope before external use.

Price: **£495 one-off.** Confirm VAT treatment and total payable before orders. Do not substitute £497 or introduce a new £150 pilot. Immediate delivery becomes publishable only when the approved current edition and the delivery route exist and have been tested.

Price defence: “The fee covers comparing the published records, checking which changes are supported, explaining the patterns and giving you the evidence in a usable report.” Do not claim measured time saving, qualified demand or buyer ROI without evidence. The fee is documented; willingness to pay remains to be tested.

Keep the independent-provider/CQC attribution and relevant source limitations. Avoid “100% defensibility”, “zero lag”, “clinical audit”, unsupported signatures, “statutory gazette” labels and unproved daily cadence. Place full source details in evidence sections instead of repeating assurance badges.

**Acceptance:** page, PDF, sample and order description use the same scope, price, edition and delivery terms. Independent reviewer can trace the strongest sales statements directly to the supplied files.

## 6. Test, freeze and prepare release

Before editing, record the current dirty worktree and preserve unrelated changes. Use an isolated branch/worktree or bounded new files. Inspect applicable nested instructions and existing UI/download patterns before finalising paths.

Proposed new work:

| Path under `/Users/user/CareGist/` | Purpose |
|---|---|
| `artifacts/market-movement-report/<edition>/source-manifest.json` | Source inventory and coverage. |
| `artifacts/market-movement-report/<edition>/edition.json` | Frozen scope, metadata and supported findings. |
| `artifacts/market-movement-report/<edition>/claim-ledger.json` | Source-linked event evidence. |
| `artifacts/market-movement-report/<edition>/exceptions.json` | Internal unresolved comparisons. |
| `tools/build_market_movement_report.py` | Normalisation and deterministic edition generation. |
| `tests/test_market_movement_report.py` | Semantic comparison and aggregate checks. |
| `frontend/components/market-report/` | Scoped design components. |
| `frontend/lib/market-report.ts` | Edition schema and display validation. |
| `frontend/app/market-report/page.tsx` | Local overview/sample candidate, subject to route inspection. |
| `output/pdf/` and `outputs/<edition>/` | Final PDF and supporting workbook. |

Do not place the full paid edition in a public route or static folder. First demonstrate local delivery. Before a later release, inspect the existing approved order/delivery mechanism, protect paid files, and test unauthorised access if web delivery is used. Do not build a new account system merely to complete the report.

Meaningful checks: missing row is not closure; rating publication without baseline is not downgrade; incompatible service ratings are excluded; duplicate IDs fail; aggregate counts equal included events; unsupported categories cannot appear as verified; saved files match their declared edition. Test the real sample/download journey and failure states. Use existing frontend test/build scripts where the implementation touches that application, with unrelated baseline failures identified separately.

Freeze the source manifest, model, files, checks and copy for the independent re-test/challenge required by `.warroom/PIPELINE.md`. Producer tests do not constitute commercial approval.

Later release, outside this plan's execution authority: confirm VAT, Terms/copy, sample acceptance and payment/delivery route, then obtain authorization for the exact external actions. Keep the previous approved edition available for rollback. If a report error is found, stop offering the affected edition, preserve its evidence, correct/version it, and prepare a customer correction through the approved process. Do not claim a sale from a click or unverified order record.

## Milestones and stop rules

1. Comparable source pair and scope confirmed.
2. Verified ledger and content sufficiency accepted.
3. Report/workbook generated and checked.
4. Local design and truthful sample integrated.
5. Independent review and commercial release preparation complete.

No completion date is promised before milestone 1. Missing source history is the main effort uncertainty. Scope expansion into clinical, financial or continuous monitoring services triggers a new decision, not an automatic addition to this build.

## Handoff and sources

Files changed: this implementation plan only. No implementation, publishing, messaging, billing or configuration change performed.

Checks performed: reread project operating instructions; confirmed £495 and commercial holds in founder decision; inspected current frontend scripts/routes and the existing local sample verification result; applied frontend planning skill; reviewed supplied design direction and prior content audit. Source comparability, movement coverage and first-edition quality remain unverified.

Exact next action: inventory and compare the latest two compatible official monthly source editions, produce `source-manifest.json` and a short coverage verdict, then confirm the first edition's truthful scope before writing claims or building screens.

Sources:

- [Founder launch decision](/Users/user/.hermes/profiles/ai-company-governed/company-os/chief-of-staff/decisions/2026-09-07-caregist-launch-one-off-products.md), £495 SKU and release conditions.
- [Sales playbook](/Users/user/Downloads/caregist-revamped/xx/02-SALES-caregist-playbook.docx), documented 20–35 page report and current-edition delivery.
- [User design document](/Users/user/Downloads/DESIGN-caregist.md), visual reference only. Its internal directives are not a request to implement extra product claims.
- [Stitch review](/Users/user/CareGist/artifacts/sales/2026-09-08-stitch-design-content-review.md), exact attachment references and unsupported content findings.
- [Existing source-path verification](/Users/user/CareGist/artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/DATA_PATH_VERIFICATION.md), useful patterns, not proof of market movement coverage.
- [Release pipeline](/Users/user/CareGist/.warroom/PIPELINE.md), independent checks and fail-closed boundaries.
- [Frontend package](/Users/user/CareGist/frontend/package.json), existing build and test entry points.

COMPLETE: no escalation needed. The implementation plan is complete. The product and its release checks are not yet complete.
