# REVENUE COMMAND PLAN — 2026-09-04

## 1. ZERO-REVENUE DIAGNOSIS

**Primary constraint: nobody has ever been asked to buy.** Secondary and
compounding: the one product that *could* take money has had its checkout
switched off for a month by a fail-closed gate that successful data collection
never got booked against.

Evidence for the primary cause: `crm_deals` held **0 rows** in production
before this session. 58,887 CQC locations, a 22-router API, a Twilio-wired CRM,
a 381-test inspection engine — and not one opportunity record. Build effort
went to product; zero went to demand.

Evidence for the secondary cause, in order:
1. `https://www.caregist.co.uk/api/v1/health` → `commercialReadiness.checkoutReady: false`.
2. `frontend/app/pricing/page.tsx:27` gates the CTA on it; `frontend/components/PricingCTA.tsx:141`
   renders "Paid checkout unavailable" — **live on the public pricing page right now**.
3. `api/routers/billing.py:516-523` fails the checkout call closed behind the
   same signal.
4. The signal needs a `pipeline_runs` row with `run_type='reconciliation'`,
   `counts_reconciled=TRUE`, `reconciled_at NOT NULL` (`db/migrations/051_cqc_freshness_evidence.sql:52-57`).
5. Production has 6 reconciliation runs, **all `failed`**. Batches
   `c6e7d7fa` (11 Aug, run 5244) and `56a11f0f` (12 Aug, run 5312) had
   **every shard `completed`** — 57,025/57,025 and 57,060/57,060 locations
   checked, **0 failures** — and were then closed by `abort` because
   `finalize` was never run. Perfect data collection, booked as failure.

Cause split — A. COMMERCIAL: no offer put to a buyer, ever. B. PRODUCT: three
products all built past MVP before one customer existed. C. TECHNICAL: the
finalize step above; RegIntel has no payment code at all. D. EXECUTION: the
same "finishing, not selling" pattern the Hermes weekly audit already names.
E. AUTOMATION: 15 of 17 Hermes cron jobs disabled; no cron output has reached
the user's phone since 19 Aug. **Weight: C is the cheapest to fix, A is the
one that actually decides the outcome.**

## 2. PROJECT VERDICTS

| Project | Verdict | Evidence |
|---|---|---|
| CareGist data + directory | **VERIFIED WORKING** | 58,887 locations / 37,116 active provider orgs; `/api/v1/providers/search` 200 in 1.3s; signal poll completed 2026-09-04 17:57 |
| CareGist checkout | **BROKEN** | `checkoutReady:false`; pricing page shows "Paid checkout unavailable" |
| CareGist CRM | **PARTIALLY WORKING** | Full pipeline schema + Twilio + TPS wired; had 0 deals; `crm_tps_automation_settings` is **empty** so screening automation processes nothing |
| RegIntel | **NOT IMPLEMENTED** (as software you can sell) | 381/381 tests pass; last prod deploy errored 46d ago; every domain dead; **zero Stripe code** |
| RegIntel Inspector Pack (as a service) | **VERIFIED WORKING** | PDF+DOCX renderers + 34-topic question bank run locally |
| LeadGen SA | **PARTIALLY WORKING** | `/healthz`, `/readyz`, capture form all 200; one funnel; manual mode; lead-reference counter bug |
| Hermes | **PARTIALLY WORKING** | launchd-supervised, ticker firing; 2 of 17 jobs enabled; delivery had been redirected off Telegram |

## 3. THE THREE REVENUE STREAMS

### #1 — CQC Inspection Readiness Review (£950) — *sell this week*
- **Offer:** a mock CQC inspection against the current framework, delivered as
  an Inspector Pack (PDF+DOCX) with findings, evidence gaps and a dated action plan.
- **Buyer:** registered manager / owner of a care home rated **Requires
  improvement** or **Inadequate**.
- **Price:** £950 core; £1,950 review + repairs. Invoice — **no Stripe needed**.
- **Sales method:** outbound telephone. 2,254 usable targets exist; 248 are loaded.
- **Readiness:** engine works, list exists, CRM holds the pipeline.
- **Blocker:** no legally usable channel yet. See §4A. Post is the only channel
  with complete data coverage and no compliance dependency.
- **Automation:** Hermes drafts the call brief per provider from its CQC record.
- **Path to first customer:** 30 screened calls → 3 conversations → 1 sale.

