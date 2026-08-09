# Active initiative: CareGist CQC Signal Intelligence

Status: **active, stage-gated delivery**
Catalogue version: `2026-08`
Launch ICP: compliance and quality-improvement firms

Authoritative product and go-to-market strategy:
`docs/CAREGIST_MASTER_STRATEGY.md`.

## Locked catalogue

- Free Directory
- Radar Regional — £299/month
- Radar National — £799/month
- Intelligence Feed Pilot — from £6,000/year, sales-assisted
- Embedded Enterprise — quote and invoice only

Static datasets, data-pack tiers, paid provider ranking, seat add-ons, and
predictive or vacancy claims are not saleable products.

## Current gate state

| Gate | State | Evidence required to pass |
|---|---|---|
| Gate 0 — promise and catalogue safety | Blocked on legal approval | Stripe catalogue and repository copy reconciled; legal drafts still require solicitor/founder approval; checkout remains disabled |
| Gate 1 — source trust | Not started in production | Seven consecutive measured shadow days and all source/latency checks passing |
| Gate 2 — private compliance pilot | Not started | Tenant-isolation tests and 20 traceable pilot events |
| Gate 3 — grounded narratives and paid Radar | Blocked | Legal approval, 100-report gold set, billing lifecycle, and delivery latency |
| Gate 4 — Feed and Embedded | Blocked | Delivery SLO evidence, replay/signature drills, restore drill, and contract scope |

## Human approvals that code cannot satisfy

- Solicitor/founder approval of Terms, Privacy, and customer-facing legal wording
- Approval of the 100-report narrative evaluation result
- Approval of each account admitted to paid Radar while rollout is controlled
- Contract, security, DPA, and SLA approval for Feed/Embedded customers
- Separate DPIA and lawful-basis decision before named-manager processing

## Prohibited shortcuts

- Do not enable checkout merely because software tests pass.
- Do not market a target delivery time until the production shadow window proves it.
- Do not publish a narrative lacking complete source evidence.
- Do not infer vacancies, closures, expansion, or provider-level conclusions from a location event.
- Do not use the superseded July lead lists for outreach without current-product re-qualification.

## Stripe catalogue reconciliation — 9 August 2026

The exact non-secret Stripe object IDs and approved commercial attributes are
versioned in `deploy/stripe-price-manifest.json`. That manifest is digest-locked
by the offline release verifier.

- Test mode: four active final products; the temporary proof product is archived.
- Live mode: four active final products; all nine named legacy products and
  their prices are archived.
- Radar Regional is £299/month; Radar National is £799/month.
- Intelligence Feed Pilot is £6,000/year and sales-assisted.
- Embedded Enterprise has no active price. Stripe's UI required a temporary £1
  price during creation; that price was immediately archived in both modes.
- Count-only reconciliation showed zero active subscriptions for every recurring
  legacy price. The two one-off products did not expose a subscription count.
- No subscription, customer, balance, transaction, tax, API-key, Payment Link,
  or account-setting record was opened or changed.
- `BILLING_CHECKOUT_ENABLED` and `RADAR_CHECKOUT_ENABLED` remain false by
  default. Creating the catalogue did not make any checkout public.

## Implementation versus release state

The repository contains the additive database migration, collectors, canonical
event ledger, tenant-owned Radar APIs, durable delivery outbox, UI, legal drafts,
and fail-closed billing gates. These changes have not been deployed to production
and migration `049_cqc_signal_intelligence.sql` has not been applied to a live
database as part of this initiative update.

Gate 0 cannot pass until the legal drafts and checkout wording are approved by a
qualified human reviewer. Gate 1 then requires seven consecutive measured days
in production shadow mode; local tests cannot substitute for that evidence.

## Local validation evidence

- Python runtime: 3.12.13.
- Ruff: all API, test, tool, and ingestion targets passed.
- Pytest: 545 passed; one dependency deprecation warning from Starlette's
  current TestClient/httpx bridge.
- Frontend: 102 tests passed; TypeScript passed; Next.js 16.2.12 production
  build passed.
- Stripe verifier: 17/17 offline checks passed independently for test and live
  catalogue IDs without making a Stripe API call.
- `git diff --check`: passed.

The Next.js build retains one non-fatal Turbopack file-tracing warning from the
existing directory fallback file-store import path. It does not prevent the
production build, but remains technical debt to scope separately.
