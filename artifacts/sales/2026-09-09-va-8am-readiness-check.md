# £795 Territory Opportunity Brief: VA 8am readiness check

Checked: 9 September 2026. Scope: readiness to offer, accept payment for and fulfil a new £795 Brief.

| Check | Result | Evidence | What blocks release |
|---|---|---|---|
| Buyer territory and selection criteria recorded | FAIL | The Birmingham and Solihull pack explicitly says its homecare staffing criteria are illustrative. No named buyer or agreed criteria are recorded. | Obtain one buyer's territory, care-service scope, exclusions and account-selection question. |
| Source supports the proposed buyer scope | PARTIAL | `verify_pack.py` passes for the retained Birmingham/Solihull prototype: 353 locations, 329 providers, 25 shortlisted organisations, two hashed CQC source editions and 25 page checks. The source edition is 1 September 2026 and was retrieved on 8 September. | Re-run the source check for the buyer's agreed territory and criteria. Do not treat the prototype as a current buyer delivery. |
| Specific delivery date confirmed by delivery owner | FAIL | The documented target is three working days, but no buyer start date, delivery date or delivery owner confirmation is recorded. | Record the named delivery owner, start date and promised delivery date after the scope check. |
| Customer terms and cancellation/refund wording fit the one-off Brief | FAIL | `frontend/app/terms/page.tsx` contains general business terms, says no new static dataset product is offered under its current catalogue, and has no Territory Opportunity Brief scope or one-off cancellation/refund wording. | Approve a brief-specific order description and cancellation/refund wording, or amend the terms before use. |
| £795 Stripe link works with the correct product and price | PARTIAL | Buyer-view check of `https://buy.stripe.com/bJe4gs4L5ed26vQ0nd3AY02` on 9 September showed `CareGist Territory Opportunity Brief`, £795.00 and no quantity selector. It uses live Product `prod_VE1CdaKNxE0yVP` and Price `price_1UDZAQ4mijLHzRRkvwXjtaQK`, supplied by the founder. Payment and post-payment behaviour were not attempted. | Independently complete a permitted test transaction before relying on post-payment confirmation, receipt and fulfilment handoff. |
| VAT status and customer wording confirmed | PARTIAL | The user confirmed CareGist is not currently VAT-registered. The buyer-view checkout showed no tax line, but its visible description does not state the VAT position. | Add “CareGist is not currently VAT-registered. No VAT is charged.” to the product description, then re-check the buyer page. |
| CareGist policy links appear at checkout | FAIL | Buyer-view check found checkout Terms and Privacy links pointing to Stripe legal pages. It did not expose CareGist policy links or a CareGist Terms acceptance control. | First amend Terms for the one-off Brief. Then configure CareGist Terms and Privacy URLs in Stripe public details, enable Terms acceptance where available, and re-check checkout. |

## Result

**NOT READY TO TAKE PAYMENT OR PRESENT AS AN ACCEPTED ORDER.**

The underlying local prototype is complete and its files pass integrity checks. The live link proves the buyer can reach the correct £795 checkout. Commercial release remains blocked by buyer scope and delivery-date confirmation, one-off Terms and policy links, VAT wording, and an independently checked paid/post-payment journey. A payment link by itself does not close them.

## Local buyer simulation completed

- Supported synthetic buyer: a Birmingham/Solihull domiciliary-care homecare staffing supplier using the two retained selection routes. Result: **local fulfilment PASS**. Intake, scope gate, 25 of 25 shortlist records, four hashed delivery files and the four-page executive PDF passed. It remains **order-ready false** because Stripe and Terms are blocked.
- Unsupported synthetic buyer: a compliance consultancy requesting breach history and director links. Result: **REJECTED**. Those inputs are outside the retained £795 evidence pack. This is the correct result, because generating a generic staffing shortlist for that buyer would be misleading.

Simulation outputs: `artifacts/product-polish/buyer-simulations/supported-result.json` and `artifacts/product-polish/buyer-simulations/unsupported-result.json`.

## What the VA may do at 8am

- Use the £795 Brief description and retained sample to prepare prospect records.
- Book or request a 15-minute scoping conversation.
- Capture the seven qualification answers in `2026-09-09-va-8am-brief-launch-pack.md`.

The VA must not state that an order is accepted, promise a delivery date, send a payment link or offer £495/£150 until this check is updated to PASS.

## Exact next action

Choose the first £795 buyer and record their territory, service scope, exclusions and selection question. That is the smallest missing input. It turns the local prototype into a proposed buyer-specific Brief, after which the source check and delivery date can be confirmed.

## Source references

- Product bundle verification: `artifacts/launch-samples/bsol-domiciliary-fresh-2026-09-08/verify_pack.py`
- Delivery-file manifest: `artifacts/product-polish/brief-preview/delivery-manifest.json`
- Product terms: `frontend/app/terms/page.tsx`
- Stripe preparation manifest: `deploy/stripe-price-manifest.json`
- Recorded product scope: `artifacts/sales/2026-09-08-defensible-territory-offer.md`
