> HISTORICAL INVOICE-LAYOUT RECORD — NOT FOR CURRENT USE (28 October 2026). Financial-layout/history text below is preserved as evidence, not current payment instructions. The old ask-to-pay email in section 3 is retired. Current £150 Digest terms require source checks and written agreement before an invoice/payment link, and payment before the first digest. Use docs/customer-pack/enquiry-email-drafts-2026-10-16.md or 2026-09-01-ask-to-pay-script-stripe.md for current wording. Henry's approval to sell the existing £150 Digest stands.

# Draft Invoice Layout + Ask-to-Pay Wording — FOR INSPECTION ONLY

Status: `DRAFT — NOT FOR ISSUE`. Created for fresh-context inspection by henry-proof
before any buyer-facing approval. No invoice has been issued. No buyer name,
address, amount, or invoice number is attached. Template fields only.

Created: 2026-08-25 by CareGist lane (hermes @caregist).

---

## 1. Scope of this document

This is the exact invoice layout and the exact ask-to-pay wording that would be
used for the proposed CareGist Radar pilot pack (4 weekly digests, £150, manual
fulfilment). It is a template: every field below marked `[PLACEHOLDER]` must be
filled by Henry's recorded approval before use.

Blocks that remain pending Henry approval:
- `[SELLER LEGAL NAME]` and address — H-Kay Limited registered details.
- `[BUYER NAME/ADDRESS]` — the specific consultancy organisation.
- `[SETTLEMENT ACCOUNT]` — no named UK bank account is on record; manual
  transfer requires one, or Henry must decide to activate Stripe live.
- `[INVOICE NUMBER]` / `[INVOICE DATE]` / `[DUE DATE]`.
- `[AMOUNT]` = £150.00 only after Henry approves the price.

---

## 2. Invoice layout (fields, in display order)

```
[SELLER LEGAL NAME]
[SELLER ADDRESS]
[SELLER VAT / COMPANY NUMBER if applicable]

INVOICE
Invoice number:   [INVOICE NUMBER]
Invoice date:     [INVOICE DATE]
Due date:         [DUE DATE] (payment due within 14 days of invoice date)

BILL TO
[BUYER NAME/ADDRESS]
[ATTN: contact/email]

DESCRIPTION OF SERVICES
CareGist Radar pilot pack: four (4) weekly CQC intelligence digests
for the [REGION] region, delivered by email/PDF.
Period: Week 1 [DATE] – Week 4 [DATE]
Quantity: 4 × weekly digest
Unit price: £37.50
Total: £150.00

PAYMENT DETAILS
Bank transfer to:
  Account name:   [SETTLEMENT ACCOUNT NAME]
  Sort code:      [SETTLEMENT SORT CODE]
  Account number: [SETTLEMENT ACCOUNT NUMBER]
  Reference:      [INVOICE NUMBER]

OR pay by card via Stripe [if Henry approves Stripe live activation]

TERMS
Payment due within 14 days of the invoice date.
This invoice is issued on completion of the first digest delivery and is
conditional on delivery of the four digests as described.
```

Notes for the reviewer:
- Amount shown as £37.50 × 4 to make the £150 visible and auditable.
- The invoice is only issued AFTER first digest delivery — see section 4,
  "delivery stop rule": no invoice without a deliverable promise we can keep.
- No VAT line is included because no VAT decision is recorded; Henry/H-Kay
  must confirm whether VAT applies before any live invoice.

---

## 3. Ask-to-pay email — superseded on 28 October 2026

The former email has been removed from operational use because it asked for bank transfer on 14-day terms after first delivery. Its original text is preserved in artifacts/draft-review/2026-10-28/originals. Use the refreshed payment-stage draft in `2026-09-01-ask-to-pay-script-stripe.md` or `docs/customer-pack/enquiry-email-drafts-2026-10-16.md`. Do not reuse payment instructions from the historical invoice-layout sections of this record.

## 4. Delivery stop rule (unchanged)

- If no verified CQC data path exists at delivery time, do not promise a
  digest and do not issue an invoice; inform the buyer before money moves.
- The sample must be described as a dated February 2026 format sample unless
  the digest is compiled from a verified live source.
- No price communication, invoice, payment, deployment, or live-service
  change until the relevant approval gates are recorded.

---

## 5. Evidence trail

- This draft is the object of henry-proof inspection (fresh-context).
- The fresh ODS path test result is recorded separately:
  `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.md`
  (compiled 2026-08-25 from CQC "Care directory with filters" 04 Aug 2026 ODS).
- Determinism re-run evidence:
  `artifacts/radar-live/2026-08-25-generator-determinism-proof.md` (byte-identical).
- Verification status of the first five FIT rows:
  `artifacts/radar-verification/2026-08-22-fit-rows-1-5-verification.md`
  (rows 3–5 marked PROVISIONAL pending independent reviewer confirmation).
