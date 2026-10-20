# Fulfil a manual order (Territory Brief £745, Weekly Digest pilot £150)

Both products are sold human-led under Business Terms v2.2: scope agreed in
writing, then a Stripe Payment Link sent by hand. Nothing is delivered
automatically. Self-serve checkout stays closed.

## Quick path (run from ~/CareGist-orders)

Three commands run the whole business. Every rule below is enforced by the
tools, so a step done wrongly is refused with a plain reason, never half-done.

```bash
# 1. After agreeing scope by email: build, check, and draft the quote (no files attached)
.venv/bin/python -m tools.prepare_order quote brief --region "North East" \
  --provider-group not_yet_inspected --service-type "Homecare Agencies" \
  --buyer-email buyer@example.com --buyer-name "Sam" --company "Example Ltd"
.venv/bin/python -m tools.prepare_order quote digest --region "North West" \
  --start-date 2026-10-26 --buyer-type "Recruiter" --buyer-email buyer@example.com

# 2. See everything, and what to do next (copy the command it shows)
.venv/bin/python -m tools.orders            # add --report to write orders/reports/*.md and .csv

# 3. After payment: the order ref is the only input
.venv/bin/python -m tools.prepare_order deliver --order-ref TOB-20261020-152156-D3F0
```

Buyer types from the enquiry map to `--provider-group`: New registrations
`new_90`, Inadequate providers `inadequate`, Requires Improvement
`requires_improvement`, Not yet inspected `not_yet_inspected`, Stale inspections
`stale_inspection`.

### What the tools guarantee

- **Right order:** `deliver` takes only `--order-ref`; buyer, scope and the
  quoted count come from the order record (typing any of them is refused).
  Every subject ends with `(ref …)`; check To and ref, then press Send.
- **Paid first:** `deliver` needs a paid sale of the right amount (£745 / £150)
  from that buyer, made after the order existed. One Stripe payment can belong
  to one order only.
- **No duplicates:** a second open order for the same buyer and product needs
  `--order-ref` (change it) or `--new-order` (genuinely separate). An unsent
  draft is never duplicated; `--redraft` replaces it only if you deleted it,
  and never after the email was sent. A paid order's scope cannot change.
- **Digest issues:** the next issue number and its week are worked out from
  the start date; an issue cannot be prepared before its day, and never twice.
- **Nothing missed:** `tools.orders` lists ACTION NEEDED: quotes not sent,
  paid orders to deliver (due 3 working days after payment, OVERDUE after),
  digest issues due, drafts waiting for Send, quotes to follow up after 7 days,
  and any **payment with no order**.
- **Counts and report:** totals (orders, quoted not paid, paid and revenue,
  delivered in full, outstanding, overdue) and `--report` sections Bought /
  Not bought yet / Delivered in full, plus a CSV of every order.

The ledger is `orders/ledger.sqlite` (buyer emails; git-ignored; back it up).
Drafts reach outreach@ only with `OUTREACH_IMAP_PASSWORD` in `.env`; without it,
open `email.eml` from the order folder. "Sent" status also needs it.

## 0. Before the first sale, and every Monday

Keep a CQC API export no older than 8 days (the source-freshness promise). A
full run makes ~94,000 CQC API calls and takes about 2 hours with 6 workers.

```bash
mkdir -p .tmp/cqc-export-$(date +%Y%m%d)
set -a; . ./.env; set +a
.venv/bin/python extract_cqc.py --output-dir .tmp/cqc-export-$(date +%Y%m%d) --detail-workers 6 --sleep 0.1
```

Note the time the run finished: it is the `--source-retrieved-at` evidence.
Check `failed_ids.txt` in the output directory is empty or tiny before use. The
run resumes from `checkpoint.json` with `--resume` if interrupted.

## 1. Agree scope, then send the link