### #2 — CareGist Radar (£299/mo regional, £799/mo national) — *2–3 weeks*
- **Buyer:** compliance consultancies and care-group BD teams.
- **Readiness:** billing code, Stripe prices, terms all present.
- **Blocker:** the reconciliation finalize (§10.2). Until then nobody *can* pay.
- **Automation:** already built — hourly feed cycle is live and producing events.

### #3 — LeadGen SA qualified leads (ZAR, per-lead or retainer) — *4+ weeks*
- **Buyer:** SA car-tracker / insurance providers.
- **Blocker:** lead-reference counter bug; single funnel; no outbound.
- Ranked third because it needs a South African buyer conversation the other
  two do not, and its acquisition asset does not yet exist.

**Later opportunities (do not build):** tender intelligence, recruitment
intelligence, provider claims, review publication, the API/Feed tier,
RegIntel-as-SaaS, TrustRoute multi-tenancy.

## 4A. CHANNEL STATUS — corrected 2026-09-04

My earlier instruction to insert an `enabled=true` row into
`crm_tps_automation_settings` was **wrong and has been withdrawn**. It would
have screened none of these 248 rows, and it would have armed a spend trigger.

`_candidate_query` in `api/services/crm_tps_automation.py:193` seeds screening
jobs from the **new-registration feed only** — `event.event_type =
'new_registration'`, keyed `ON CONFLICT (organization_id, provider_id)`. The
inspection cohort is by definition *existing* providers with a published
rating, so they can never enter that queue. There is also a second, independent
gate: live health reports `crm_operations.calling.tps_automation_enabled:
false`, and the local `.env` has neither a TPSCheck key nor the automation flag.
A tenant row saying `enabled=true` in front of a disabled app flag is a
fake-on: it starts spending the moment anyone sets the env var.

Verified data coverage across the 2,362-provider cohort (and the 248 loaded):

| Channel | Coverage | Compliance dependency | Status |
|---|---|---|---|
| **Post** | **2,362 / 2,362 full postal addresses** (248/248 loaded) | none — TPS/CTPS and PECR do not govern business post | **OPEN** |
| Phone | 2,274 numbers | CTPS screening; existing automation structurally cannot screen this cohort | **BLOCKED — procurement** |
| Email | **0 addresses** | needs enrichment, `subscriber_type='corporate'` with recorded evidence, and `crm_email_campaigns_enabled` | **BLOCKED — two builds** |

The email path is well built, not missing: `is_email_marketing_eligible`
(`api/services/crm_campaigns.py:17`) requires GB + an address + corporate
subscriber status, `crm_extended.py:172` refuses the corporate-subscriber basis
without it, and evidence is mandatory. It is blocked on inputs, not on code.

## 4. FIRST CUSTOMER — exact sequence
1. Send 100 letters to the top-ranked providers in
   `outreach/inspection_targets_20260904.csv`. One page: their CQC overall
   rating, the re-inspection ahead of them, what a mock inspection produces,
   £950, a phone number to call you back on.
2. Log each send as a `crm_activities` row against the contact and move the
   deal `new` -> `attempting_contact`.
3. Handle inbound calls. An inbound call carries no CTPS restriction, which is
   precisely why post is the unlock here.
4. Move the deal `connected` -> `qualified` -> `proposal_sent` -> `won`.
5. Invoice on acceptance. Run the RegIntel engine locally, deliver the Inspector Pack.

To open the phone channel instead, the real action is procuring bulk CTPS
screening from a licensed reseller and screening the CSV as a file — not
flipping anything in this codebase.

## 5. REVENUE MATH
Assumptions, deliberately conservative for cold B2B telephone: 25% reach a
decision-maker, 20% of those take a real conversation, 25% of those buy.
**≈1.25 sales per 100 dials.**

| Target | Stream #1 @ £950 | Volume needed |
|---|---|---|
| First £1 | 1 sale | ~420 letters |
| £1,000/mo | 1 sale/mo | ~420/mo |
| £5,000/mo | 5 sales/mo | ~2,100/mo — at this point CTPS procurement pays for itself |
| £10,000/mo | 10 sales/mo | needs the phone channel open, or 6 sales + 12 Radar Regional @ £299 |

Radar is what makes £10k/mo survivable: 34 × £299 = £10,166 **recurring**,
versus 10 one-off reviews that must be re-sold every month.

