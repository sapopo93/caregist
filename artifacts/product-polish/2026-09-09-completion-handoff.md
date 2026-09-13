# CareGist product-polish handoff, 9 September 2026

## Objective

Bring the retained £795 Territory Opportunity Brief up to a coherent, evidence-led delivery standard, and give every recorded CareGist product the same clear presentation of price, delivery, evidence and current availability. Do not turn an unfinished product into a purchasable offer.

## Files changed

- `artifacts/product-polish/brief-preview/build_preview.py`: validates retained sources and delivery assets before rendering; packages the CSVs, workbook and the four-page executive PDF; writes `delivery-manifest.json`; corrects unsupported evidence wording.
- `artifacts/product-polish/brief-preview/index.html`: regenerated £795 preview and its four delivery files.
- `artifacts/product-polish/build_catalogue.py` and `catalogue/index.html`: generate a 10-product local catalogue from `catalogue-evidence.json`. Every card says whether a buyer receives a delivery today.
- `artifacts/product-polish/build_radar_pilot_sample.py`, `radar-pilot-sample/index.html`, and `radar-pilot-sample/caregist-radar-gloucestershire-dated-format-sample.pdf`: dated £150 Radar format sample from the retained 4 August 2026 CQC edition.
- `artifacts/product-polish/verify_product_polish.py` and `verification.json`: read-only delivery, file-integrity and local-link verifier.

## Checks performed and results

- `python3 artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/verify_pack.py`: PASS. 353 locations, 329 providers, 25 shortlisted organisations, two retained source hashes, 25 representative page checks, three workbook sheets, no workbook error cells and a four-page executive PDF.
- `python3 artifacts/product-polish/brief-preview/build_preview.py`: PASS. Rebuilt the preview only after its sources and four delivery files passed validation.
- `python3 artifacts/product-polish/build_catalogue.py`: PASS. Rendered 10 catalogue entries from the controlled catalogue record.
- `python3 artifacts/product-polish/build_radar_pilot_sample.py`: PASS. Created one PDF page and its web view. Rendered with Poppler and visually reviewed.
- `python3 artifacts/product-polish/verify_product_polish.py`: PASS. 10 catalogue products, 4 verified £795 assets, 4 Brief PDF pages, 1 Radar sample PDF page and 32 working local links.
- Browser review: £495 says “No report exists to deliver today”; £150 says the four-week source and cadence are unverified; £795 exposes all four retained files.

## What a buyer receives today

- £795 Territory Opportunity Brief: a complete local prototype for Birmingham and Solihull. It contains a 353-location, 21-column CSV; a 25-organisation shortlist with published fact, reason, qualification question and uncertainty; a three-sheet workbook; and a four-page executive PDF. It remains launch preparation because the buyer criteria in this prototype are illustrative and the commercial gates are open.
- £495 Market Movement Report: no buyer delivery. No completed edition or compatible event ledger exists, so a payment must not be taken.
- £150 Radar pilot: the recorded promise is four weekly email/PDF digests for an agreed region, with no software. The new dated Gloucestershire sample demonstrates the format only. It does not verify four future weekly deliveries, so no new buyer payment should be taken.

## Unresolved issues that affect selling today

- £795: buyer-specific criteria and a delivery start still need to be agreed. CareGist is not currently VAT-registered. Legal/Terms approval and a payment route are unresolved. Review the customer wording before VAT registration takes effect.
- £495: build and independently check one real edition from compatible source editions and a reproducible event ledger before accepting payment.
- £150: independently verify the fresh weekly CQC source route and four-week delivery cadence before accepting a new pilot buyer.
- All paid products: checkout and legal/Terms are still fail-closed. No production, billing or outbound action was taken here.

## Exact next action

Assign the named fresh-source verification to the independent re-test step for the £150 pilot. If it passes, freeze a four-week delivery run and evidence packet before any new payment request. In parallel, do not accept a £495 order until one completed Market Movement Report edition is built and independently checked.

## Source references

- Founder decision: `/Users/user/.hermes/profiles/ai-company-governed/company-os/chief-of-staff/decisions/2026-09-07-caregist-launch-one-off-products.md`
- £795 retained pack: `artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/pack-data.json` and `verify_pack.py`
- £150 retained source: `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.json`
- Controlled catalogue: `artifacts/product-polish/catalogue-evidence.json`

COMPLETE: no escalation needed for the local product-polish objective. Commercial release remains gated by the issues above.
