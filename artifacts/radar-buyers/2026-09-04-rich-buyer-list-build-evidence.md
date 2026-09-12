# Rich Consultancy Buyer List — Build Evidence Record (2026-09-04)

**Status:** RESEARCH COMPLETE — feeds Henry's approved-send-list gate. No outreach performed.

## Deliverable
`/Users/user/CareGist/artifacts/radar-buyers/cqc-consultancy-rich-buyer-list-100.csv`

## Method
- Seed: `cqc-consultancy-buyer-list-100.csv` (100 consultancies, previously "public-source candidate; manual fit check required", no channels).
- Six parallel enrichment workers (one accountable producer per slice, ranks 1–17 / 18–34 / 35–51 / 52–68 / 69–85 / 86–100), each doing read-only public-web research: site liveness, CQC-fit confirmation, verified business email + phone from published pages, regions served, South-West relevance.
- Cross-checked against canonical verified-email records (`2026-08-22-fit-rows-1-5-verification.md`, approval-register deliverability notes) so the GO-authorised rows 1–5 stay consistent.
- Independent CoS QA after merge: sample of 8 emails re-verified at source URLs (all PASS), DEAD rows inspected for technical evidence, schema/rank integrity validated (100/100, no dupes/missing).

## Results
| Metric | Count |
|---|---|
| Rows | 100 |
| Site LIVE | 97 |
| Site DEAD (removed from contactable set) | 3 (ranks 50, 58, 87) |
| CQC-fit CONFIRMED | 92 |
| CQC-fit UNCLEAR (manual review) | 8 |
| Rows with ≥1 verified business email | 74 |
| Rows with verified phone | 79 |
| South-West relevant (incl. Gloucestershire) | 7 (79 UNKNOWN — regional scope not stated on most sites) |

## GO-authorised rows 1–5 (send state reconciliation)
| Row | Org | Email (source) | Phone | GO match |
|---|---|---|---|---|
| 1 | CQC Consultants | dan@cqc-consultants.com (homepage mailto, verified 2026-08-22; homepage since redesigned, mailto no longer published — pre-send re-check advised) | 01843 278765 | email VERIFIED → retained |
| 2 | Fulcrum Care Consulting | info@fulcrum.care (contact page) | 020 3411 4014 | match |
| 3 | The UK Care Consultants | — (form only) | 0203 475 4334 | phone-only as recorded |
| 4 | Cura Compliance UK | info@curacompliance.co.uk (contact page) | +44 7470 390526 | match |
| 5 | Team Care Compliance | hello@teamcarecompliance.org.uk (site footer) | 07456 388400 (WhatsApp); 0115 845 0220 on record | match |

Tracker send-state (VA_REVENUE_TRACKER.csv, 2026-09-04 read): rows 1–5 all `contacted: NOT_STARTED` — the four GO-authorised emails have **not been sent**. GO file records the send as Henry's action.

## Notes / flags for manual fit review
- Rank 94 Stratum Consulting: email verified (start@stratum-consulting.co.uk) but site targets private-practice medical consultants, not CQC care-provider registration — weak fit, confirm before inclusion in any send wave.
- Rank 6 CQC Medisolutions: no published email/phone on site.
- 79/100 do not state service region; 7 explicitly South-West/Gloucestershire. The £150 pilot is one England region (Gloucestershire verified sample exists) — regional-fit columns are informational; the digest can be produced for any single England region, so non-SW consultancies are NOT excluded, they just need their region offered.

## Governance
- Read-only research only; no emails/phones contacted; no personal data collected (business contact channels from published pages only).
- No changes to send gates: outreach still requires Henry's approved-send-list decision per GO 2026-09-02 07:06 (rows 1,2,4,5) or a new GO.
- Verdict: `DONE` (research artifact). Readiness gate for send: `NOT READY` — requires Henry's send decision; row 1 route re-check recommended.
