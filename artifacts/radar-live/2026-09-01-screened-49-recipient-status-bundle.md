# CareGist Founding-Buyer Pilot — Screened-49 Recipient Status Bundle

Source: production CRM `crm_contacts` (Neon Postgres), read-only extraction, 2026-09-01T04:58:37+00:00.
Extract: `artifacts/radar-live/2026-09-01-screened-49-crm-extract.json` (49 records, minimal fields).

## Status

- **49 records** match Henry's screened set (CRM total = 49; all `market_code GB`, all `lifecycle assigned`).
- **TPS/CTPS screening completed 2026-08-13** on every record (`phone_screened_at` present for 42/42 clear).
- **42 CALLABLE** (`clear`) — phone channel only.
- **7 DO-NOT-CALL** — 6 `tps` (TPS-registered), 1 `unknown` (screening unresolved).
- **0 email addresses, 0 contact names** on file → the email pilot (buyer email + invoice + Stripe link) **cannot reach these records as-is**.
- `email_marketing_basis = none` on all 49 → per CRM campaign rules, email sends are disabled until a manager records a valid basis for every selected contact.

## Personal-data purpose

Processing is limited to the 2026-08-25 approved outreach purpose: contacting the TPS-screened CRM set about the CareGist founding-buyer pilot (procurement-concierge digest at £150). No data leaves the machine; no channel is fabricated; extraction was read-only.

## Do-not-call set (7) — never contact without fresh screening

- `UNKNOWN` — CareGist authorised test line
- `TPS` — Euroclydon Nursing Home
- `TPS` — Muirhead Dental Health Addingham
- `TPS` — Stoke Road Dental Practice
- `TPS` — The Brook Health Centre
- `TPS` — The Vintry
- `TPS` — Woodford Dental Care

## Callable set (42) — phone channel, no email on file

- 247 Serenity Care Limited
- Accedo Herts North
- ADHD Lifestyle Academy - Remote Clinical Advice Service
- Alina Homecare Services Ltd Weston-Super-Mare
- Auricle Ear Health and Microsuction
- Beacon Lodge Dental Surgery
- CareYourWay Wilmslow
- Clarity Homecare Taunton
- Cranstoun Royal Borough of Windsor and Maidenhead
- DaVita (UK) Limited - Tolworth
- Edenbridge Manor Care Home
- Eunique Dental
- Glide Health & Dental Hygiene
- Hassle Free Healthcare Limited
- Hey Baby 4D Sunderland
- Hummingbird Domiciliary Care Ltd
- In-House Care Services Ltd
- Joy Care Solutions Ltd
- Kind Hearts Home Care Ltd
- Leonie Bryan - Home Address
- Lifeways Community Care Limited (Southampton)
- LoveMyLife Ltd
- Main office
- MedHealth Ultrasound Southampton
- Merlin Park
- Ms Julienne Espineli
- Multi-Care Community Services Ltd - Bedfordshire
- New Vision Care Services Limited
- Newton Leys Dental and Implant Clinic
- Northampton Dental Clinic
- Opaline Dental Studio
- Orchid Assisted Living Limited
- Quay Health
- Rejuven8 Clinic
- Reliable Healthcare and Support Services Ltd
- Serenity (UK) Global Healthcare Limited
- Shephall Dental Surgery
- Tetbury Dental Practice
- The Bridge Dental Care
- TIC Rochdale
- YoD Care Services (Hereford)
- Zen House Dental Battersea

## Blocking facts for Henry's gate

1. **No email channel exists for the 49.** The approved email script cannot be sent to them without email addresses (verify on published routes, or supply from CRM).
2. **Email sends additionally require a manager-recorded marketing basis** in the CRM (`email_marketing_basis`), a founder-only action.
3. **Phone outreach to the 42 clear requires an approved call script and calling tooling** — no phone script has been approved; live Twilio/calling was previously BLOCKED.
4. Invoice/Stripe-link issuance remains founder-only (exact buyer, invoice number/date, VAT, live payment link).

This bundle supersedes the earlier `2026-09-01-screened-49-contact-bundle.md` assumption that the 49 had email channels.