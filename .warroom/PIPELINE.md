# PIPELINE — CareGist collection → publication → sale → fulfilment

**Refreshed:** 2026-09-11 00:30 BST. Measured against live production.

---

## Stage 1 — Collection

| | |
|---|---|
| **State** | `PARTIAL` |
| **Evidence** | `cqc-signal-poll` green, last success 2026-09-10T21:48Z (18 m 49 s), running every ~2–5 h. `eventActivity.latestObservedAt` 2026-09-10T21:54:08Z, `latestEffectiveDate` 2026-09-09. |
| **Gap** | Authoritative reconciliation never completed. Last attempt **failed at 21,000 / 57,085 = 36.79 %**. `reconciledAt: null`, `sourceRetrievedAt: null`. |
| **Risk** | Signal polling works; the *authoritative count* does not. A poll is not a reconciliation. |

## Stage 2 — Publication

| | |
|---|---|
| **State** | `RUNNING` |
| **Evidence** | Public site 200 on `/`, `/pricing`, `/search`, `/territory-opportunity-brief`, `/data-status`, `/why-caregist`, `/examples/birmingham-solihull/index.html`. `/api/health/directory` → `status ok`, `writeMode database`, `readMode database`, `databaseAvailable true`. |
| **Live scale** | 58,937 location rows · 57,188 active locations · 37,111 active provider organisations · 10,006 named group labels. |
| **Gap** | Publication is live but published on a source that is **24.2 h over its 192 h freshness SLA**. |
| **Not found** | `/directory`, `/radar`, `/pricing/territory`, `/territory-opportunity-brief/example` all 404. `/search` is the real directory surface. |

## Stage 3 — Sale (ordering)

| | |
|---|---|
| **State** | `NOT RUNNING` (for money) |
| **Evidence** | Live `/pricing` presents the £795 Territory Opportunity Brief as the only paid offer, with a **`mailto:` CTA** ("Start a scope conversation"). No order form, no cart, no checkout route deployed. |
| **Free tier** | Directory search is live and free — this is the only genuinely working "product" end-to-end. |
| **Gap** | The distance between "an interested buyer" and "a recorded order" is entirely human, unmanaged and unmeasured. `ASKED_TO_PAY`: 0 recorded. |

## Stage 4 — Payment

| | |
|---|---|
| **State** | `NOT RUNNING` |
| **Evidence** | `/api/v1/health` → `commercialReadiness.checkoutReady: false`, `shadowCoveragePassed: false`, `delivery.enabled: false`. `billing_checkout_enabled` defaults `False`. |
| **Config smell** | Production Vercel holds `TERRITORY_BRIEF_CHECKOUT_ENABLED` and `STRIPE_PRICE_TERRITORY_BRIEF`, but **no code on `main` reads either** (`git grep` over `api/` and `frontend/` → no matches). |
| **`ASKED_TO_PAY` / `PAID`** | 0 / 0 |
| **Note** | Fail-closed is correct here. The gate is doing its job. |

## Stage 5 — Fulfilment

| | |
|---|---|
| **State** | `MANUAL ONLY` |
| **Evidence** | No generator, renderer, delivery or fulfilment code exists on `main` — `api/services/territory_brief*.py` live **only** on the unmerged branch, with `territory_self_serve_checkout_enabled: False`. The published promise is a human-produced pack in "three working days". |
| **Gap** | Fulfilment capacity is one human's calendar. Not measured, not scheduled, not backed up. |
| **Blocked from automation by** | Migration 060 unapplied · code unmerged · Blob and Resend credentials unverified · **terms unsigned**. |

## Stage 6 — Operations

| | |
|---|---|
| **State** | `DEGRADED` |
| **Evidence** | Freshness watchdog **crash-fails in ~17 s** (`ModuleNotFoundError: pydantic_settings`) on every scheduled run — it never reaches a check. Production smoke **red on every scheduled run since 2026-09-03** against a SHA that is not on `main`. `WATCHDOG_NOTIFICATIONS_ENABLED: false`. |
| **Consequence** | The two alarms that should have caught Stage 1 and Stage 2 are both non-functional, and one is silent. Detection, not data, is the operations failure. |
| **Working** | `cqc-signal-poll` (green). Site availability (200s). DB read/write (`database` mode). |

---

## Where the chain actually breaks

```
[1] Collection   PARTIAL ──── 36.79% reconciled · 24.2h over SLA
        │
[2] Publication  RUNNING ──── live, but on stale source
        │
[3] Sale         NOT RUNNING ─ mailto only · 0 asked to pay
        │
[4] Payment      NOT RUNNING ─ checkoutReady false ✓ (correctly closed)
        │
[5] Fulfilment   MANUAL ───── no deployed code, unsigned terms
        │
[6] Operations   DEGRADED ─── both alarms broken · one silent
```

**The break is at Stage 1 and Stage 6, not Stage 3–5.** Building more checkout surface
cannot fix a sourcing claim that is 24.2 h overdue, and cannot fix alarms that never fire.
Any proposal that starts at Stage 3 or 4 is **out of order** and gains nothing this week.
