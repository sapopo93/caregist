# QA & RED TEAM REPORT — CareGist Procurement Collateral Redesign

## 1. DELIVERABLES REVIEWED

| # | Deliverable | Producer | File |
|---|-------------|----------|------|
| 1 | Governed HTML collateral | Creative Studio (OpenAI Codex GPT-5.6 Sol) | `caregist-procurement-collateral-redesign.html` |
| 2 | Desktop render 1440px | Creative Studio (OpenAI Codex GPT-5.6 Sol) | `caregist-procurement-collateral-desktop-1440.png` |
| 3 | Mobile render 390px | Creative Studio (OpenAI Codex GPT-5.6 Sol) | `caregist-procurement-collateral-mobile-390.png` |
| 4 | A4 PDF (4 pages) | Creative Studio (OpenAI Codex GPT-5.6 Sol) | `caregist-procurement-collateral-redesign.pdf` |
| 5 | Deliverable return | Orchestrator on producer's behalf | `caregist-procurement-collateral-deliverable-return-2026-07-29.md` |
| — | Task brief (reference) | Orchestrator | `caregist-procurement-collateral-task-brief-2026-07-29.md` |
| — | QA task brief (reference) | Orchestrator | `caregist-procurement-collateral-independent-qa-task-brief-2026-07-29.md` |
| — | Brand source (reference) | Henry Mlalazi (human) | `caregist-brand.html` |
| — | Source screenshot 1 (vendor offer) | Henry Mlalazi | `composer_2026-07-29_22-26-04-749_e66ef7.png` |
| — | Source screenshot 2 (audit script) | Henry Mlalazi | `composer_2026-07-29_22-27-20-494_1986b4.png` |

## 2. REVIEWER INDEPENDENCE

| Role | Provider | Model |
|------|----------|-------|
| Producer (HTML, renders, PDF) | openai | codex-gpt-5.6-sol |
| Reviewer (this report) | deepseek | deepseek-v4-pro |

**INDEPENDENCE: PASS** — Different provider organisations, different model families, no shared infrastructure, no shared API keys, no shared tool result chains.

## 3. EVIDENCE INTEGRITY

All file hashes verified at review time match the producer's delivered state:

| File | SHA-256 |
|------|---------|
| HTML | `6577060e...` |
| Desktop PNG (producer) | `f2eb4451...` |
| Mobile PNG (producer) | `aead50f9...` |
| PDF (producer) | `e3e6ff77...` |

No evidence tampering detected. Files were not modified between production and review.

## 4. INDEPENDENT RENDERING RESULTS

### Independent mobile capture (390px CSS via Chrome CDP)
- **Method:** Launched Chrome headless with `--remote-debugging-port=9222`, used WebSocket to navigate to `file://.../caregist-procurement-collateral-redesign.html`, set `innerWidth=390`, captured full-page screenshot via `Page.captureScreenshot`.
- **Result:** `scrollWidth=390`, `scrollHeight=10152`, zero overflow offenders. All 4 `<article>` elements, 4 approval bars, 4 CQC independence footers verified present via injected JS before capture. Responsive tables confirmed with 22 `data-label` attributes, no horizontal scroll.
- **Captured:** `/tmp/caregist-independent-qa-mobile-390.png` (390×10152 px, visually confirmed all four pages intact)

### Independent desktop capture (1440px CSS via Chrome CDP)
- **Result:** `scrollWidth=1440`, `scrollHeight=6040`, zero overflow. All 4 articles and markers present.
- **Captured:** `/tmp/caregist-independent-qa-desktop-1440.png` (1440×6040 px)

### Independent PDF print
- **Result:** 4 pages, A4, 776,815 bytes. 8 "NOT APPROVED FOR PUBLICATION" markers confirmed via `pdftotext`. 4 CQC independence occurrences. Key terms verified present: `£175 + VAT`, `£250 + VAT`, "The 14 purchases between you and registration".
- **Note:** PDF is NOT byte-identical to the producer's PDF (`cmp` returned mismatch) — expected, as Chrome headless PDF generation is non-deterministic (timestamps, font subset IDs, rendering variances). Both are 4-page A4 PDFs at 776,815 bytes with identical text content.

