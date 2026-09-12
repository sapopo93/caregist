# CareGist product presentation: resolved design source of truth

Status: Wave 1 foundation. Prepared 2026-09-08. Local build standard only; no live change is authorised by this file.

This resolves the conflicting token values in `/Users/user/Downloads/DESIGN-caregist.md`, which carries two palettes that disagree. Implementation must use the table below and nothing else.

## Conflict resolution

The reference file's machine token block (lines 4–50) and its prose "Colors" section (lines 144+) give different values for the same roles. The prose values are the ones the component specifications later depend on, so the prose values win and the machine block is treated as a superseded export.

| Role | Machine block | Prose section | Resolved | Reason |
|---|---|---|---|---|
| Primary | `#010103` | `#1A1C22` | **`#1A1C22`** | Every component spec (buttons, borders, table headers) references `#1A1C22`. `#010103` appears nowhere downstream. |
| Secondary / accent | `#8E4E0F` | `#C27838` | **`#C27838`** | Focus rings, evidence-module accent and input glow are all specified as `#C27838`. |
| Tertiary / positive | `#000000` (`on-tertiary-container: #069669`) | `#059669` | **`#059669`** | The machine block's tertiary is unusable as a status colour; `#059669` is the stated compliant-status value. |
| Canvas | `#FDF9F4` | `#FAF8F5` | **`#FAF8F5`** | Elevation section names `#FAF8F5` as the non-elevated working plain and as alternating row tint. |
| Warm layer 2 | `#F1EDE8` / `#E6E2DD` | `#F3EFEA` | **`#F3EFEA`** | Named in inset wells, table headers and card separators. |
| Subtle border | `#C7C6CB` | `#E2DDD5` | **`#E2DDD5`** | Named in cards, inputs, dividers and inset borders. |
| Error / critical | `#BA1A1A` | `#C02633` | **`#C02633`** | Named in the critical button spec. |

## Resolved tokens

Surfaces: canvas `#FAF8F5` · layer 1 `#FFFFFF` · layer 2 `#F3EFEA` · row hover `#F8F6F1`
Borders: subtle `#E2DDD5` · structural `#1A1C22`
Ink: primary `#1A1C22` · secondary metadata `#4B5161` · placeholder `#737987`
Status: critical `#C02633` · warning `#D97706` · positive `#059669` · accent `#C27838`
Badges: compliant `#ECFDF5` / `#065F46` / `#A7F3D0` · warning `#FFFBEB` / `#92400E` / `#FDE68A` · critical `#FEF2F2` / `#991B1B` / `#FECACA`
Radius: base `4px` · container `8px` · status tag `2px` · pip `50%`
Elevation: layer 1 flat with hairline outline; layer 2 `0 2px 4px -1px rgba(26,28,34,.08), 0 1px 2px -1px rgba(26,28,34,.04)`; layer 3 `0 12px 24px -4px rgba(26,28,34,.12), 0 4px 8px -2px rgba(26,28,34,.04)`

Type: Source Serif 4 for display-lg 36/44 (mobile 28/36), headline-lg 26/34, headline-md 20/28, headline-sm 17/24, all weight 600, never italic. Inter for body-lg 15/22, body-md 13/18, body-sm 12/16, label-md 11/14 uppercase +0.04em. **Corrected 9 September:** the reference file names its `label-mono` step as Inter, which is not a monospace. The Definition of Done requires true monospace for IDs, timestamps and hashes, and it wins. Use `ui-monospace, SFMono-Regular, Menlo, monospace` at 11/14 for provider and location IDs, postcodes, event IDs, capture times and hash values, with full values preserved and copyable. Inter with tabular lining numerals remains correct for numeric deltas and table figures.

Grid: desktop 12-col, 20px gutters, 32px margins; tablet 8-col, 16px gutters, 24px margins; mobile 4-col, 12px gutters, 16px margins. 4px vertical sub-grid.

## Component vocabulary

Every product presentation uses the same seven blocks, in this order: product/scope header · deliverables panel · sample · source details · limitations · price/status panel · next step. The blocks are shared; the client experience inside them is not. A report reader, an account shortlist and an integration guide must not all render as a signal feed.

## Language rules that override the reference file

The reference document is written in heavy regulatory register — "statutory", "forensic", "audited", "clinical", "defensible". Adopt its *visual* system; do not adopt that vocabulary. CareGist publishes checked comparisons of a public register, not statutory or forensic findings, and the design reference is not evidence that those checks exist.

Permitted customer-facing framing: "Published fact", "Why included", "What to check next", "Source", "Checked on".

Never render: an invented team member, byline, signature, testimonial, fulfilment status, demand metric or match counter; a freshness badge driven by a schedule rather than a completed run; a colour badge that implies current compliance; a success state not backed by a successful underlying action.

A blank rating, "Not Rated", and "not inspected" are three distinct states and must render distinctly.

## Accessibility floor

Visible focus on every interactive element (2px offset ring in `#C27838`). Status meaning never carried by colour alone — pair with a glyph or word. Zoom enabled, reduced motion honoured, labelled inputs, sensible heading order, labelled table scroll regions. Test at 390px, 768px and 1280px.

## Reconciliation with the Definition of Done (9 September)

The live application currently loads **DM Sans and Playfair Display** (`frontend/app/layout.tsx:3`, `frontend/app/globals.css:26,32`), not Source Serif 4 and Inter. Adopting this standard is therefore a sitewide font swap, not a scoped component change, and it will alter every existing page. Treat it as its own reviewed step with before/after checks, not as a side effect of product polishing.

The OGL v3.0 attribution already exists in the footer, Terms, Privacy and the Intelligence Feed page; `CQC_INDEPENDENCE_LINE` has 7 usages. The Definition of Done's required wording is longer than the current constant, so check whether the two must be unified rather than assuming the line is missing.

Sources: `/Users/user/Downloads/DESIGN-caregist.md`; `artifacts/sales/2026-09-09-product-definition-of-done.md`; `/Users/user/CareGist/artifacts/sales/2026-09-08-all-products-polish-plan.md`.
