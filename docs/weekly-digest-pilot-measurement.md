# Weekly Digest pilot measurement

This is a four-week, one-off £150 pilot. It is a measurement plan, not a new
recurring product or an approval to open checkout.

## Delivery hypothesis

- Send one digest each week for one buyer-selected England region.
- Include only verified, observation-dated CQC register movement with an
  official source link.
- Do not imply that a registration, rating movement, or inspection report
  proves supplier need or buying intent.
- Do not send daily updates by default.
- Treat immediate event alerts as a separate hypothesis. They require a
  verified material event, a matching location ID, and explicit buyer opt-in.

## Record for every pilot

Capture the following for each of the four weeks:

- digest sent date and source edition date;
- number of candidate events, included events, and held-for-review events;
- source URL, location ID, event type, effective date, and evidence status for
  every included event;
- whether the buyer opened, saved, forwarded, or acted on an item;
- providers or locations the buyer contacted after seeing the digest;
- buyer-reported time saved, usefulness, false positives, and missing signals;
- whether the buyer asks for weekly, monthly, or event-triggered updates;
- explicit willingness to pay for the next defined package.

## Release gates

The digest remains internal or manually reviewed if any of these is true:

- the authoritative source refresh is incomplete or outside its freshness SLA;
- an event lacks a source URL, location ID, event type, effective date, or
  supporting detail;
- a rating change lacks comparable before-and-after evidence for the same
  location and category;
- the item is supported only by a new registration, low rating, or inspection
  issue and is worded as buyer intent;
- the item has unresolved conflicting evidence;
- a delivery copy has not been reopened and checked.

## Decision after week four

Do not convert the pilot into a subscription based on opens alone. Continue
only if buyers report a concrete workflow change, at least one qualified action
is attributable to the digest, and the buyer accepts the proposed price and
cadence. A recurring offer needs a new founder decision and fresh checkout and
fulfilment evidence.

## Current status

`research_only=true`, `approved_delivery=false`, and `checkoutReady=false` remain
the safe defaults until the external collection, payment, fulfilment, and
delivery gates have independently passed.
