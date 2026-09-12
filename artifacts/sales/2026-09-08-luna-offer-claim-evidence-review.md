# Luna offer review: claim to evidence

> SUPERSEDED conclusions: the [primary-evidence review and price defence](/Users/user/CareGist/artifacts/sales/2026-09-08-offer-price-defence-and-handoff.md) inspected the 7 September founder decision, approval register, sample CSVs and digest JSON. The £795 Brief is an authorised launch SKU in preparation; the £150 price had conditional approval and recorded contacts. Missing rendered evidence is not proof that the underlying fields cannot be delivered. Read the replacement review before acting on the historical findings below.

**Scope:** `artifacts/sales/2026-09-08-caregist-radar-pilot-one-page-offer.md`

**Reviewed:** 8 September 2026

**Verdict:** **PARTIAL.** The £150 pilot has a documented candidate scope and price evidence. It is not sellable today because CareGist cannot yet prove delivery of every promised item.

| Luna offer claim | Evidence inspected | Verdict | Corrected position |
|---|---|---|---|
| Buyer: UK CQC compliance and quality-improvement consultancies | `docs/CAREGIST_MASTER_STRATEGY.md` §4; `VA_MONDAY_REVENUE_PACK.md` §1 | PASS | This is the documented pilot buyer. |
| Four weekly email/PDF digests for one England region | `VA_MONDAY_REVENUE_PACK.md` §§1, 11; `artifacts/radar-live/2026-09-01-draft-invoice-final.md` | PARTIAL | It is the proposed pilot scope and cadence. It is not a delivery commitment until the source and approval gates pass. |
| New registrations or applicants | `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.md`; `artifacts/radar-live/2026-08-25-ods-path-test-result.md` §3 | PARTIAL | The sample supports new registrations. It does not evidence a separate applicant event, so “applicants” was removed. |
| Rating changes | `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.md` lines 13–30 | FAIL | The source file has the latest rating and its publication date, not rating history. The correct event is “rating published”, not “rating changed”. |
| Provider name, service type, location, CQC reference, plain-English note and public source link for every item | Available fresh digest: `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.md`; proposed content: `VA_MONDAY_REVENUE_PACK.md` §1 | PARTIAL | The available fresh digest proves provider and location details for one rating publication. It does not prove service type, item-level CQC reference, plain-English note, or item-level public link in every delivered digest. These were removed from the offer as promised deliverables. |
| Each digest states a snapshot date | `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.md` §§1–2 | PASS | The available digest states the source edition and window. |
| Quiet weeks are disclosed | `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.md` §§3–4; `artifacts/radar-live/2026-09-01-draft-invoice-final.md` | PASS | The example contains zero registrations, and the draft invoice says zero-change weeks must be stated plainly. |
| £150 for four digests (£37.50 each) | `artifacts/radar-live/2026-09-01-fairness-evidence-150-pilot.md` §§1, 4–5 | PARTIAL | This is a proposed pilot price with fairness evidence. The same file says no price has been communicated, invoiced or collected. It must not be described as an authorised price. |
| Four-week delivery time | `VA_MONDAY_REVENUE_PACK.md` §11; `artifacts/radar-live/2026-09-01-draft-invoice-final.md` truthfulness notes | FAIL | This is a proposed cadence. The invoice states that no invoice is issued if no verified CQC data path exists at delivery time. No current run proves four successive weeks. |
| No renewal, no software, dashboard, login, API, provider contact data, predictions or commercial-result guarantee | `VA_MONDAY_REVENUE_PACK.md` §§1–3; `artifacts/radar-live/2026-09-01-buyer-email-draft-stripe.md` | PASS | These are stated exclusions and remain in the corrected offer. |
| Available sample proves the offer | `artifacts/radar-live/2026-08-04-fresh-weekly-digest-gloucestershire.md`; `artifacts/radar-sample/2026-08-22-dated-sample-digest.md`; `artifacts/launch-samples/bsol-domiciliary-sample/README.md` | FAIL | There are three different artefacts: a dated February format sample, a 4 August Gloucestershire digest, and an unverified Birmingham/Solihull pre-test sample. None proves a current buyer-specific four-week service. |
| £795 Territory Opportunity Brief is another price for the same product | `docs/CAREGIST_MASTER_STRATEGY.md` §5; `artifacts/launch-samples/bsol-domiciliary-sample/README.md`; `deploy/stripe-price-manifest.json` | FAIL | The master strategy calls Opportunity Briefs delivery templates, not independent products. The £795 material is an unverified pre-test kit and its Stripe manifest entry is `pending_creation` / `payment-link-pending`. It must not appear as an alternative price. |

## Selling-today issues only

1. **No deliverable current source run.** The only fresh-digest evidence is a dated 4 August edition. The proposed invoice forbids billing when a verified CQC data path cannot produce the digest. No evidence shows four current weekly runs for a buyer's selected region.
2. **No authorised commercial route.** The £150 price has fairness evidence, but the current invoice, buyer email and ask-to-pay script are explicitly draft-only. VAT, buyer confirmation, invoice fields and a founder-created verified payment link remain open.
3. **Deliverable detail is unproven.** The available fresh sample does not establish item-level source links, CQC references, service types or explanatory notes for every item. Do not sell those as included until a first deliverable proves them.
4. **Sample is not buyer-ready.** The February format sample is internal and stale. The Birmingham/Solihull sample is unverified pre-test material. The August Gloucestershire digest is dated and not a buyer-specific current sample.
5. **No approved route to a named buyer.** A specific buyer and lawful contact route must be confirmed before external use.

## Files changed

- `artifacts/sales/2026-09-08-caregist-radar-pilot-one-page-offer.md` — corrected event language, delivery status, sample scope and £795 separation.
- `artifacts/sales/2026-09-08-luna-offer-claim-evidence-review.md` — this review.

## Checks performed and results

- Inspected the authoritative strategy, pilot pack, price evidence, invoice/buyer drafts, all three available sample types and the Stripe manifest.
- Compared every buyer-facing deliverable and price in the Luna offer to an on-disk source.
- `git diff --check` passed.

## Exact next action

Produce and independently check one current, buyer-region digest that includes every intended buyer deliverable. Then obtain recorded founder approval for the final scope, £150 price, VAT treatment, named buyer and payment route. Until then, do not sell or send the offer.

**COMPLETE: no escalation needed.**
