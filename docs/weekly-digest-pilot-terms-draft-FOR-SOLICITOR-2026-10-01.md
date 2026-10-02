# Weekly Digest pilot: draft terms, FOR SOLICITOR REVIEW

**Status: DRAFT. Not approved, not published, not legal advice.** Prepared 1 October 2026.
Nothing in `frontend/app/terms/page.tsx` has been changed. Gate 0 (solicitor or founder approval of Terms) applies before any of this goes live.

## Why this exists

The public site sells the Weekly Digest (£150, four weekly digests) on `/pricing`, but Business Terms v2.1
(in force 9 September 2026) contain no Digest wording. Section 1 lists no Digest product, section 6 covers
fees and refunds for the Brief only, and section 7 gives a delivery target for the Brief only. A buyer who
pays £150 today is paying with no stated scope, refund, delivery or remedy terms.

## Insertion 1: section 1 (Products and scope), new bullet after the Territory Opportunity Brief bullet

> **Weekly Digest pilot:** a one-off pilot of four weekly digests for one agreed England region. Each digest
> reports new registrations and newly published ratings in the agreed region, taken from CQC's published
> register, with the source edition date and the observation window stated. It is delivered by email and PDF.
> It is not a subscription, dashboard, API or alert service.

## Insertion 2: section 1, closing paragraph, new sentence

> For a Weekly Digest pilot, the written confirmation of region, buyer type and first delivery date is the
> order form for that purchase and prevails where it differs from a general statement on this site.

## Insertion 3: section 6 (Fees), new paragraph after the Territory Opportunity Brief paragraph

> The Weekly Digest pilot costs **£150** for four weekly digests. CareGist confirms the region, the start
> date and the source path before it sends an invoice or payment link. Payment is due in full before the
> first digest. The buyer may cancel by email before the first digest is sent and receive a full refund.
> After the first digest is sent, the fee for digests already delivered is non-refundable, except where
> CareGist fails to deliver an agreed digest. If CareGist does not deliver an agreed digest within the
> agreed week, it will deliver it late or refund £37.50 for that digest, at the buyer's choice. The pilot
> does not renew automatically and ends after the fourth digest.

## Insertion 4: section 7 (Availability and delivery targets), new paragraph

> The delivery target for each Weekly Digest is the agreed weekday of each of four consecutive weeks from
> the agreed start date. The target is not a guaranteed service level. A digest reflects the most recent CQC
> register edition CareGist has reconciled, which may be earlier than the delivery date. A digest is
> not a live feed, and it does not state or imply vacancies, budgets or buying intent.

## Decisions for the founder before this goes to the solicitor

1. **"Newly published ratings" vs "rating changes".** The site says "rating changes, and closures". The
   register edition carries only the latest rating and its publication date, so a change cannot be shown
   without comparable before-and-after evidence for the same location. This draft says "newly published
   ratings" and omits closures. Either the site copy moves to match, or you confirm the pipeline can
   evidence changes and closures and this wording widens.
2. **Item-level official link.** The site promises "a direct official-source link on every item". Earlier
   sample notes said item-level public CQC links were not proven. This draft does not repeat the promise.
   Decide whether to promise it, and test it first.
3. **£37.50 per-digest refund figure.** It is £150 divided by four. Confirm this is the remedy you want.
4. **Stale contradiction, not fixed here.** Terms v2.1 still lists Radar Regional, Radar National, Feed
   Pilot and Embedded Enterprise while `/pricing` says everything else is stopped. Removing them is a
   legal-text change for the same solicitor review.
5. **Version bump.** If approved, bump the version and in-force date in `frontend/app/terms/page.tsx`
   (currently "Version 2.1 · In force from 9 September 2026"), and record the approved text hash the way
   the Brief terms were handled.
6. **Payment mechanism.** The pilot is invoice-based (draft invoice CG-2026-001 has placeholder bank
   details). No Stripe link exists for it. This draft does not change that.
