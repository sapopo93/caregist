# Screened-49 Contact Bundle — BLOCKED (canonical 49-record list not locatable)

**Status:** `BLOCKED — NOT CONTACT-READY`. The exact 49-record file cannot be found in any local location searched. Per the standing hard rule, recipients are NOT invented: this bundle therefore contains **zero populated recipient rows**. Do not contact anyone from this artifact.

Created: 2026-09-01 by CareGist pilot bundle producer (Hermes).

---

## 1. What was required

A contact-ready bundle of the **49 TPS-screened CRM records** (Henry's recorded approval 2026-08-25: outreach to the 49 TPS-screened CRM records under the approved script; customers buying leads are NOT screened and must NOT be contacted). Each row: record identifier, organisation, verified channel status (VERIFIED / PENDING / UNKNOWN), suppressing any record lacking a verified lawful channel.

## 2. BLOCKED finding

**The canonical list of the 49 TPS-screened CRM records is not present as a file, export, or database dump anywhere under the searched locations.** Every local reference describes the 49 as a founder-confirmed fact about the live CRM; none carries the record list itself. The 49 live on the CRM application database (Postgres, deployed on Neon per `docs/DEPLOYMENT_CHECKLIST.md`); no local dump or export exists, and no credential or connector to export it is available to this task (and export/contact of real CRM personal data is outside this task's permitted scope in any case).

## 3. Search trail (all executed 2026-09-01, raw)

| # | Search | Location | Result |
|---|---|---|---|
| 1 | files `*screened*` | /Users/user/CareGist | 0 matches |
| 2 | files `*tps*` | company-os | 0 matches |
| 3 | files `*.csv` (16 found, each inspected) | /Users/user/CareGist | none is a 49-record list (see §4) |
| 4 | files `*crm*` | /Users/user/CareGist | 33 matches — all code/migrations/docs; CRM data is in the DB, not files |
| 5 | files `*.db` / `*.sqlite*` | /Users/user/CareGist and company-os | 0 matches (no local CRM dump) |
| 6 | content `49` | /Users/user/CareGist | 50 matches (limit hit) — docs/code references and CQC data files only |
| 7 | content `49 (TPS\|CRM\|screened\|records)` | /Users/user/CareGist | 0 matches in normal files (only hidden CQC raw data files) |
| 8 | content `49` | company-os | 50 matches (limit hit) — every hit describes the 49 as confirmed state; **no hit contains a file path or export** |
| 9 | content `screened` | profile (ai-company-governed) | 27 matches — same nature as #8 |
| 10 | content `TPS` | /Users/user/CareGist | 50 matches — docs + `api/services/crm_tps_automation.py` (the automation that screens CRM records on the live DB) |
| 11 | read `approval-register.json` (lines ~290–350) | company-os | Evidence array holds Henry's verbatim confirmations ("the 49 have been TPS screened", "CTPS/TPS screening has been run for the 49 records on the CRM") — **no artifact path to a 49-record export** |
| 12 | read `TODAY_EXECUTION_CARD.md`, reviews `2026-08-30`/`2026-08-31` | company-os | Same: 49 referenced as fact; canonical list is on the CRM |
| 13 | session_search "49 TPS screened CRM records list export" | profile session DB | No indexed sessions found in this profile context |
| 14 | terminal `find` for `*.sqlite*/*.db/*.dump/*crm*.csv/*contact*.csv/*contact*.json/*outreach*.csv` | /Users/user/CareGist (depth 4) | Only `_provider_cache.sqlite` (CQC provider cache, not CRM) and no contact export files |

## 4. Files that were inspected and are NOT the 49 (do NOT use as recipient sources)

| File | Contents | Why it is not the 49 |
|---|---|---|
| `leads/caregist_tps_screen.csv` | 127 rows | All rows `PENDING_LICENSED_OFFICIAL_SCREEN`, call decision `HOLD_UNTIL_OFFICIAL_RESULT_AND_INTERNAL_SUPPRESSION_CHECK` — these are records awaiting official screening, not 49 already-screened records |
| `leads/caregist_ctps_screen.csv` | 127 rows | Same PENDING/HOLD status as above |
| `leads/caregist_demand_prospects_100.csv` | 100 rows | Prospect pool, not the screened 49 |
| `leads/caregist_supply_prospects_100.csv` | 100 rows | Prospect pool, not the screened 49 |
| `artifacts/radar-buyers/cqc-consultancy-buyer-list-100.csv` | 100 rows | Buyer list from public research; 100 ≠ 49 |
| `VA_REVENUE_TRACKER.csv` | 20 rows (16 FIT + 4 REVIEW) | 20 ≠ 49; it is the working tracker, not the screened CRM export |
| `artifacts/radar-verification/2026-08-22-fit-rows-1-5-verification.md` | 5 FIT-row channel verifications | Verifies channels for tracker rows 1–5 (e.g. Team Care Compliance published routes), **not** for the 49 CRM records; cannot be mapped onto the 49 without the canonical list — do not substitute |

## 5. Required bundle table — NO RECORDS POPULATED (BLOCKED)

| Record identifier | Organisation | Verified channel status | Lawful channel |
|---|---|---|---|
| *(cannot be populated — canonical 49 list not locatable)* | | | |

- **VERIFIED count: 0 of 49** (no 49-record row can be confirmed against any local source).
- **Suppression applied:** all records — no record lacking a verified lawful channel is listed, because no record could be verified at all.
- Per the hard rules and the task instruction, no identifier, organisation name, or channel is invented, guessed, or copied from another list (the 20-row tracker, the 127-row screening inputs, or the 100-row pools are explicitly NOT the 49 and must not be treated as such).

## 6. What unblocks this (for Henry)

1. Export the 49 screened CRM records (identifier, organisation, verified lawful channel) from the live CRM, OR
2. Name the file/export location where the canonical 49-record list is stored, OR
3. Confirm in writing that outreach proceeds on a different, explicitly named recipient set with verified channels.

Until one of these is recorded, the founding-buyer pilot CANNOT contact anyone, and the funnel state remains CONTACTED 0 | REPLIED 0 | QUALIFIED 0 | OFFERED 0 | ASKED_TO_PAY 0 | PAID 0.