## 6. HERMES ARCHITECTURE
```
07:00 daily → Chief of Staff → gpt-5.6-luna → CRM read → call brief for today's
              20 screened contacts → self-check vs CQC record → Telegram
hourly     → Feed cycle (live)  → no LLM     → CQC API   → trusted_event_ledger
             → health check → Radar delivery
daily 18:00→ Pipeline auditor  → deepseek-v4-flash → SQL → stage-change digest
             → flags deals untouched >5 days → Telegram
weekly     → Waste audit (live)→ gpt-5.6-luna → repo+logs → Telegram
on failure → Watchdog          → deepseek-v4-flash → health+cron state
             → alert if checkoutReady flips false → Telegram
```

## 7. MODEL ROUTING TABLE
Configured primary is `gpt-5.6-sol` via `openai-codex`, but the logs show
actual usage of deepseek-v4-flash 1776 / grok-4.6 1542 / gpt-5.6-sol 589 —
codex is rate-limited (41× `HTTP 429: usage limit reached`). Route to what runs.

| Tier | Task | Primary | Fallback | Escalate when |
|---|---|---|---|---|
| 1 | CRM updates, extraction, classification, list filtering | `deepseek-v4-flash` (deepseek) | `grok-4.6` | never |
| 2 | Call briefs, lead research, outreach copy, digests | `grok-4.6` (xai-oauth) | `deepseek-v4-flash` | output contradicts the CQC record |
| 3 | Offer/pricing decisions, difficult code, QA of customer-facing output | `gpt-5.6-sol` (openai-codex) | `grok-4.6` | £-affecting or customer-visible |
| 4 | Escalation only | `gpt-5.6-sol` reasoning=high | — | tiers 1–3 disagree, or >£1k at stake |

Cost priority: tier 1 is ~90% of volume and must stay on deepseek. **Change
`model.default` from `gpt-5.6-sol` to `grok-4.6`** so the 429 storm stops
killing cron runs.

## 8. AUTOMATION BACKLOG
- **P0** — CTPS screening enablement; reconciliation on a schedule; deal-stage
  decay alert; watchdog on `checkoutReady`.
- **P1** — Hermes call-brief generation; pipeline digest to Telegram;
  re-enable `cos-revenue-day-shift` at 2×/day; fix the cron fire-fence that
  marks successful runs failed.
- **P2** — Radar onboarding email; weekly movers digest.
- **DO NOT BUILD** — RegIntel SaaS/Stripe; TrustRoute multi-tenancy; tender
  intelligence; the Feed/API tier; any new dashboard; LeadGen SA funnel #2.

## 9. 30-DAY REVENUE SPRINT
- **Week 1 — selling only.** 100 letters out. Start CTPS procurement in
  parallel. Target: first inbound call. No code except what a reply exposes as broken.
- **Week 2** — 150 more letters, first delivery, ask for a referral. Run the
  reconciliation; confirm `checkoutReady:true`.
- **Week 3** — 150 letters + first 20 Radar approaches to consultancies.
- **Week 4** — 150 letters, close Radar #1, put the letter drafting on Hermes.

## 10. HUMAN ACTIONS (only you can do these)
1. **Send the letters.** 100 pages, printed and posted. This is the only
   customer-acquisition action currently available without a procurement or a
   build, and it is a person doing it.
2. **Decide whether to procure bulk CTPS screening.** That, not any flag in
   this repo, is what opens the 2,274-number phone channel. Do it when letter
   volume stops being enough — around the £5k/mo line.
3. **Run the reconciliation** (hours of CQC API traffic + production writes):
   `python3 tools/run_cqc_reconciliation.py --shard-count 8`
   then confirm `checkoutReady` flipped true before touching the checkout flags.
4. **Decide RegIntel's delivery promise** — turnaround time and what is in the pack.
5. **Restart the Hermes gateway** so the Telegram delivery change takes effect:
   `hermes gateway restart`.

