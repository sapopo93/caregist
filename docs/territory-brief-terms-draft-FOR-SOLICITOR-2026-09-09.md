# Territory Opportunity Brief — instant self-serve supply

## DRAFT FOR SOLICITOR REVIEW — NOT APPROVED, NOT IN FORCE

Prepared 2026-09-09 for review by the solicitor who approved Business Terms
v2.0 / v2.1. Nothing here is legal advice. Do **not** set
`TERRITORY_BRIEF_TERMS_VERSION` / `_SHA256` / `_CONSENT_SHA256` or enable
`TERRITORY_SELF_SERVE_CHECKOUT_ENABLED` until the solicitor returns approved
wording and a version string.

---

## 1. What is changing and why

Business Terms **v2.1** (in force 9 Sep 2026) describe the Territory Opportunity
Brief as a **bespoke, human-mediated, cancellable, 3-working-day** service:

> "CareGist confirms the scope and the relevant source path **before it sends a
> payment link or accepts payment**." … "The buyer may **cancel by email before
> work begins and receive a full refund**." … "The delivery target … is **three
> working days** after … the written scope confirmation".

The product is moving to **instant self-serve**: the buyer selects the territory
themselves on the website, pays £745 through Stripe Checkout, and the completed
Brief (PDF + CSV) is generated automatically and made available to download
within seconds — no prior scope confirmation, no work-in-progress window.

That is the **opposite** of the v2.1 model, so three things need approved
replacement wording:

1. the **product description** (Terms §1);
2. the **fees / cancellation** paragraph (Terms §6);
3. the **delivery target** paragraph (Terms §7);

and one new thing needs approving:

4. the **express immediate-supply consent** shown as a required checkbox at
   checkout (stored in code as `TERRITORY_BRIEF_CONSENT_TEXT`; its SHA-256 is
   pinned in config and re-verified at fulfilment).

---

## 2. Open question for the solicitor (affects all wording below)

**Is the Territory Opportunity Brief sold only to businesses, or also to
consumers?**