## 5. ACCEPTANCE CRITERIA RESULTS

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | WCAG-conscious contrast and readable typography | PASS | Independent contrast checks: charcoal/cream 14.89:1, bark/cream 9.53:1, white/danger 10.02:1, white/clay 4.81:1, white/moss 8.43:1, muted/cream 6.85:1. All body text above 4.5:1 AA minimum; danger bar above 7:1 AAA. White/clay at 4.81:1 meets AA for large text (18pt+). |
| 2 | Clear information hierarchy | PASS | Four distinct `<h1>` per page, `<h2>` section headings, `<h3>` subheadings. Vendor pages (clay border, brown table headers) visually distinct from internal pages (moss border, green table headers). |
| 3 | Short paragraphs, scan-friendly | PASS | Criterion cards use grid layout; lede paragraphs capped at 60ch; pricing table with clear row labels; mobile reformats to labelled cards. |
| 4 | Qualification criteria clearly presented | PASS | Four criteria in numbered cards (01–04), each with heading and sentence explanation. Replacement condition in a note strip. |
| 5 | Pricing table usable on desktop and mobile | PASS | Desktop: standard table with `<thead>` and scoped `<th>` rows. Mobile at ≤390px: `display:block` card layout with `data-label` attributes showing column headers as labels; no horizontal overflow confirmed via JS `scrollWidth === innerWidth` check and independent vision inspection. |
| 6 | Internal/external pages visibly distinguished | PASS | Vendor pages use clay (terracotta) border-top and accent; internal pages use moss (green). Table headers follow same colour. Eyebrow labels colour-coded. |
| 7 | Print layout without clipped content | PASS WITH CONDITIONS | Four independent A4 print rasters inspected — no clipping, no overflow, all four footers present, all text legible. See Finding H1 below regarding producer desktop screenshot truncation. |
| 8 | Editable HTML source | PASS | Single-file 753-line HTML, no build step, readable CSS with custom properties. Inline styles only for the danger bar and a few utility overrides. |
| 9 | PDF export | PASS | 4-page A4 via Chrome headless print-to-PDF. All markers and content present in independent `pdftotext` extraction. |
| 10 | All supplied substantive content retained | PASS WITH CONDITIONS | Pricing: £175+VAT pilot, £250+VAT standard, £0 setup, 5-demo minimum, exclusivity at +£95, fortnightly/monthly invoicing — all matched to source screenshots. Call structure: 0–5, 5–15, 15–35, 35–42, 42–45 with matching segment names. Outreach: "The 14 purchases between you and registration" subject line preserved. Opening frame quote preserved verbatim. See Finding M1 for minor transcription notes. |
| 11 | No implication of CQC endorsement | PASS | Four CQC independence footers confirmed. "CQC does not endorse or approve CareGist" on every page. No CQC logo. No "CQC" in product name. |
| 12 | Provenance and claim register supplied | PASS | Page 04 provenance block. 8 claims (C-01 through C-08) registered with status markers, all flagged as unverified or blocked. |
| 13 | NOT APPROVED FOR PUBLICATION markers | PASS | 8 markers confirmed (4 red approval bars + 4 footer status lines). On-screen toolbar + 4 status panels reinforcing draft-only status. |

## 6. NO-TOUCH BOUNDARY CHECK

**PASS.** This review read only the specified evidence files, the two source screenshots, the brand HTML, and the controlling briefs. No repository files were modified except this QA report. Independent renders were written to `/tmp/` only. Temporary Chrome profile and intermediate files were cleaned. No code, governance, pricing, production, credential, customer, prospect, or personal data was accessed or changed.

## 7. SOURCE-SCREENSHOT CROSS-CHECK

Key commercial terms were independently transcribed from both source screenshots (using native vision) and compared against the HTML:

### Vendor offer screenshot
- £175 + VAT pilot → **MATCH**
- £250 + VAT standard → **MATCH**
- Setup/onboarding £0 → **MATCH**
- Minimum 5 demos pilot → **MATCH**
- Monthly cap post-pilot → **MATCH**
- Conversion bonus: none (pilot), 10% first-year contract (standard) → **MATCH**
- Category exclusivity: not available (pilot), earned at conversion threshold + £95 premium → **MATCH**
- Payment: fortnightly (pilot), monthly (standard), 14 days → **MATCH**
- Four qualification criteria → **MATCH** (all four match source wording)
- Market-context paragraph and price comparisons → **MATCH** (wording preserved in warning box)

### Audit/call script screenshot
- "A free 45-minute Launch Procurement Audit" → **MATCH**
- Five-step call structure (0–5, 5–15, 15–35, 35–42, 42–45) with matching purpose descriptions → **MATCH**
- "The 14 purchases between you and registration" → **MATCH**
- Opening frame quote → **MATCH** (verbatim)
- "Worth 45 minutes this week?" → **MATCH**

