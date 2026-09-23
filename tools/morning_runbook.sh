#!/usr/bin/env bash
# Read-only. Prints the current state and the exact next command.
# Nothing here writes to production; every mutating step is printed, not run.
set -uo pipefail
cd "$(dirname "$0")/.."

echo "=== CareGist morning runbook — $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="

python3 - <<'PY'
from datetime import datetime, timezone
recon = datetime(2026, 9, 16, 12, 0, 7, tzinfo=timezone.utc)
slot  = datetime(2026, 9, 23, 2, 15, tzinfo=timezone.utc)
now   = datetime.now(timezone.utc)
breach = recon.timestamp() + 192 * 3600
left  = (breach - now.timestamp()) / 3600
run_h = 4.25
print(f"\n[1] RECONCILIATION — {left:.1f}h to breach (2026-09-24T12:00Z)")
print(f"    a run takes ~{run_h}h, so you can still fit {int(left // run_h)} attempt(s)")
delay = (now - slot).total_seconds() / 3600
if delay < 5.5:
    print(f"    the scheduled slot is {delay:.1f}h late; prior delays were 5.4h and 5.5h,")
    print("    so it may still arrive. Dispatching now is still correct: waiting to")
    print("    confirm a drop leaves no retry window.")
if left < run_h * 2:
    print("    *** margin for only one attempt. Do this FIRST. ***")
PY

echo
echo "    Last reconciliation run:"
gh run list --workflow=cqc-reconciliation.yml --limit 1 \
  --json createdAt,conclusion,status -q '.[]|"      \(.createdAt)  \(.conclusion // .status)"' 2>/dev/null \
  || echo "      (gh unavailable)"
cat <<'TXT'

    Run, in this order:
      gh workflow run cqc-reconciliation.yml --ref main -f dry_run=true
      # then, only if that is green:
      gh workflow run cqc-reconciliation.yml --ref main -f dry_run=false
    If a shard dies, RESUME — do not restart:
      gh workflow run cqc-reconciliation.yml --ref main -f dry_run=false \
        -f resume_batch_id=<batch uuid> -f resume_run_id=<run id>
    If finalize refuses on unconfirmed deactivations, re-dispatch adding:
      -f acknowledge_unconfirmed_deactivations=true
    Do NOT cancel a late scheduled run to replace it; they serialize safely.

[2] MIGRATION 064 — unblocks PR #71's only failing check
    Purely additive: 3 CREATE TABLE IF NOT EXISTS, 6 indexes, 4 functions and
    triggers, no destructive statements. Confirm a backup, then:
      PROD_DATABASE_URL=... python db/apply_migrations.py \
        --target production --confirm-production-backup

[3] MERGE PR #71 — green on everything except [2]
      gh pr merge 71 --merge

[4] RE-PIN SMOKE SHAS — do this LAST, once main has stopped moving
      gh variable set CAREGIST_EXPECTED_FRONTEND_GIT_SHA --body "$(git rev-parse origin/main)"
      gh variable set CAREGIST_EXPECTED_BACKEND_GIT_SHA  --body "$(git rev-parse origin/main)"

[5] PAID JOURNEY — yours alone, not an agent's
    One permitted test transaction on the live link, then check the receipt,
    the post-payment confirmation and the fulfilment handoff.
    Live link: https://buy.stripe.com/bJe8wI7Xhd8YdYi2vl3AY04  (£745.00)

Until [5] is done the VA may agree scope and quote £745, but must not state
that an order is accepted.
TXT
