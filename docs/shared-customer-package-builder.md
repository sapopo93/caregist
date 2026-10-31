# Shared customer package builder

Status: implemented locally; not deployed or release-approved.

## Product contract

| Public product ID | Internal ID | Price | Product-specific payload |
| --- | --- | ---: | --- |
| `territory-opportunity-brief` | `territory_opportunity_brief` | £745 one-off | `brief.pdf`, provider-level `providers.csv` |
| `weekly-digest` | `weekly_digest_pilot` | £150 for four issues | `digest.pdf`, `digest.csv` |

Both use `api/services/customer_package.py`. Existing product generators remain authoritative for content. The
shared layer adds `selection-confirmation.pdf`, `selection.json`, `evidence.json`, and `manifest.json`, then creates
one immutable ZIP.

The frozen `territory-brief-template-v2-2026-10-29` package was used as the content-quality reference for selection,
evidence, and dossier boundaries. Its workbook is not copied into the live product: the current customer promise is
PDF plus CRM-ready CSV, so adding an XLSX would silently expand the contract.

## Selection snapshot and binding

The snapshot records the order and customer references, product, verified payment reference, selection version,
template/source versions, geography, service and rating/context criteria, provider cap, buyer objective, requested
files, confirmation time, and explicit preview status. Its canonical JSON is SHA-256 hashed. Production customer
email is represented by a one-way SHA-256 binding rather than embedded as plaintext in the private blob.

Paid builds require a payment reference. Only the standalone preview command can omit it, and preview status is
written into the selection, manifest, and confirmation PDF. Publication refuses an order/customer mismatch.

## Provider and research boundary

Territory Brief rows are deduplicated by CQC provider ID before the confirmed cap is applied. Conflicting names,
duplicate final records, empty selections, and selections above 50 or above the buyer's cap fail closed; rows are
never silently truncated or padded by the package layer. The product generator's documented deterministic top-N
selection states both the eligible-provider count and selected count in the PDF and every CSV row. The final
provider IDs, names, and locations must exactly match `providers.csv`; malformed CSV or incomplete PDF bytes fail
closed. Tests cover 1, 8, 24, and 50 distinct providers.

A completed researched dossier must contain published findings, subsequent evidence, a buyer question,
comparative reason, disconfirming evidence, next step, owner role, and decision effect. Every other record is
labelled exactly `Qualification incomplete`, kept in a candidate register, and excluded from the researched
shortlist. Customer-readable output warns that historic ratings do not establish current deficiency, budget, need,
or buying intention.

## Integration and retry behaviour

The manual workflow stores the fixed requested formats with the quoted scope, rebuilds from that ledger state after
payment, attaches the complete ZIP alongside the existing direct files, and creates no email when packaging fails.
The Stripe-confirmed Territory Brief path builds the same package in memory, uploads PDF/CSV/ZIP, persists the
selection and manifest, and creates all three entitlements before marking the order fulfilled.

Each version includes both the selection hash and a content hash. Identical retries converge on the same path,
including concurrent workers. Changed content creates a new version without overwriting the old one. Interrupted or
tampered publication fails closed and leaves no live partial directory. Blob uploads that fail part-way can leave
private orphan objects (an existing platform limitation), but the database transaction does not mark delivery or
queue an email. Stripe retries derive the confirmation time from durable `paid_at` evidence or the authoritative
Checkout Session creation time, so a retry does not create a new selection hash merely because wall-clock time moved.

## Preview and verification

`python -m tools.build_customer_package_preview --preview ...` is the explicit admin-only, no-delivery path. It
does not read or mutate order/payment state.

Local verification on 30 October 2026:

- full Python suite: 1,567 passed, 143 skipped (Postgres-dependent tests skipped without an integration URL);
- frontend unit suite: 194 passed;
- Ruff and migration governance: passed;
- realistic CQC fixture: a 30-provider Territory Brief and a rendered Weekly Digest both passed through the shared
  builder; adversarial cases cover wrong binding, duplicates, overflow, missing outputs, tampering, interruption,
  concurrent retry, and ZIP-upload failure.

## Current limits

- This change does not deploy, apply migration `072`, or enable any fail-closed commercial gate.
- Weekly Digest remains the existing operator-led IMAP draft workflow; the shared builder does not automate sends.
- Applying the migration and exercising the Postgres integration tests require the normal staged migration/recovery
  procedure and a disposable integration database.
- Release approval still requires the independent review and customer-journey gates in `AGENTS.md`.

## 31 October follow-up

The earlier “not deployed” status above is historical: PR #153 is already on main
and production. The dated follow-up audit is
`artifacts/report-quality/2026-10-31/REVIEW.md`. It separates bounded engineering
verification from the unpassed premium report and operational acceptance gates.
New migration 074 permits confirmed provider caps of 1–50. Digest generation now
uses a content-bound source register, preserves registration-ending uncertainty,
and refuses mismatched scope, dates, customer/order or event content. Exclusion
parity is retained as counts/hashes rather than duplicating purge-controlled IDs.
