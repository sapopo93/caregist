# Claim–Evidence Check — CareGist Radar £150 Pilot (buyer-facing)

**Prepared by:** @marketing-cmo (Marketing CMO)
**Date:** 2026-08-23 (BST)
**Scope:** Buyer-facing claims in `~/CareGist/VA_MONDAY_REVENUE_PACK.md` (v. VA-READY SELLING AND MANUAL-FULFILMENT PACK) plus supporting artifacts.
**Purpose:** Input to @henry-proof's £150 price approval, which is contingent on this check landing first.
**Labels:** `verified` (primary evidence on disk) · `user-provided` (Henry/Hazel-approved scope) · `hypothesis` (plausible, unproven) · `unknown` (no evidence). Only `verified` and explicitly approved `user-provided` claims may be spoken or written.

---

## 1. Claim register (what the VA may say)

| # | Buyer-facing claim | Label | Evidence | Verdict |
|---|---|---|---|---|
| C1 | "We aggregate public CQC register information for one region and deliver a weekly summary." | `verified` (capability) | 115 MB provider cache `~/CareGist/_provider_cache.sqlite`; `_providers_list.ndjson` (4.7 MB); mirror + delta tooling `~/CareGist-commercial-fail-closed/tools/` (`run_new_registration_feed_cycle.py`, `send_weekly_movers.py`) | PASS — capability real |
| C2 | "The digest uses only publicly available CQC data; every item links to the public source." | `verified` (for sample items) | `weekly-territory-sample.md` (02 Feb 2026, Gloucestershire) — every item carries provenance URL `https://api.service.cqc.org.uk/public/v1/locations/...` | PASS for sample items; **verify URLs still resolve before buyer sees them** |
| C3 | "We will show you a sample before you commit." | **BLOCKED** | Only sample on disk is 2026-02-20 snapshot, explicitly marked `# DRAFT — not approved` / `# INTERNAL SAMPLE — not for sending or publication` | **FAIL — cannot truthfully promise a current sample today** |
| C4 | "This is a pilot: 4 weeks, one region, weekly email with a PDF digest." | `user-provided` | Pack §1; tracker `VA_REVENUE_TRACKER.csv` (20 orgs) | PASS |
| C5 | "Price is £150 for the 4-week pilot." | `user-provided` (pending approval) | Pack §4; @finance confirms £150 inside governed corridor (£131.25 floor / £250 ceiling) | PASS **only after** Henry's recorded price approval |
| C6 | "No software, nothing to install." | `verified` | Pack §1 — manual fulfilment only; no login/dashboard/API sold | PASS |
| C7 | "Every item links to the public register page, and the digest states the register snapshot date." (objection line) | `verified` for design; **freshness unknown** | Sample states snapshot date; **latest fresh run (13 Aug 2026) BLOCKED — official CQC CSV URLs returned HTTP 403** (`2026-08-13-current-weekly-directory-delta-return.md`, status BLOCKED) | PASS as design; **cannot guarantee a current digest can be compiled this week** |

## 2. Hard finding — freshness gate

- The most recent fresh-data run, **2026-08-13**, returned **BLOCKED**: `https://www.cqc.org.uk/system/files/2026-08/05_August_2026_CQC_directory.csv` (and the 12 Aug URL) returned **HTTP 403** to unauthenticated GET (both `requests` and `curl`). The run stopped under its own stop rule and did **not** fabricate a substitute — correct behaviour.
- Consequence: **no current-region sample exists** for the 24–31 Aug selling window. The only sample is stale (Feb 2026) and unapproved for sending.
- Week-1 delivery (default w/c 1 Sept) depends on the same pipeline. If the 403 persists, the first digest cannot be truthfully compiled.

## 3. What this means for the ask

1. The **£150 price and offer language are defensible** — the pack's exclusions, limitations and prohibited claims are correct and there is no fabricated proof in the buyer-facing copy.
2. The **"sample before you commit" promise is currently unfulfillable** — either (a) unblock the fresh-data pipeline and produce + approve a current sample before Monday, or (b) change the scripted promise to "we'll send you a sample of the format" with the stale sample clearly dated, or (c) hold the sample promise and sell on format + references.
3. **No price, invoice or ask-to-pay goes live** until Henry's two approvals are recorded — unchanged.
4. The VA's call opener itself (C1–C4, C6) is **safe to use** on Monday subject to approvals and @operations' preflight.

## 4. Escalation

- **@operations:** confirm whether the CQC CSV 403 can be resolved (alternate official source, caching, or a mirror refresh) before Monday; if not, week-1 fulfilment is at risk and the sample promise must be amended.
- **@henry-proof:** the £150 gate can land on offer language; the sample-promise clause needs Henry's call on (b) vs (c) if the pipeline stays blocked.

---

*Governance: internal working artifact. Does not authorise publishing, contact, price communication, invoicing, or payment. All external actions remain behind the named approvals and @operations' preflight.*
