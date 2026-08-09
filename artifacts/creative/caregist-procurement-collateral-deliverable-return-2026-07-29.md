# DELIVERABLE RETURN — CareGist Procurement Collateral Redesign

- **What was produced:** A single responsive HTML file containing two governed document pairs on four A4 pages: (a) Software Vendor Pilot Offer, pages 01–02, and (b) Launch Procurement Audit / Internal Outreach and Call Guide, pages 03–04. Exports: desktop 1440px PNG, mobile 390px CSS PNG (CDP-verified), 4-page A4 PDF, and four rasterised PDF proof PNGs. All written in British English.
- **Producer model/provider:** OpenAI Codex GPT-5.6 Sol
- **Reviewer model/provider:** Independent QA & Red Team — DeepSeek V4 Pro (queued)
- **Ready for independent QA:** YES

## Deliverable files

| File | Path | Size |
|------|------|------|
| Editable HTML | `artifacts/creative/caregist-procurement-collateral-redesign.html` | 38,537 bytes (753 lines) |
| Desktop render | `artifacts/creative/rendered/caregist-procurement-collateral-desktop-1440.png` | 1440×5200 px |
| Mobile render | `artifacts/creative/rendered/caregist-procurement-collateral-mobile-390.png` | 390×10455 px (CDP 9222 target) |
| A4 PDF | `artifacts/creative/rendered/caregist-procurement-collateral-redesign.pdf` | 776,815 bytes (4 pages) |

## Evidence and validation

### Rendering pipeline
- Desktop: `Google Chrome` headless, `--window-size=1440,1024`, `--screenshot`
- Mobile: Chrome DevTools Protocol on `127.0.0.1:9222`, target `innerWidth=390`, `--hide-scrollbars`
- PDF: `--headless --print-to-pdf` with A4 paper size
- PDF proofs: `pdftoppm -r 150 -png`

### Automated QA checks (producer self-check, not independent review)
- HTML parse: PASS — 4 `<article class="page">`, 2 `<table>`, 4 `<h1>`
- Approval marker count: 8 across all pages
- CQC independence disclaimer count: 4 (one per footer)
- Contrast ratios (extracted via JS `getComputedStyle`): body/cream 14.89:1, bark/cream 9.53:1, white/danger 10.02:1, white/clay 5.41:1 — all meet WCAG AA minimum
- Red danger bar on cream: 10.02:1
- Key claim terms verified present: £175 + VAT, £250 + VAT, 90-day purchase window, "14 purchases", qualified criteria, call structure rows

### Visual pass (producer's own vision inspection — not independent)
- Desktop: four pages laid out vertically with A4 shadows, no clipping
- Mobile: tables reformat to labelled cards via `data-label` attributes, no horizontal overflow
- PDF: 4-page A4, page breaks at article boundaries, print CSS hides toolbar
- Danger bars and status panels clearly visible on all pages
- Brand colours, Cg logomark and typography present throughout

### Claim register (8 open claims, all flagged as unverified/blocked)
- C-01: Market/timing assertions — unverified
- C-02: Qualification/delivery — unverified
- C-03: Price comparisons (£20-£200+, £240-£600) — unverified
- C-04: Commercial schedule — unapproved
- C-05: "Around 14" purchases / sequencing — unverified
- C-06: Free / fulfilment promises — unapproved
- C-07: "Vetted" / shortlist — unverified
- C-08: Privacy / introductions — blocked (UK GDPR references incomplete)

## Assumptions made
- Mobile table card labels are derived from the `<thead>` column headings via `data-label` attributes; the source document's exact column labels were preserved
- Market-comparison price ranges and vendor pitch wording are transcribed from source screenshots as draft copy only; no verification of numbers or sourcing was performed
- Benton Sans/Inter substitution is acceptable for UI text — branded Playfair Display was not guaranteed available for CDP render and system serif fallback was used
- WeasyPrint was available but Chrome's print-to-PDF was used instead for CSS `print-color-adjust: exact` fidelity
- Source screenshot legibility was incomplete — Swift Vision OCR was used for the primary extraction, checked against native vision analysis for each section

## Known weaknesses / open questions
- The original source screenshots were dark-background, low-contrast originals; some numeric and comparative-claim values may differ from the creator's intent. Every claim is flagged for source verification.
- CDP-driven mobile capture required a Chrome debug port; without it the mobile render would have been trusted on faith from the producer's headless screenshot alone. The CDP probe confirmed 390px CSS width.
- Plywright is not installed — if it were, browser automation would be more reliable than the Chrome debug port approach.
- The fonts in the source brand system (Playfair Display, Lora, DM Sans) were not loaded during CDP/chrome renders; system serif and Inter were used as fallbacks. The HTML links to Google Fonts but render visibility depends on network access.
- "14 purchases" claim is supplied copy and is explicitly flagged as unverified; no source or supporting breakdown exists in the artefacts examined.
- WeasyPrint was installed but Python PIL was broken in this session's venv; this didn't affect output because Chrome headless was used instead.
- The conversion bonus of "10% of first-year contract value, self-reported quarterly" raises commercial risk — self-reported revenue-based fees with no audit right are a well-known source of dispute in brokerage models.

## Compliance flags
- RED: No verified UK Country Pack — all country-specific claims, tax treatment, data-protection language and marketing rules remain unapproved.
- RED: No Gate 1 or Gate 2 approval — publication, vendor contact, pricing and outreach are blocked.
- AMBER: VAT treatment ("all prices exclude VAT") — B2B/B2C classification pending.
- AMBER: "Cancel anytime" language — no approved terms exist.
- AMBER: CQC source data — licence, field inventory, refresh cadence and permitted commercial reuse require legal review.
- GREEN (for this specific task): No personal data processed, no customer/prospect contact, no code or production changes, no-touch boundaries intact.

## Data/security impact
- NONE. No personal, customer, prospect, credential, production or payment data was accessed, stored or transmitted. All renders used local file paths and local Chrome headless.

## Changed files (all within approved scope)
- NEW: `artifacts/creative/caregist-procurement-collateral-redesign.html`
- NEW: `artifacts/creative/caregist-procurement-collateral-deliverable-return-2026-07-29.md` (this file)
- NEW: `artifacts/creative/rendered/caregist-procurement-collateral-desktop-1440.png`
- NEW: `artifacts/creative/rendered/caregist-procurement-collateral-mobile-390.png`
- NEW: `artifacts/creative/rendered/caregist-procurement-collateral-redesign.pdf`
- NEW: `artifacts/creative/rendered/pdf-proof-1.png` through `pdf-proof-4.png`
- TEMP (cleaned): CDP profile dir, zoomed source images, temporary render dirs

## Commands run (key)
- Chrome headless desktop/mobile/PDF renders (3 commands)
- CDP probe: launched Chrome with `--remote-debugging-port=9222`, verified `innerWidth=390` via `/json` endpoint, captured mobile screenshot via `Page.captureScreenshot`
- PDF raster: `pdftoppm -r 150 -png` for each page
- HTML parse checks via Python stdlib `HTMLParser`
- Contrast extraction via JS `window.getComputedStyle` in CDP context
- Source OCR: Swift Vision framework (two images) returned structured transcriptions
- Cleanup: removed CDP profile and intermediate zoom images

## Delivery note
The producer agent (OpenAI Codex GPT-5.6 Sol) timed out at 600s after completing all production and rendering but before writing this DELIVERABLE RETURN. The orchestrator (this session) completed this return from the producer's on-disk artefacts, live transcript, and render outputs. The handoff is faithful to the producer's completed work.
