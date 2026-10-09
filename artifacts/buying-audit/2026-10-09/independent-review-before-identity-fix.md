# Independent final technical review — 2026-10-09

**Verdict: technical clearance withheld.** Two high-severity entitlement/identity defects remain, plus incomplete failure recovery. These are static code findings with proposed reproductions, not independently executed failures. This review does not approve commercial operation, deployment, checkout, delivery, leads, claims, collectors or exports. Model agreement is not green; the producing worker cannot approve its own work.

## Scope and evidence

Read `AGENTS.md`, `.warroom/README.md`, `.warroom/PIPELINE.md`; reviewed the current working-tree production diff in billing, territory fulfilment/delivery, audit and territory scope, the three named new integration test files, relevant unit-test changes, schema migrations and webhook/full-dataset context. HEAD was `3d3f3e42e95d3f1829387df19731eb819d93e993`; findings concern the uncommitted patch over that HEAD, not a deployed release. Unrelated working-tree changes were outside scope. The generation worker's outstanding unit checks are not evidence here.

**Tests were not rerun.** No network, external actions, runtime database queries, secret inspection or production modifications were performed. Only this review artifact was written. Applied the output-quality-gate skill by comparing claims with source and supplied evidence, within the user's static-review restriction.

| Claim | Source / observable evidence | Assessment for technical reviewer |
| --- | --- | --- |
| Refund works with existing schema and fails atomically on missing audit | Migration 046; billing.py:2115–2201; audit.py:58–72; refund/webhook tests | Incompatible SQL removed; strict audit exception reaches outer webhook transaction. Supported by code and supplied synthetic tests. |
| Failed territory generation retains trusted payment and consent | delivery.py:190–332; generation recovery tests | Supported for generation/upload exceptions followed by a successful recorder; broader failures remain uncovered. |
| Refund cannot rebound into fulfilment | fulfilment.py:203–294; billing.py:1658–1781 | Territory audit guard improves this; payment identity overwrite and legacy dataset ordering remain unsafe. |
| Provider counts do not authorise purchase | territory-scope.ts diff; TerritoryScopePicker.tsx:215–275 | Helper always returns canCheckout=false; inspected component presents an enquiry and explicitly says online ordering is unavailable. No live/browser verification. |

## Findings requiring correction

### 1. HIGH — Successful territory replay can overwrite durable payment identity and ignore conflicting consent

**Location:** `api/services/territory_brief_fulfilment.py:241–309`; compare `api/services/territory_brief_delivery.py:260–332`.

The normal fulfilment SELECT omits existing payment intent, amount and currency. Its UPDATE unconditionally assigns the newly retrieved payment intent. The recorder correctly rejects a different existing intent, but the success path does not. The success path also inserts consent with `ON CONFLICT (order_id) DO NOTHING` without reading and comparing the existing evidence; the recorder does compare it.

**Proposed reproduction:** seed a failed order bound to session S and payment P1, with fewer than five attempts. Return an otherwise valid authoritative session S carrying P2. Let generation succeed. The handler locks/checks P2, overwrites P1 and grants delivery. A refund for P1 can consequently miss the order. A pre-existing consent row with different session/terms/hashes also survives silently while delivery proceeds. This requires conflicting persisted versus retrieved evidence; this review does not claim Stripe normally changes a session's payment identity. The missing fail-closed invariant is concrete, and UNIQUE payment/session indexes do not enforce immutability of a row's binding.

**Required fix / acceptance:** under the order lock, reject conflicting non-null payment evidence before generation; validate the existing immutable consent row on every path. Real-Postgres tests should prove payment and consent conflicts leave identity, status, tokens, email and artifacts unchanged. Refund/P1 contention must not be bypassed by locking P2.

### 2. HIGH — Legacy full-dataset checkout can grant access after a full refund has already committed

**Location:** `api/routers/billing.py:1658–1748`, `2155–2168`.

Refund now durably records unmatched payments, but legacy dataset fulfilment neither takes the shared payment advisory lock nor checks full-refund audit evidence. It checks only local order status. That is insufficient before the payment binding exists.

