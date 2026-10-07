# CareGist first-sale offer: one registration factsheet

Prepared 5 October 2026. Status: concrete offer for owner approval; no customer order, payment or acceptance is assumed.

## Customer offer

CareGist supplies a manually checked, dated factsheet for **one named CQC provider and one named registered location in England**. Quantity: one pack, comprising a PDF, UTF-8 CSV and SHA-256 delivery manifest. Proposed fixed price: **£49**. Before quoting, H-Kay Limited must confirm the final tax-inclusive amount and VAT treatment. The seller's legal identity, registration details, support contact and invoice details must appear on the accepted quote.

The quote names the provider ID, location ID, recipient and delivery deadline. Proposed turnaround: one working day after scope agreement and confirmed payment, subject to a named operator accepting that deadline. If an operator is unavailable, agree a later deadline before taking payment.

## Exact delivery specification

The PDF and CSV contain: provider/location identifiers and names; published registration status and start/end dates where available; regulated activities; service types; latest published rating or the source's explicit not-rated/not-inspected status; source URLs; source retrieval time; human reviewer; omissions and conflicts. The manifest identifies the exact delivered files and their hashes. Do not infer a location rating from a service rating or equate an archived location with a closed business.

Verify the selected records directly against the current CQC source on the day of production, within 24 hours of delivery. Preserve the selected source response/page, its URL, retrieval timestamp and hash privately with the delivery record. An incomplete bulk reconciliation does not provide this selected-record verification. Unresolved identity, registration or rating conflicts stop delivery and payment collection until the customer agrees a narrower accurate scope.

No residential address or service-user information is needed. Omit addresses from this offer. Exclude personal contacts, inspection-report narrative, third-party text, logos, compliance certification, legal advice, endorsement, forecasts, monitoring and promised future updates.

## Source permission

CQC publishes its reusable data under the Open Government Licence and requires acknowledgement: [Using CQC data](https://www.cqc.org.uk/about-us/transparency/using-cqc-data). Its published terms exclude third-party rights and prohibit implied endorsement: [CQC terms](https://www.cqc.org.uk/about-us/our-policies/terms-conditions). Record the applicable licence and exclusions for the precise source used: [OGL v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

Include in each real pack: “Contains public sector information licensed under the Open Government Licence v3.0. Source: Care Quality Commission. CareGist is independent of CQC; no endorsement is implied.” Use only covered factual fields; obtain separate permission or remove excluded material. The synthetic sample uses invented facts and does not claim CQC provenance.

## Draft customer terms and acceptance criteria

Before payment, the customer agrees the written scope, final price, deadline, delivery channel, these criteria and the correction/refund process. This is a point-in-time factual information service. State the source's own update limitations and list any unavailable fields explicitly.

Acceptance means all three files open, the specified IDs match, the CSV agrees with the PDF, included facts match the saved source at the stated retrieval time, attribution and limitations appear, and the agreed recipient receives the pack by the agreed deadline. A source's explicit missing or not-rated value is acceptable if accurately disclosed in the agreed scope. A missing promised file, wrong identity, unsupported fact, undisclosed omission or missed agreed deadline is grounds for rejection.

Ask for written acceptance or a specific rejection within five working days. Silence is **not** acceptance. Correct a substantiated defect within two working days of notification, if the customer agrees; otherwise offer a full refund for an undeliverable or rejected defective pack. A later CQC change does not establish that a correctly dated pack was defective. These draft terms require seller approval before use and do not remove statutory rights.

## Supported manual fulfilment

1. Record the genuine buyer, scoped IDs, final price, named operator and agreed deadline in a quote. Obtain customer agreement before payment.
2. Record the exact source/licence evidence and human check. Do not invent a paid order or mark a synthetic pack as a customer delivery.
3. Produce the PDF/CSV/manifest using `scripts/render-registration-factsheet.py`. The labelled sample is in `docs/first-sale/`; it is neither an order nor proof of production delivery.
4. Have a second person check the pack against the saved sources and accepted quote. Store their dated approval. This satisfies the repository's independent approval requirement; model output does not approve itself.
5. Issue an authorised invoice or agreed payment request through the existing approved merchant process. Confirm the actual payment reference/status before recording payment; do not enable automated checkout for this offer.
6. Deliver the exact hashed pack to the agreed recipient using an authorised channel. Record recipient, channel, timestamp, file hashes and transmission receipt. Record customer acceptance/rejection separately from payment.
7. Record corrections, refund decisions and completion against that genuine quote/order. A local render, successful send attempt or payment alone does not prove customer acceptance.

## Evidence needed to sell this specific offer

- Owner approval of the final £49 proposal, VAT treatment, seller/contact details and draft terms.
- A named operator and independent checker accepting the quoted delivery deadline.
- A genuine prospective buyer agreeing the one-provider/one-location scope, final price and delivery criteria. No previous paid order is required.
- Selected-source rights/provenance and factual verification for that pack; payment and authorised delivery capability ready for that quote.

The existing rolling observation window remains a gate for automated continuous products. It is not substituted for this offer's dated selected-source checks, and no existing paid-access gate is relaxed.