- The Consumer Contracts Regulations 2013 cancellation right (and the reg. 37 /
  reg. 28(1)(b) "lose the right to cancel once fully performed / digital content
  supplied" mechanism) applies to **consumers**, not business buyers.
- v2.1 already offers a **contractual** cancel-by-email refund regardless, and
  the current placeholder consent text is written in consumer-regime language.
- If the answer is "business only", the consent checkbox can be simplified to a
  plain acknowledgement that the Brief is supplied immediately and the £745 fee
  is non-refundable once the download is made available (no statutory-right
  waiver needed). If "consumers too", the waiver wording matters.

Everything below is drafted the **cautious** way (assumes a consumer might buy,
keeps the express reg. 37 waiver). The solicitor may cut it back.

---

## 3. Draft — Terms §1 (Products and scope)

**Replace** the current Territory Opportunity Brief bullet with:

> **Territory Opportunity Brief:** a one-off research pack for an England
> territory (a local authority or region) that the buyer selects at checkout. It
> is generated automatically from CareGist's processed copy of CQC public
> information at the time of purchase and is made available to download
> immediately after payment. It contains a ranked shortlist of 25 to 50
> organisations with an evidence-based reason for each, a CRM-ready CSV, a short
> executive brief, and source links and observation dates for the public CQC
> information used. The territory selected at checkout is the scope of the
> purchase; there is no separate scope-confirmation step.

**Delete** from §1 the sentence:

> "For a Territory Opportunity Brief, the written scope confirmation identifies
> the territory, buyer criteria and factual selection criteria. It is the order
> form for that purchase…"

(replace with, if the solicitor wants an order-form anchor:)

> "For a Territory Opportunity Brief, the territory and options selected in the
> CareGist checkout, together with the order confirmation issued by Stripe, are
> the order for that purchase and prevail where they differ from a general
> statement on this site."

---

## 4. Draft — Terms §6 (Fees, subscription and cancellation)

**Replace** the Territory Opportunity Brief paragraph with:

> The Territory Opportunity Brief costs **£745** (excluding VAT). The buyer
> selects the territory at checkout and pays in full through Stripe before the
> Brief is generated. Because the Brief is produced and supplied to the buyer
> immediately, the buyer is asked at checkout to expressly request that
> immediate supply and to acknowledge that, once the completed Brief has been
> made available to download, any right the buyer would otherwise have to cancel
> and receive a refund is lost. After that point the £745 fee is non-refundable,
> except where the Brief is not delivered, is faulty, or is materially not as
> described, or where a refund cannot lawfully be excluded. If automated
> generation fails after payment, CareGist will retry and, if it still cannot
> deliver the Brief for the selected territory, will refund the fee in full. No
> refund is due because the buyer selected the wrong territory or is
> dissatisfied with which organisations the public data caused to be shortlisted.

---

## 5. Draft — Terms §7 (Availability and delivery targets)

**Replace** the "three working days" paragraph with:

> A Territory Opportunity Brief is generated and made available to download
> immediately after Stripe confirms payment; delivery is normally within a few
> minutes. This is a target, not a guaranteed service level. If automated
> generation does not succeed, CareGist will retry and, failing that, refund the
> fee under section 6. Upstream CQC unavailability, delay, correction, or schema
> change can affect what a Brief contains and when it can be produced.

(The existing final sentence — "CareGist may pause a collector, signal type,
explanation, outbound delivery, or checkout…" — stays.)

---

## 6. Draft — express immediate-supply consent (checkout checkbox)

This is the exact string that must be approved. It becomes
`TERRITORY_BRIEF_CONSENT_TEXT` in
`api/services/territory_brief_fulfilment.py`; its SHA-256 goes in
`TERRITORY_BRIEF_CONSENT_SHA256`. Stripe shows it next to a **required**
"I agree" checkbox; fulfilment refuses to deliver unless Stripe records the
acceptance and the hash matches.

### Option A — cautious / consumer-safe (recommended pending §2 answer)

> I expressly request that CareGist generate and supply my Territory Opportunity
> Brief immediately, before the end of any statutory cancellation period. I
> understand and agree that once the completed Brief has been made available for
> me to download I will lose any right I would otherwise have to cancel this
> purchase for a refund. This does not affect my rights if the Brief is not
> delivered, is faulty, or is not as described. I agree to the CareGist Business
> Terms of Service.

### Option B — business-buyer / plain

> I confirm I am buying for business purposes. I request immediate generation
> and supply of my Territory Opportunity Brief and acknowledge that the £745 fee
> is non-refundable once the completed Brief has been made available for me to
> download, except where it is not delivered, is faulty, or is not as described.
> I agree to the CareGist Business Terms of Service.

---

## 7. After the solicitor approves

1. Publish the updated Terms page; note the new **version string** (e.g.
   `2.2` / a dated identifier) and compute the SHA-256 of the approved Terms
   text → `TERRITORY_BRIEF_TERMS_VERSION`, `TERRITORY_BRIEF_TERMS_SHA256`.
2. Paste the **exact** approved consent string into
   `api/services/territory_brief_fulfilment.py::TERRITORY_BRIEF_CONSENT_TEXT`
   (byte-for-byte — trailing spaces and punctuation matter), and set
   `TERRITORY_BRIEF_CONSENT_SHA256` to `sha256(that string)`.
3. `Settings.validate_production()` then stops hard-failing on the territory
   block; `create_territory_brief_checkout` stops returning 503 for "awaiting
   approved Business Terms and consent wording".
4. This is still not enough to enable — see the checklist in
   `docs/territory-brief-instant-delivery-2026-09-09.md` §6 (Stripe test webhook
   endpoint, Blob token, migration 060, Postgres generation source, E2E run).
