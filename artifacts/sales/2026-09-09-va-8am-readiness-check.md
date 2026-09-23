# £745 Territory Opportunity Brief: VA 8am readiness check

Checked: 9 September 2026. **Two rows re-checked against `main` on 23 September 2026
and corrected below — they were stale and both read as "do not sell" when the
underlying blocker had already been cleared.** Everything not marked
`RE-CHECKED 23 Sep` is still the 9 September finding and has NOT been re-verified.

Scope: readiness to offer, accept payment for and fulfil a new £745 Brief.

**Read this first.** The rows below mix two different things. Some are *per-deal
steps the VA performs on every order* (recording the buyer's territory and
criteria, confirming a delivery date). Those are never "done" in advance — they
are the job. Others are *structural blockers only the founder can clear*
(Stripe policy links, an independently checked paid journey). Do not read a
per-deal FAIL as "the product cannot be sold"; read it as "not yet done for
this buyer".

| Check | Result | Evidence | What blocks release |
|---|---|---|---|
| Buyer territory and selection criteria recorded | FAIL | The Birmingham and Solihull pack explicitly says its homecare staffing criteria are illustrative. No named buyer or agreed criteria are recorded. | Obtain one buyer's territory, care-service scope, exclusions and account-selection question. |
| Source supports the proposed buyer scope | PARTIAL | `verify_pack.py` passes for the retained Birmingham/Solihull prototype: 353 locations, 329 providers, 25 shortlisted organisations, two hashed CQC source editions and 25 page checks. The source edition is 1 September 2026 and was retrieved on 8 September. | Re-run the source check for the buyer's agreed territory and criteria. Do not treat the prototype as a current buyer delivery. |
| Specific delivery date confirmed by delivery owner | FAIL | The documented target is three working days, but no buyer start date, delivery date or delivery owner confirmation is recorded. | Record the named delivery owner, start date and promised delivery date after the scope check. |
| Customer terms and cancellation/refund wording fit the one-off Brief | **PASS — RE-CHECKED 23 Sep** | `frontend/app/terms/page.tsx` on `main` now defines the Brief as "a one-off, buyer-specific research pack for an agreed England territory" with the 25–50 shortlist, CSV/Excel dataset and 3–5 page brief (section 2); states the £745 fee, payment due in full before work begins, **cancel by email before work begins for a full refund**, non-refundable once work has begun except where CareGist fails to deliver the agreed scope or a remedy cannot lawfully be excluded, and a revised delivery date or full refund if a post-payment source issue prevents the agreed scope (section 6); a three-working-day delivery target (section 7); and liability limited to the fee paid (section 11). | Nothing. This row was the 9 September state and is no longer accurate. |
| £745 Stripe link works with the correct product and price *(describes the RETIRED direct-checkout route — see the sales workflow; do not send a payment link before scope is agreed)* | PARTIAL | Buyer-view check of `https://buy.stripe.com/bJe4gs4L5ed26vQ0nd3AY02` on 9 September showed `CareGist Territory Opportunity Brief`, £745.00 and no quantity selector. It uses live Product `prod_VE1CdaKNxE0yVP` and Price `price_1UDZAQ4mijLHzRRkvwXjtaQK`, supplied by the founder. Payment and post-payment behaviour were not attempted. | Independently complete a permitted test transaction before relying on post-payment confirmation, receipt and fulfilment handoff. |
| VAT status and customer wording confirmed | **PASS — RE-CHECKED 23 Sep** | H-Kay Limited is not VAT registered. `/pricing/territory`, `/terms`, the offer page and all three VA packs now carry the identical shipped wording **"£745 fixed fee. No VAT added."** (merged as `56b38a2`). No surface anywhere still says "excludes VAT". | Nothing for the VA to say differently. Quote that wording verbatim. |
| CareGist policy links appear at checkout | FAIL | Buyer-view check found checkout Terms and Privacy links pointing to Stripe legal pages. It did not expose CareGist policy links or a CareGist Terms acceptance control. | First amend Terms for the one-off Brief. Then configure CareGist Terms and Privacy URLs in Stripe public details, enable Terms acceptance where available, and re-check checkout. |

## Result

**NOT READY TO TAKE PAYMENT OR PRESENT AS AN ACCEPTED ORDER** — this verdict is
unchanged and remains the founder's to revise, not an agent's.

What changed since 9 September: **Terms and VAT wording are no longer blockers.**
Both were cleared and re-verified against `main` on 23 September.

What still blocks taking payment, and who can clear it:

| Remaining blocker | Who clears it |
|---|---|
| CareGist policy links and Terms acceptance at checkout | Founder (Stripe dashboard config) |
| An independently checked paid / post-payment journey | Founder (a permitted test transaction) |
| Buyer territory, criteria and exclusions recorded | **VA, per deal** |
| Named delivery owner, start date and promised delivery date | **VA + delivery owner, per deal** |

The VA can do everything up to and including agreeing scope in writing and
quoting the £745 price. The VA must not send a payment link or state that an
order is accepted until the founder has cleared the two rows above.

## Local buyer simulation completed

- Supported synthetic buyer: a Birmingham/Solihull domiciliary-care homecare staffing supplier using the two retained selection routes. Result: **local fulfilment PASS**. Intake, scope gate, 25 of 25 shortlist records, four hashed delivery files and the four-page executive PDF passed. It remains **order-ready false** because Stripe and Terms are blocked.
- Unsupported synthetic buyer: a compliance consultancy requesting breach history and director links. Result: **REJECTED**. Those inputs are outside the retained £745 evidence pack. This is the correct result, because generating a generic staffing shortlist for that buyer would be misleading.

Simulation outputs: `artifacts/product-polish/buyer-simulations/supported-result.json` and `artifacts/product-polish/buyer-simulations/unsupported-result.json`.

## What the VA may do at 8am

- Use the £745 Brief description and retained sample to prepare prospect records.
- Book or request a 15-minute scoping conversation.
- Capture the seven qualification answers in `2026-09-09-va-8am-brief-launch-pack.md`.

The VA must not state that an order is accepted, promise a delivery date, send a payment link or offer £495/£150 until this check is updated to PASS.

## Exact next action

Choose the first £745 buyer and record their territory, service scope, exclusions and selection question. That is the smallest missing input. It turns the local prototype into a proposed buyer-specific Brief, after which the source check and delivery date can be confirmed.

## Source references

- Product bundle verification: `artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/verify_pack.py`
- Delivery-file manifest: `artifacts/product-polish/brief-preview/delivery-manifest.json`
- Product terms: `frontend/app/terms/page.tsx`
- Stripe preparation manifest: `deploy/stripe-price-manifest.json`
- Recorded product scope: `artifacts/sales/2026-09-08-defensible-territory-offer.md`