| | Territory Brief | Weekly Digest pilot |
|---|---|---|
| Written confirmation must state | territory (local authority or region), window days, shortlist size, delivery within ~3 working days | England region, buyer type, first delivery weekday |
| Payment Link | `https://buy.stripe.com/bJe8wI7Xhd8YdYi2vl3AY04` (£745) | `https://buy.stripe.com/3cI8wIfpJ4Csg6qfi73AY01` (£150) |

For a Brief, generate it **before** sending the link (the quote step does this)
and state the exact shortlist size in the confirmation; the Brief promises up to
50 organisations. Unless the buyer narrowed the service type, it covers every
CQC-registered service type (GP, dental and healthcare as well as social care);
agree that with the buyer.

The written confirmation is the order form under v2.2. Keep it in the email
thread with the buyer.

## 2. When payment arrives

Stripe emails the account owner. If the CareGist webhook is enabled, the sale is
also recorded as `analytics_events.event_type = 'manual_sale_paid'` with the
buyer email, amount and checkout session ID. It grants nothing and never
retries. Match the payment to the email thread by buyer email and amount.

## 3a. Deliver a Territory Brief

```bash
EXPORT=.tmp/cqc-export-YYYYMMDD
.venv/bin/python -m tools.generate_territory_opportunity_brief \
  --kind local_authority --name "Birmingham" --window-days 90 --shortlist 30 \
  --locations-source $EXPORT/_locations_detail.ndjson \
  --providers-source $EXPORT/_providers_detail.ndjson \
  --order-reference "<Stripe checkout session ID>" \
  --generated-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --out-dir .tmp/briefs/<buyer>
```

Run it as a module (`-m`); running the file directly fails with `No module
named 'api'`. The window ends on the newest CQC date in the export, so a partial
or stale export silently shifts it: check the printed `window` ends within a few
days of today and `considered` is not 0 before sending.

Open the PDF and CSV, check the territory, shortlist count and dates, then email
both files and the source manifest to the buyer. Record the delivery date in the
thread.

## 3b. Deliver a Weekly Digest (four issues)

Run once a week on the agreed weekday, after a fresh export (step 0) that
finished after the window's last day:

```bash
EXPORT=.tmp/cqc-export-YYYYMMDD
DATABASE_URL=... .venv/bin/python -m tools.build_weekly_digest_pilot \
  --region "North West" --week-ending YYYY-MM-DD --issue 1 \
  --customer "<buyer>" \
  --locations-source $EXPORT/_locations_detail.ndjson \
  --source-retrieved-at "<export finish time, ISO with timezone>" \
  --out-dir .tmp/digests/<buyer>
```

New registrations come from production (read-only). Newly published ratings come
from the export's `currentRatings` report dates. As of 20 Oct 2026 CQC had
published only 3 rating reports nationally since 1 Sep, so expect the ratings
section to be empty or near-empty until CQC resumes; say so when agreeing the
region. A region typically has a handful of new registrations a week (North West:
4 in the week to 19 Oct). The tool refuses an export retrieved on or before the window's last day.
Email the PDF and CSV. Issues 2–4 repeat with the next week-ending date and a
fresh export.

## 4. Refunds and missed deliveries

Follow v2.2: full refund before the first digest; a proportional one-quarter
refund or late delivery for a missed digest; refund through the Stripe
dashboard.

## Stripe state (2026-10-20, set with founder approval)

- Active Payment Links: £745 Brief (`bJe8wI…04`) and £150 Weekly Digest
  (`3cI8wI…01`, checkout shows "CareGist Weekly Digest pilot — 4 weekly
  digests"). The £895 combined link is deactivated.
- The CareGist webhook (`/api/v1/billing/webhook`) is enabled; each sale is
  recorded as `manual_sale_paid`. Confirm the first real sale appears there; if
  it does not, the production `STRIPE_WEBHOOK_SECRET` does not match the
  endpoint's signing secret.
- The `tenderriskassurance.co.uk` webhook on the same Stripe account is
  disabled, so CareGist buyers' details no longer go to it. That site no longer
  receives payment events from this account.
