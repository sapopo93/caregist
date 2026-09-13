# CareGist Radar — Recipient/Channel Verification Evidence (FIT rows 1–5)

- **Prepared by:** Hermes (`@caregist`) completion audit, safe zero-spend prep per VA_MONDAY_REVENUE_PACK.md STOP rule 4 and @sales' verification brief.
- **Date:** 2026-08-22 (BST)
- **Method:** Direct GET of each organisation's own public website (browser UA), extraction of published contact routes only. **No named-individual harvesting, no enrichment, no contact made, no spend.**
- **Scope note:** This covers the first 5 FIT rows — the pack's day-1 verification scope ("Mon 24 = verify first 5 FIT"). Rows 6–16 remain `VERIFY recipient/channel before contact`.

## Verified routes (org-level, published on the org's own site)

| # | Organisation | Source URL | Channel | Verified value | Evidence | Status |
|---|---|---|---|---|---|---|
| 1 | CQC Consultants | https://cqc-consultants.com/ | Email | dan@cqc-consultants.com | Published mailto on homepage: "Email: dan@cqc-consultants.com" | ✅ VERIFIED |
| 1 | CQC Consultants | https://cqc-consultants.com/ | Phone | 01843 278765 | Published tel: link + "Phone: 01843 278765" text; registered office 128 City Road, London | ✅ VERIFIED |
| 2 | Fulcrum Care Consulting | https://fulcrumcareconsulting.com/cqc-consultancy/ | Phone | 020 3411 4014 | "Call Us Now on 020 3411 4014"; "For Urgent Help Call 0203 411 4014" (same number, alternate formatting) | ✅ VERIFIED |
| 2 | Fulcrum Care Consulting | https://fulcrumcareconsulting.com/cqc-consultancy/ | Email | info@fulcrum.care | Present in fetched page content | ✅ VERIFIED |
| 3 | The UK Care Consultants | https://www.theukcareconsultants.co.uk/ | Phone | 0203 475 4334 | Contact page visible text: "Contact Information 0203 475 4334"; tel: link present but masked in markup (+442****4334 — consistent prefix); no published email found (contact form only) | ✅ VERIFIED (phone only) |
| 4 | Cura Compliance UK | https://curacompliance.co.uk/ | Phone | 07470 390526 | JSON-LD schema `telephone: "07470390526"`; tel: link masked in markup (+447****0526 — consistent) | ✅ VERIFIED |
| 4 | Cura Compliance UK | https://curacompliance.co.uk/ | Email | info@curacompliance.co.uk | Present in fetched page content | ✅ VERIFIED |
| 5 | Team Care Compliance | https://teamcarecompliance.org.uk/ | Phone | 0115 845 0220 | Published on site (tel: link) + Nottshelpyourself directory; confirmed by henry-proof external check | ✅ VERIFIED (primary) |
| 5 | Team Care Compliance | https://teamcarecompliance.org.uk/ | Email | hello@teamcarecompliance.org.uk | Published on site + Nottshelpyourself directory; confirmed by henry-proof external check (also kerry@teamcarecompliance.org.uk, Director Kerry McCulloch — org-route only, address the organisation) | ✅ VERIFIED |
| 5 | Team Care Compliance | https://teamcarecompliance.org.uk/ | Phone (alt) | 07155 410220 (+44-715-541-0220) | JSON-LD ContactPoint only; NOT independently confirmed by henry-proof | ⚠️ PROVISIONAL — do not use until verified; primary is 0115 845 0220 |
| 5 | Team Care Compliance | — | Email (old) | help@teamcarecompliance.org.uk | Recorded previously from JSON-LD; NOT confirmed on published materials by henry-proof — likely typo; replaced by hello@ above | ❌ REMOVED — do not use |

## Excluded as template/placeholder noise (not routes)

- `user@domain.com` (CQC Consultants — form validation example string)
- `00000000000000` (Fulcrum — template)
- Date-like strings matched by the phone regex (`026-08-24 22`, `026-05-05 18`, `026-08-25 03`) — not contact numbers
- `0561705-866`, `0883-8248-47`, `0888086247`, `04239279664`, `00316127`, `005 0 0 0 21 7` (CQC/Team pages — malformed/template matches)

## Compliance notes

- **PECR/org-level:** All routes are corporate contact channels published by the organisation itself. No personal data harvested; no named individuals logged as recipients.
- **CTPS/TPS screening:** REQUIRED before any phone contact (pack STOP rule 4 + @sales brief). Status: **NOT YET SCREENED — pending Henry's outreach-scope approval; screening is part of the approval gate.** Any number found on CTPS (companies) must not be cold-called.
- **No-name opener:** Where only an org-level route is verified (e.g., row 3, phone only), the VA must use a no-name opener — the pack's "Hi [first name]" wording must NOT be used. Variant needs Henry approval before day-1 calls.
- **Team Care Compliance (row 5):** primary route is now 0115 845 0220 + hello@teamcarecompliance.org.uk (both confirmed on published materials by henry-proof, 2026-08-25). `07155 410220` remains PROVISIONAL (JSON-LD only) and `help@teamcarecompliance.org.uk` is REMOVED (not confirmed, likely typo). Use only the VERIFIED routes; the VA must still address the organisation, not named individuals (Kerry McCulloch is a published director, not a personal-data recipient).
- **CQC Consultants (row 1):** `dan@cqc-consultants.com` is a published corporate mailbox (first-name local part) — acceptable as the org's own published contact, but flag to VA: address the organisation, not the individual, unless the mailbox owner introduces themselves.

## Source artifacts

Raw HTML snapshots under `artifacts/radar-verification/`:
- `CQC_Consultants.html` (2.0 MB)
- `Fulcrum_Care.html` (170 KB)
- `ukcontact.html` (41 KB — The UK Care Consultants contact page)
- `Cura_Compliance.html` (501 KB)
- `Team_Care_Compliance.html` (298 KB)

## Audit status

- Journey state: **AMBER** — verification for first 5 FIT rows complete with published-route evidence; contact itself remains gated on Henry's recorded approvals (price, invoice/payment, outreach scope, region, no-name opener, CTPS/TPS screening).
- This evidence does **not** constitute approval to contact. It unblocks day-1 prep only.