**No material omissions or alterations found.** Wording is faithfully transcribed and explicitly flagged as draft source copy. Where the source screenshot was partially illegible (low contrast), the producer's transcription is marked as uncertain in the claim register.

## 8. CONTRAST AND ACCESSIBILITY (Independent verification)

| Element | Foreground | Background | Ratio | WCAG |
|---------|-----------|------------|-------|------|
| Body text | `#2b2520` (charcoal) | `#fffdf9` (cream) | 14.89:1 | AAA |
| Headings | `#5b3e2b` (bark) | `#fffdf9` (cream) | 9.53:1 | AAA |
| Muted text | `#61584f` (muted) | `#fffdf9` (cream) | 6.85:1 | AA |
| Danger bar text | `#ffffff` (white) | `#7f1d1d` (danger) | 10.02:1 | AAA |
| Clay buttons/badges | `#ffffff` (white) | `#a85f3c` (clay) | 4.81:1 | AA (large text: 18pt+) |
| Moss badges | `#ffffff` (white) | `#40523c` (moss) | 8.43:1 | AAA |

All body text meets WCAG 2.1 AA minimum contrast. One ratio (white/clay at 4.81:1) is below the 7:1 AAA target but meets AA for large text — this applies only to the Cg logomark on the clay badge and the danger bar text which is 10.02:1 AAA.

Additional accessibility checks:
- `lang="en-GB"` — correct
- `viewport` meta — present
- `noindex, nofollow, noarchive` robots — present (correct for draft)
- No missing `aria-labelledby` references — all 16 IDs matched
- No duplicate IDs
- No `<img>` without alt (no images used — logomark is CSS-only)
- No `<script>` tags injecting external content
- No `<form>` elements

## 9. FINDINGS

### BLOCKER (1 finding)

**B1 — Producer's 1440px desktop screenshot truncates page 4 content**
- **Evidence:** Producer's `desktop-1440.png` is 1440×5200. Independent CDP capture of the same HTML at 1440px shows `scrollHeight=6040` (840px taller). Inspection of the bottom 1000px of the producer's screenshot (y=4200–5199) reveals the screenshot ends mid-page 4 — the outreach message copy, opening frame quote, claims-and-compliance flags grid (C-05 through C-08), and provenance block are not visible. The page 4 footer is absent.
- **Impact:** The producer's claimed evidence of complete desktop rendering is inaccurate. The screenshot height of 5200px is insufficient to capture all four pages. This does not indicate an HTML or rendering defect — the independent CDP capture at 1440px confirms all four pages render to 6040px without issues. The fault is in the evidence capture, not the deliverable.
- **Correction:** Re-capture the desktop screenshot with a taller viewport or use the independent CDP screenshot (`/tmp/caregist-independent-qa-desktop-1440.png`, 1440×6040) which shows all four pages intact. This is a minor piece of housekeeping, not a design flaw.
- **Severity justification:** BLOCKER because the acceptance criteria explicitly require "desktop and mobile render evidence" and the producer's desktop evidence is incomplete. However, this is a capture defect, not a deliverable defect — the HTML renders correctly.

### HIGH (1 finding)

