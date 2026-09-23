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

## D4 — RESOLVED. A live £745 link exists; the docs pointed at a dead one.

**This entry has been wrong twice. Both corrections are kept, because the second
mistake is the more instructive one.**

*First version:* listed CareGist Terms/Privacy URLs at Stripe checkout and a
Terms-acceptance control as blockers. Overstated — in a scope-first flow the VA
sends the terms link with the confirmed scope before payment, so the contract is
formed in writing beforehand. Henry pushed back and was right.

*Second version:* checked the link recorded in the VA pack
(`buy.stripe.com/...3AY02`), found it returns "The link is no longer active",
and concluded there was **no payment mechanism at all**. Committed that to the
repo. **That was wrong and it was sloppy** — it generalised from one dead URL
without asking whether a replacement existed. Henry caught it.

**What is actually true**, established from the Stripe API and confirmed in a
browser:

| | |
|---|---|
| Live link | `https://buy.stripe.com/bJe8wI7Xhd8YdYi2vl3AY04` (`plink_1UEkzy4mijLHzRRkWjk3pFVW`, active) |
| Sells | "Territory Opportunity Brief", quantity 1, **74500 GBP = £745.00** |
| Price / Product | `price_1UDzJP4mijLHzRRkfYJG3OZZ` / `prod_VESD16ql3keycy` |
| Superseded | `plink_1UDZBR...` (`...3AY02`), and the Product/Price IDs in the 9 Sep pack |

**The defect was in the documentation, not in Stripe**, and it is now fixed: all
three VA packs point at the live URL and the readiness check records the correct
identifiers. No Stripe change was made and none was needed.

**What genuinely remains, unchanged:** the paid journey has still never been
checked end to end — receipt, post-payment confirmation, fulfilment handoff. That
needs one permitted test transaction, it is money movement, and it stays with
Henry. It is a real gap, but it is not the emergency the second version claimed.

**Method note, since this is the second time tonight the same error appeared:**
a dead identifier in a document is evidence the document is stale, not evidence
the underlying thing is gone. Ask the system, not the note about the system. The
identical mistake produced the earlier false claim about `a1357fe`, where commit
timestamps were used instead of asking the run what it checked out.

---

## What needs none of the above

The VA can work at 08:00: agree scope in writing, quote £745, record the buyer's
criteria, and now send a payment link that actually resolves. Pricing wording is
correct and identical across every buyer surface and all three packs, verified
against production.

The ceiling stays where it was: do not state that an order is accepted until the
paid journey has been checked once.

---

## D1 — REVISED 2026-09-23 05:05Z, after Codex's investigation landed.

**Codex corrected me and is right.** I stated the Wednesday 02:15Z scheduled run
"did not fire", checking at 03:33Z — 1h18m past the slot. That was premature.
The two prior scheduled events were created **5h26m** and **5h29m** after their
declared slots:

| Run | Slot | Created | Delay | Result |
|---|---|---|---|---|
| `35069788326` | 09-16 02:15Z | 07:41:07Z | 5h26m | success |
| `35497685490` | 09-20 02:15Z | 07:44:37Z | 5h29m | cancelled |

At 05:04Z today the slot is **2.83h old** — still inside the observed envelope.
Absence is **not yet distinguishable from delay**. Codex also ruled out
repository-side suppression: workflow `330711851` is `active`, Actions are
`enabled` with `allowed_actions: all`, `main` is the default branch and carries
the workflow, and the 03:28Z push rules out the 60-day public-repo inactivity
disable. Diagnosis: GitHub schedule delivery delay.

### Where I now differ from Codex, on timing rather than diagnosis

Codex says re-check after 07:45Z. Correct for *diagnosis*, wrong for the
*deadline*. Do the arithmetic:

- Wait to 07:45Z to confirm a drop, then dispatch → finishes **~12:00Z**, exactly
  at the breach, **with no retry window at all**.
- Dispatch now (~05:05Z) → finishes **~09:20Z**, leaving roughly 2h40m of margin
  for one resume or retry.

A run takes ~4h15m and the known failure mode (a transient upstream 500 killing
a shard) is *not* fixed. Planning with zero margin against a failure mode you
have already seen twice is the wrong risk trade.

**Revised decision: dispatch now. Do not wait for 07:45Z.**

If the delayed scheduled run then arrives, that is fine and costs only duplicated
work — the concurrency group `cqc-reconciliation-production` is
`cancel-in-progress: false`, so the two serialize rather than collide.

**Codex's operational warning stands and is important:** do **not** cancel a late
scheduled run in order to replace it with a manual one. Let it queue.

### Acknowledgement input — Codex's design is right, and I withdraw my objection

I declined to add this overnight because a badly-gated input would let a
*scheduled* run accept deactivations CQC never confirmed. Codex's version gates
exactly that: default `false`, rejected on dry runs, rejected on scheduled
events, CLI flag passed only when the manual input is exactly `true`, and the
CLI semantics preserved (unconfirmed candidates stay ACTIVE, IDs and count
recorded, residual identity mismatch still refuses the batch). 96 tests pass.
That meets the safety property I was protecting. **It should ship** — it makes
the documented recovery path reachable from Actions. It is still not on the
pushed branch.
