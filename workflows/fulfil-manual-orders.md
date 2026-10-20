# Fulfil a manual order (Territory Brief £745, Weekly Digest pilot £150)

Both products are sold human-led under Business Terms v2.2: scope agreed in
writing, then a Stripe Payment Link sent by hand. Nothing is delivered
automatically. Self-serve checkout stays closed.

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
from the export, because production's rating-publication data stopped on 20 Sep
2026. The tool refuses an export retrieved on or before the window's last day.
Email the PDF and CSV. Issues 2–4 repeat with the next week-ending date and a
fresh export.

## 4. Refunds and missed deliveries

Follow v2.2: full refund before the first digest; a proportional one-quarter
refund or late delivery for a missed digest; refund through the Stripe
dashboard.

## Known constraints (2026-10-20)

- The CareGist Stripe webhook endpoint is disabled. Re-enable it only after the
  `manual_sale_paid` change is deployed, or each Payment Link sale errors and
  retries.
- `tenderriskassurance.co.uk/api/webhooks` on the same Stripe account also
  receives every `checkout.session.completed`, including CareGist buyers'
  details. Filter or remove it.