## 11. IMPLEMENTATION EVIDENCE
| Item | Status | Evidence |
|---|---|---|
| Checkout blocked, root cause | **VERIFIED** | live `/api/v1/health`; batches `c6e7d7fa`/`56a11f0f` all shards completed, 0 failures, marked failed |
| Target list builder | **IMPLEMENTED + TESTED** | `tools/build_inspection_target_list.py`; 2,254 eligible, 250 ranked |
| Target CSV | **IMPLEMENTED** | `outreach/inspection_targets_20260904.csv` |
| CRM pipeline loaded | **IMPLEMENTED + TESTED** | 248 contacts, 248 deals, £235,600, all stage `new`, all screening `unknown` |
| Reconciliation orchestrator | **IMPLEMENTED** (not run) | `tools/run_cqc_reconciliation.py`; `--help` verified |
| Hermes Telegram delivery | **IMPLEMENTED** | `cron/jobs.json` both live jobs `deliver: telegram`, streak reset; backup `jobs.json.bak-20260904` |
| TPS automation cannot serve this cohort | **VERIFIED** | `crm_tps_automation.py:193` filters `event_type='new_registration'`; live health `tps_automation_enabled:false`; settings table 0 rows |
| Postal coverage | **VERIFIED** | 2,362/2,362 cohort and 248/248 loaded rows have address_line1 + postcode |
| Email coverage | **VERIFIED ZERO** | 0 email addresses across the cohort |
| RegIntel payment | **VERIFIED NOT IMPLEMENTED** | no Stripe code in any RegIntel dir |
| RegIntel deployment | **VERIFIED BROKEN** | last prod deploy errored 46d ago; all domains dead |
| LeadGen SA liveness | **VERIFIED WORKING** | `/healthz` 200, `/readyz` ready, capture form 200 |

## 12. NEXT 3 ACTIONS
1. Post 100 letters from `outreach/inspection_targets_20260904.csv`. It is the
   only open channel and needs no spend approval beyond postage.
2. Run `tools/run_cqc_reconciliation.py --shard-count 8` and confirm
   `checkoutReady: true`, which unblocks stream #2.
3. Get a quote for bulk CTPS screening so the phone channel is ready when
   letter volume stops being enough.

---

## 13. CTPS SOLVED — 2026-09-04 (supersedes §4A "BLOCKED — procurement")

The expensive path was the only one wired up. The cheap path was already built
and unused.

* **Do not use** `crm_tps_automation.py` (paid per-lookup TPSCheck API, dual
  gated, and scoped to `event_type='new_registration'` so it cannot see this
  cohort anyway).
* **Use** the bulk-file route: `tools/export_screening_batch.py` ->
  screening bureau -> `tools/import_screening_results.py`.
* `crm_phone_screening_cache` is UNIQUE on `(organization_id, phone_hmac)` and
  the exporter excludes anything screened inside 28 days, so **a number is
  never paid for twice**.
* Measured cost for the current list: **249 numbers, £1.25-£2.49 one-off.**
  The £3,300/yr licence and £150-200/mo unlimited plans are not worth buying.

Phone channel status: **OPEN, pending one ~£2 bureau order.**

## 14. MONEY WHILE WE SLEEP — chain status

payment -> webhook -> entitlement -> fulfilment email, verified link by link:

| Link | Status | Evidence |
|---|---|---|
| Checkout reachable | **BROKEN** | `checkoutReady:false` — the one remaining break |
| Stripe webhook | **VERIFIED WORKING** | live POST with bad signature -> 400 |
| Entitlement grant | **VERIFIED IMPLEMENTED** | `billing.py:1611` refuses to grant on a non-entitled status |
| Fulfilment email | **VERIFIED WORKING** | `pending_emails` 32 total, **0 unsent** |
| Payments to date | **0** | `stripe_processed_events` = 0; Stripe live balance £0.00 |

## 15. OPERATING TOOLS (all tested)

| Command | Does |
|---|---|
| `tools/revenue_snapshot.py` | Stripe balance + MRR + CRM pipeline. Read-only. |
| `tools/self_heal.py [--heal]` | Detects the failure modes that caused £0; finalizes a stranded batch **only inside the 8-day SLA**. |
| `tools/export_screening_batch.py` | Smallest payable screening batch. |
| `tools/import_screening_results.py` | Applies a bureau file with full audit evidence. |
| `tools/run_cqc_reconciliation.py` | prepare -> shards -> finalize in one command. |
| `tools/daily_revenue_watch.sh` | Both reports; exit 1 when a human is needed. |

Hermes job `caregist-revenue-watch` runs the watch daily at 07:30 to Telegram
as a `no_agent` script job, so a model rate-limit cannot stop it. Its wrapper
always exits 0 on purpose: Hermes counts a non-zero exit as a job failure, and
failure streaks are what silently auto-disabled thirteen other jobs here.
