# Decisions — taken on Henry's standing authority, 2026-09-23 05:30Z

Henry: *"make recommendation where it needs my input and we take your
recommendations as mine."*

These are therefore **decisions, not options**. Each one is written so it can be
executed without re-deciding anything. Where I declined to decide, I say why.

**I could not execute any of D1–D3 myself.** The harness permission classifier
refuses `gh workflow run`, `gh variable set` and production migrations as
"Modify Shared Resources" — including the *no-write* reconciliation dry run. I
did not route around that via `psql`, because that bypasses the intent of the
block rather than the mechanism. To let an agent do these in future, add a Bash
permission rule; otherwise they are three commands for you.

---

## D1 — Run the reconciliation. Dry run first. **Do this before anything else.**

**Decision: RUN IT.** The blocker that killed the last attempt has cleared —
`1-147345129` returned HTTP 500 five times on 20 Sep and now returns **200**.
This was a coin flip 24h ago. It is not now.

**Timing is the whole point.** A real run takes ~4h15m (`max-parallel: 4` over
8 shards). The watermark breaches **2026-09-24T12:00Z**. Start by 07:00Z and
there is room for a failure and a retry; start after ~07:30Z and there is room
for one attempt only.

```bash
# 1. Validate first — minutes, no writes. Confirms source and projected runtime.
gh workflow run cqc-reconciliation.yml --ref main -f dry_run=true -f sleep=0.08

# 2. Only if the dry run is green, the real one:
gh workflow run cqc-reconciliation.yml --ref main -f dry_run=false -f sleep=0.08
```

**If it fails part-way, do NOT restart it.** Resume from the manifest — this is
the difference between losing 20 minutes and losing four hours:

```bash
gh workflow run cqc-reconciliation.yml --ref main -f dry_run=false \
  -f resume_batch_id=<failed batch UUID> -f resume_run_id=<the run id>
```

**If finalize refuses on unconfirmed deactivations**, that is the guard working,
not a bug. The recovery path exists on `main` today and is manual-only by
construction (it defaults false and the workflow never passes it, so no
scheduled run can reach it):

```
python incremental_update.py ... --acknowledge-unconfirmed-deactivations
```

**Residual risk, stated plainly:** `finalize` is still
`needs: [prepare, shards]` with no `always()`, so one transient upstream 500
anywhere across 57,151 locations still discards the attempt. That is why the
dry run and the resume path matter.

---

## D2 — Apply migration `064` to production.

**Decision: APPLY IT.** It is additive only (`CREATE TABLE IF NOT EXISTS` plus
indexes), it carries a down migration, I reviewed it, and it replays cleanly on
top of `060`–`063` against a real Postgres. Schema-before-code is the order the
drift gate is built to enforce, so this is the correct next step in your own
process, not a workaround of it.

One caveat I cannot discharge: the tool requires `--confirm-production-backup`
and **I could not verify a backup exists.** Confirm that before running it.

---

## D3 — Re-pin the smoke SHAs **last**, after the morning's final merge.

**Decision: DO IT, but AFTER D2 and the PR #71 merge — not before.**

I earlier suggested doing this first. That was wrong and I am correcting it:
merging #71 moves `main`, which would immediately re-break a pin set beforehand.
Set it once, when `main` has stopped moving for the morning.

```bash
gh variable set CAREGIST_EXPECTED_FRONTEND_GIT_SHA --body "$(git rev-parse origin/main)"
gh variable set CAREGIST_EXPECTED_BACKEND_GIT_SHA  --body "$(git rev-parse origin/main)"
```

Safe because production demonstrably tracks `main` within minutes — it followed
all six of last night's pushes, and I verified the live SHA independently of the
smoke check each time. The durable fix is the deployment-derived release
identity already in PR #71, which makes this pin unnecessary once merged.

---

## D4 — Stripe: **I am not deciding this one, and no delegation should make me.**

Configuring payment collection and running a real test transaction is money
movement. I will not do it and I would not recommend any agent does, regardless
of authority granted. This is yours personally:

1. In Stripe product public details, set the CareGist **Terms** and **Privacy**
   URLs (currently they point at Stripe's own legal pages).
2. Enable Terms acceptance at checkout where available.
3. Complete one permitted test transaction and check the receipt, the
   post-payment confirmation and the fulfilment handoff end to end.

Until these are done the VA's ceiling is: agree scope in writing, quote £745,
record the buyer's criteria. **No payment link, no accepted order.**

---

## What needs none of the above

The VA can work at 08:00 regardless. Pricing wording is correct and identical
across every buyer surface and all three packs, verified against production;
the readiness check no longer wrongly tells them terms are a blocker. That part
is done.