**Proposed reproduction:** reserve a pending dataset order with a null payment intent; process its full refund first. Refund updates no dataset order because it matches only `stripe_payment_intent_id` with status `paid`, but commits audit and event dedup. Then process the paid checkout session: local status is still pending, so dataset fulfilment sets paid, creates a token and queues delivery despite the prior full refund. The same omission permits a concurrent refund to miss an uncommitted payment binding. An already-paid matching dataset order still receives the existing revocation behavior; the issue is ordering around initial binding.

This is a pre-existing dataset-handler omission exposed by the shared refund repair, not a claim that this patch introduced the entire legacy defect. Restoring a previously broken refund handler does not close it.

**Required fix / acceptance:** use the same payment-lock-before-order-lock protocol and durable refund check for legacy dataset fulfilment, with authoritative payment validation. Cover refund-before-checkout and overlapping transactions using separate database connections, asserting no token/email entitlement is granted after the refund wins.

### 3. MEDIUM — Payment/consent recovery covers only generation/upload exceptions; database/commit failures and process interruption remain gaps

**Location:** `api/services/territory_brief_fulfilment.py:311–397`; `api/routers/billing.py:1583–1653`; `api/services/territory_brief_delivery.py:177–187`.

Only the generation/upload try block raises the contextual generation error consumed by the post-rollback recorder. Failure while writing fulfilled status, tokens or pending email, or committing the outer transaction, rolls back payment/consent without invoking that recorder. Successful uploads use random paths and have no compensating cleanup here. A process exit between rollback and recorder also loses the in-memory context. Database entitlement writes remain atomic, but external uploads and durable recovery do not share that guarantee.

If refund then commits while the local payment binding is absent, its territory audit guard prevents later fulfilment, but the replay raises before restoring payment/consent or marking the order refunded. The local order can remain pending without its paid evidence. This is a recovery/accounting gap, not evidence that the territory refund audit guard grants access.

**Required acceptance:** inject a failure after both uploads and at transaction commit; verify durable payment/consent/refund reconciliation and artifact cleanup policy. Define a durable reconciliation path for interruption before the recorder. The supplied tests do not establish these properties.

## Test evidence and limits

- `recovery-tests.log` reports **39 passed in 4.02s**: 30 territory unit cases, four refund integration cases, two generation recovery cases and three webhook recovery cases. These are supplied results, not this reviewer's execution; the log does not bind its run to a frozen diff hash.
- The generation tests exercise both sequential orders of recorder/refund after a real transaction rollback. They do not overlap transactions or measure lock contention. They assert one consent row, but do not test conflicting consent, payment identity overwrite, recorder rollback on conflict, or success after durable failure recovery.
- Webhook tests exercise real schema/SQL and handler dedup with synthetic signature construction and Stripe retrieval. They support sequential replay and rollback on injected strict audit failure, not live Stripe signature validity or external delivery.
- The older characterisation test intentionally seeds a failed order without payment identity and passes when refund cannot match it. Its docstring still says the recorder only persists status/error/attempts, which is stale after this patch. Its pass must not count as recovery acceptance.
- Repeating the same failure recorder advances attempts to five. Evidence insertion is idempotent, but attempt counting is not: that test records one actual generator call and multiple recorder invocations. It does not prove five distinct generation attempts or an exactly-once attempt counter.
- Direct `_handle_refund` calls in the basic refund test run without an explicit outer transaction. Their transaction-scoped advisory lock ends with the lock statement; those tests cannot establish lock protection across the subsequent mutations. Production webhook does supply the required outer transaction.
- `frontend-final-tests.log` reports **183 tests passed, zero failed/skipped**. This is Node test output, not evidence that the changed Playwright journey expectation ran. It establishes neither live readiness nor end-to-end purchase/delivery.

## Bounded positive assessment

For a stable territory payment identity inside the production webhook's outer transaction, refund, fulfilment and recorder acquire the same payment lock before the order lock. At ordinary READ COMMITTED isolation, a waiter checks durable refund evidence in a subsequent statement after acquiring the lock. Strict refund audit failure propagates through the nested audit savepoint and aborts the outer webhook transaction, including revocation and event dedup. The recorder's payment update and consent comparison share a transaction, so conflicting consent rolls its update back. These are useful repairs supported by inspection; actual contention and deployment configuration were not verified.

The enquiry-only helper change receives limited static technical clearance. The payment/recovery changes do not receive overall technical clearance until the findings above are resolved and independently verified. All named commercial gates remain closed under the repository operating loop.
