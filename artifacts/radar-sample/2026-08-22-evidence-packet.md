# CareGist Radar — Evidence Packet for Henry Approval Bundle (2026-08-22)

Prepared by: Hermes (`@caregist`) per @henry-proof's evidence-order direction (sample digest FIRST, then 5-row verification, then approval bundle).
Status: PRE-APPROVAL PREP — no contact, no price communication, no invoice. All artifacts internal.

---

## 1. Sample digest (D2(b) candidate — dated format sample)

- **Artifact:** `artifacts/radar-sample/2026-08-22-dated-sample-digest.md`
- **Format:** exact weekly-digest structure (territory, window, selection rule, new registrations, rating changes, provenance per event)
- **Territory:** Gloucestershire — deterministic selection (highest supported-event count in latest seven-day window; tie-break alphabetical)
- **Snapshot as of:** 20/02/2026 (source mirror retrieved 24/02/2026)
- **Window:** 14/02/2026 to 20/02/2026; 5 supported new registrations, 0 rating changes
- **Data source (inspectable):**
  - `_locations_detail.ndjson` — 118,634 rows, 769,877,406 bytes, modified 24/02/2026 07:59:55
  - `_providers_detail.ndjson` — 63,144 rows, 97,596,653 bytes, modified 24/02/2026 06:36:06
  - sha256: locations `162dac50a6e63aec14bf90187df6f7fbe7b7ddef702b4bb8b4ff4d58284f58b8`; providers `980f94e274e7cfa2682b769d5fbe8325d19a78f4e7e04c99db6d2cacec7133f0`
- **Generator:** `tools/generate_radar_territory_sample.py` (deterministic, `generated_at` anchored to snapshot date)
- **Regeneration proof:** re-run on 22/08/2026 produced byte-identical output — sha256 md `062c3b55ff815ac70cc81d06fc511669104629eb39afb4685a1eadeadc4f04ad`, json `b87e105c5fe29a129326e558d389f85acda81d7cc963ce55f713377200724cba` — unchanged before/after.
- **Truth boundary:** digest is explicitly a DATED format sample, not current data; candidate buyer wording included but marked PENDING HENRY APPROVAL (D2). No promise of fresh weekly data until the live CQC path is verified.

## 2. Fresh-data path status (2026-08-25 update — path now verified)

- 13/08/2026 documented run: mandated official CQC monthly CSV URLs returned HTTP 403 (evidence in `artifacts/radar-sample/2026-08-13-current-weekly-directory-delta-return.md`).
- 22/08/2026 direct checks: care-directory CSV URLs HTTP 404; public API HTTP 502.
- **25/08/2026 RESOLUTION:** the official "Using CQC data" page lists the current monthly register editions. Downloaded and verified (HTTP 200, SHA-256 recorded):
  - `artifacts/radar-live/2026-08-04_HSCA_Active_Locations.ods` — 04 Aug 2026 edition, 24.1MB (registration dates + ratings; the authoritative new-registration source)
  - `artifacts/radar-live/2026-08-04_Latest_ratings.ods` — 04 Aug 2026 edition, 26.9MB
  - `artifacts/radar-live/2026-08-19_CQC_directory.csv` — 19 Aug 2026 edition, 18.9MB (freshest plain directory; no registration dates)
- **A verified live CQC data path NOW EXISTS.** The 22/08 "no verified path" statement is retired. Evidence: `artifacts/radar-live/2026-08-25-ods-path-test-result.md`.
- **Fresh digest compiled:** `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.md` (+ `.json`) — 57,009 active locations, 684 Gloucestershire rows, window 29 Jul–04 Aug 2026: **0 new registrations, 1 rating publication** (Nuffield Health Cheltenham Hospital — Good, 29/07/2026). Key product-shape truth: a single-county weekly new-registration digest will often be zero; buyer wording must state updates truthfully or territory must widen. PENDING HENRY APPROVAL for any buyer-facing "current" claim.
- Delivery stop rule now re-anchored: a digest may be described as current only when its source edition is a verified CQC public file recorded in `artifacts/radar-live/`; otherwise it keeps the dated-sample label. If no verified edition exists at delivery, no digest is promised, no invoice issued — buyer is told before any money moves.

## 3. Recipient/channel verification — first 5 FIT rows (lawful-contact gate)

- **Artifact:** `artifacts/radar-verification/2026-08-22-fit-rows-1-5-verification.md`
- **Method:** direct GET of each org's own public website (browser UA); org-level published routes only; no named-individual harvesting; no enrichment; no contact made; £0 spend.
- **Result:**
  1. CQC Consultants — email dan@cqc-consultants.com (published mailto) + phone 01843 278765 (tel: link + text) — VERIFIED by henry-proof spot-check 25/08 (Companies House 09888898; dan@ is organisation mailbox) ✅
  2. Fulcrum Care Consulting — phone 020 3411 4014 (published CTAs) + email info@fulcrum.care — VERIFIED by henry-proof spot-check 25/08 (matches published site) ✅
  3. The UK Care Consultants — phone 0203 475 4334 (contact page visible text; tel: link masked) — PHONE ONLY, no published email — PROVISIONAL (pending independent site confirmation) ⚠️
  4. Cura Compliance UK — phone 07470 390526 (JSON-LD schema) + email info@curacompliance.co.uk — PROVISIONAL (pending independent site confirmation) ⚠️
  5. Team Care Compliance — phone 07155 410220 (JSON-LD ContactPoint) + alt 0115 845 0220 (tel: link; primary to confirm) + email help@teamcarecompliance.org.uk — PROVISIONAL (pending independent site confirmation; primary phone unresolved) ⚠️
- **Compliance:** PECR org-level basis; CTPS/TPS screening NOT yet run — pending Henry's outreach-scope approval (recorded in evidence file); no-name opener variant needed for phone-only routes (pack's "Hi [first name]" not usable) — PENDING Henry approval.
- Raw HTML snapshots: `artifacts/radar-verification/*.html`.

## 4. What remains gated (Henry's non-delegable approvals — not recorded by anyone else)

Per @henry-proof: price and invoice approvals are Henry's alone. PENDING HENRY APPROVAL:
- **D1** pilot region (buyer-selected at discovery, or name one — Gloucestershire recommended)
- **D2** sample promise: (b) dated format sample [built above], or (c) hold sample promise, sell on format + references
- **D3** £150 price; invoice/bank-transfer layout + ask-to-pay wording (henry-proof to inspect fresh-context); outreach script incl. no-name opener variant; CTPS/TPS + personal-data purpose
- **Settlement account blocker (finance):** no UK settlement account on record for H-Kay Limited — manual bank-transfer route needs a named UK bank account, or Henry's founder-only call to activate Stripe live. Invoice layout cannot be final without it.

## 5. Audit state

- Journey state: **AMBER** — pre-approval prep complete for sample + first-5 verification; contact/payment remain RED-gated on Henry's recorded approvals and the verified CQC data path.
- This packet is producer-prepared; fresh-context independent review by @henry-proof required before the approval bundle reaches Henry (producer never approves its own work).
