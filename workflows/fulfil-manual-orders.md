# Fulfil a manual order (Territory Brief £745, Weekly Digest pilot £150)

Both products are sold human-led under Business Terms v2.2: scope agreed in
writing, then a Stripe Payment Link sent by hand. Nothing is delivered
automatically. Self-serve checkout stays closed.

## Quick path: `tools/prepare_order.py`

Each step is one command. It builds the deliverable for exactly the scope the
buyer's coverage check counted (same directory query as the website), runs the
checks below, and saves the email as a **draft in outreach@caregist.co.uk**. It
never sends: open Drafts in Private Email, review, press Send. A failed check
prints `NOT READY` with the reason and drafts nothing.

Quotes never attach the product: the confirmation email carries only the scope,
count, price and payment link. `deliver` refuses until the buyer has paid: it
looks for a paid sale of the right amount (£745 Brief, £150 Digest) for the
buyer's email in CareGist's sales record (`manual_sale_paid`), falling back to
Stripe read-only, and drafts nothing otherwise. Use the email the buyer paid with.

Checks: CQC export ≤ 8 days old; the scope has locations; the shortlist is not
empty (Terms v2.2.1 promise up to 50 organisations, and the quote states the
exact number, which is binding); every shortlisted entry has dated CQC evidence;
the evidence window is current. At delivery the Brief must contain at least the
number quoted for the same order ref; if a data refresh reduced it, the command
stops so you can agree the change with the buyer first.

Copy the values from the enquiry email (Region, Buyer type, Service type,
Providers in scope). Buyer types map to `--provider-group`: New registrations
`new_90`, Inadequate providers `inadequate`, Requires Improvement
`requires_improvement`, Not yet inspected `not_yet_inspected`, Stale inspections
`stale_inspection`.

```bash
# Brief, after agreeing scope: confirmation + £745 link (keep the printed order ref)
.venv/bin/python -m tools.prepare_order brief quote --region "North East" \
  --provider-group not_yet_inspected --service-type "Homecare Agencies" \
  --expected-count 1221 --buyer-email buyer@example.com --buyer-name "Sam" --company "Example Ltd"

# Brief, after payment: rebuild, check, delivery draft with PDF, CSV and manifest
.venv/bin/python -m tools.prepare_order brief deliver --order-ref TOB-... \
  --region "North East" --provider-group not_yet_inspected --service-type "Homecare Agencies" \
  --buyer-email buyer@example.com --buyer-name "Sam"

# Weekly Digest: confirmation + £150 link, then one delivery per week
.venv/bin/python -m tools.prepare_order digest quote --region "North West" \
  --start-date 2026-10-26 --buyer-type "Recruiter" --buyer-email buyer@example.com
.venv/bin/python -m tools.prepare_order digest deliver --order-ref WDP-... --region "North West" \
  --week-ending 2026-10-25 --issue 1 --buyer-email buyer@example.com
```

Drafts need `OUTREACH_IMAP_PASSWORD` (the outreach@ mailbox password) in `.env`;
add it yourself. Without it the command still writes `email.eml` in the order
folder (`.tmp/orders/<ref>/`) for you to open. The sections below describe the
same steps by hand.

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