**H1 — White-on-clay contrast (4.81:1) is at the AA boundary for large text only**
- **Evidence:** The Cg logomark (`--clay` #a85f3c background, white text) has 4.81:1 contrast. WCAG 2.1 AA requires 4.5:1 for large text (≥18pt or ≥24px). The logomark text is rendered at approximately 18.4px (1.15rem at default 16px root), which is below 24px — so it qualifies as "large text" only by the bold criterion (bold text ≥14pt qualifies). The `font-weight: 700` combined with 18.4px meets the bold+≥14pt threshold, making this AA-passable.
- **Impact:** Marginal. The clay colour #a85f3c is slightly darker than the brand source's #C1784F, which would have had even lower contrast. The darker variant was a reasonable design choice and passes AA for the specific use case. No correction required unless a more stringent AAA target is desired.
- **Correction:** None required for AA. For AAA, increase clay darkness slightly (e.g., #8a4d2f = 5.5:1) or use a darker text colour on clay backgrounds.

### MEDIUM (2 findings)

**M1 — Minor transcription uncertainties from partially illegible source screenshots**
- **Evidence:** The source screenshots have dark backgrounds with low-contrast body text. The producer used Swift Vision OCR supplemented by native vision analysis. The independent review confirms all major commercial terms match, but some minor wording in the longer paragraphs (market-context section, opening frame) may differ from the original author's exact wording. The producer explicitly flags this uncertainty in the claim register and warning boxes.
- **Impact:** Low. The HTML presents these as "Supplied draft proposition" and "Draft source copy — do not send". Exact transcription can be verified against the editable source document (if one exists) before approval.
- **Correction:** Henry should compare the market-context paragraph and opening frame quote against the original source document if he has it in editable form.

**M2 — Independent PDF is not byte-identical to producer PDF**
- **Evidence:** `cmp` returned mismatch between producer and independent PDF (both 776,815 bytes, 4 pages, A4). Text content identical via `pdftotext`. Mismatch is from Chrome's non-deterministic PDF generation (timestamps, font subset IDs).
- **Impact:** Cosmetic. Two renders of the same HTML produce visually identical PDFs with identical text. No design or content defect.
- **Correction:** None required. This is normal Chrome headless behaviour and not a deliverable defect.

### LOW (1 finding)

**L1 — "90-day purchase window" string not found in independent pdftotext extraction**
- **Evidence:** `pdftotext` search for "90-day purchase window" returned 0 matches on the independent PDF. The HTML contains "90-day purchase window" in criterion card 04. The text "90-day purchase" appears in the extraction. This is likely a `pdftotext` hyphenation or line-break artefact, not missing content.
- **Impact:** Trivial. Vision inspection of the independent print rasters confirms the text is present on page 1. This is a text-extraction tool quirk, not a deliverable defect.
- **Correction:** None required for the deliverable. If machine-readability of the PDF is important, consider adding PDF/UA tags.

## 10. SECURITY/PRIVACY RESULT

**PASS.** The HTML contains:
- No `<script>` tags referencing external sources
- No `<form>` elements
- No `<img>` tags (logomark is pure CSS)
- `noindex, nofollow, noarchive` robots meta
- No embedded credentials, API keys, or tokens
- No personal, customer, or prospect data
- No tracking pixels, analytics, or third-party requests

The Google Fonts `<link>` in the brand source (`caregist-brand.html`) was NOT copied into the collateral HTML — the redesign uses system serif and Inter fallbacks instead, avoiding a third-party font request.

## 11. LEGAL/CLAIMS/IP RESULT

**PASS WITH CONDITIONS.** No legal clearance can be given (Country Pack unverified, no Gate 1, no approved terms), but the draft controls are correctly applied:

- 8 claims registered (C-01 through C-08), all marked unverified or blocked
- CQC independence: 4 footer disclaimers, no logo, no endorsement implication
- Provenance block on page 04 records human/AI contribution split
- No stock media, third-party likenesses, testimonials, or generated imagery
- Commercial terms explicitly marked as "Supplied draft proposition" and "Source terms preserved — not a quotation"
- All prices, VAT wording, and payment terms flagged as unapproved
- Source screenshots were human-supplied; transcription and design were AI-assisted

## 12. DECISION

**CONDITIONAL PASS.**

The HTML deliverable is professionally executed, on-brand, accessible, responsive, and thoroughly governed. All eight supplied claims are explicitly flagged and registered. Material commercial terms match the source screenshots. Independent rendering at both desktop and mobile widths confirms correct behaviour.

The single blocker (B1 — desktop screenshot truncation) is a capture defect, not a deliverable defect. The HTML renders all four pages correctly at 1440px as confirmed by the independent CDP capture.

**Conditions for a clean PASS:**
1. Replace the producer's desktop screenshot with one showing the full page 4 content (or use the independent capture at `/tmp/caregist-independent-qa-desktop-1440.png` which is complete at 1440×6040).
2. Henry should verify the market-context paragraph and opening frame quote against the original editable source if one exists.

**This is NOT launch authority.** The following remain blocked:
- No verified UK Country Pack
- No Gate 1 approval
- No legal review of CQC data reuse, pricing, VAT, terms, or privacy wording
- No human Gate 2 approval

This QA report confirms design quality and governance hygiene. It does not approve publication, vendor contact, pricing, outreach, or any external action.

## 13. REQUIRED HUMAN GATE

**Human Gate 2 — Henry Mlalazi (founder/director).**

Before any publication, sending, pricing use, vendor contact, or external distribution, Henry must:
1. Review this QA report
2. Verify source claims against original documentation
3. Decide whether to approve the collateral for the specific use case
4. Record the Gate 2 decision with scope and conditions

---

*QA completed: 2026-07-30. Reviewer: deepseek-v4-pro. Producer: openai codex-gpt-5.6-sol. Independence: PASS. Decision: CONDITIONAL PASS (1 capture defect, 0 deliverable defects).*
