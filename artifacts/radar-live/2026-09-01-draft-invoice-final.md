# CareGist Radar pilot pack — Final Invoice Draft (Stripe route, per approved 2026-08-25 layout)

**File status:** `DRAFT — NOT FOR ISSUE`. Follows the approved invoice layout of `2026-08-25-draft-invoice-layout-ask-to-pay.md` §2 with the payment route corrected to **Stripe (card), seller H-Kay Limited**, settling to **H-Kay Limited's Starling Bank account** (Henry's recorded approval 2026-08-25). No invoice has been issued. No buyer has been named or approached.

**Pre-issue gates (all still open):** Henry's 06:00 approval of this exact draft; Henry's confirmation of the buyer (name/address from the screened set — placeholder below); invoice number/date; live Stripe payment link issued by the founder; VAT treatment confirmed by the accountant. DO NOT ISSUE until all gates are recorded.

Created: 2026-09-01 by CareGist pilot bundle producer (Hermes).

---

## Invoice (fields in display order)

```
SELLER
H-Kay Limited
C/O Bilberry Accountants Ltd, Castle Court, 41 London Road,
Reigate, England, RH2 9RJ
Company number: 10417923 (status ACTIVE — Companies House verified 2026-08-25)
VAT registration: TBC — pending accountant confirmation

INVOICE
Invoice number:   [INVOICE NUMBER]
Invoice date:     [INVOICE DATE]
Due date:         [DUE DATE] (payment due within 14 days of invoice date)

BILL TO
[BUYER NAME/ADDRESS — PLACEHOLDER. Henry must confirm the exact buyer name
and address before this invoice may be issued.]
[ATTN: contact/email]

DESCRIPTION OF SERVICES
CareGist Radar pilot pack: four (4) weekly CQC intelligence digests
for ONE England region — the [REGION] region — delivered by email/PDF.
Period: Week 1 [DATE] – Week 4 [DATE]
Each digest is compiled from the public CQC register (official ODS
snapshot) for the week and states its snapshot date; it reflects only
publicly visible signals at compile time. In some weeks there may be no
new registrations or rating changes in the region; the digest will state
that plainly. Quantity: 4 × weekly digest
Unit price: £37.50
Total: £150.00

PAYMENT DETAILS
Pay £150 via Stripe (card), seller H-Kay Limited. Funds settle to H-Kay Limited's Starling Bank account. Payment reference: [INVOICE NUMBER].
Secure Stripe payment link: [STRIPE PAYMENT LINK — founder to issue and verify]

TERMS
Payment due within 14 days of the invoice date.
This invoice is issued on completion of the first digest delivery and is
conditional on delivery of the four digests as described.

VAT
VAT treatment: TBC — pending accountant confirmation. If VAT applies to
this supply, the correct rate will be added before this invoice is issued;
no payment will be requested without the VAT position confirmed.
```

---

## Truthfulness and compliance notes (recorded)

- **Promise wording** above is truthful: one England region, four weekly digests, ODS-based, zero-change weeks possible, no renewal.
- **Payment line** in PAYMENT DETAILS above is **byte-for-byte identical** to the payment line in `2026-09-01-buyer-email-draft-stripe.md` and `2026-09-01-ask-to-pay-script-stripe.md`. The prior settlement-account payment block is removed in full; the payment route is Stripe (card), seller H-Kay Limited, per Henry's 2026-08-25 approval (funds settle to H-Kay Limited's Starling Bank account).
- Invoice is issued only AFTER first digest delivery (delivery stop rule, unchanged from the approved layout §4): if no verified CQC data path exists at delivery time, no invoice is issued and the buyer is told before any money moves.
- No buyer name/address, amount, or invoice number is attached; `[PLACEHOLDER]` fields require Henry's recorded approval before issue.
- No claim of CQC endorsement; no urgency/exclusivity language; no renewal solicitation.

## Evidence trail

- Companies House verification of H-Kay Limited (ACTIVE, no. 10417923): `artifacts/radar-live/2026-08-25-hkay-companies-house-verification.md`.
- Approved layout superseded on payment route only: `artifacts/radar-live/2026-08-25-draft-invoice-layout-ask-to-pay.md`.
- Fresh ODS digest compiled and verified for Gloucestershire: `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.md`; determinism re-run: `artifacts/radar-live/2026-08-25-generator-determinism-proof.md` (byte-identical).
- Price fairness evidence (condition for £150): `artifacts/radar-live/2026-09-01-fairness-evidence-150-pilot.md`.
