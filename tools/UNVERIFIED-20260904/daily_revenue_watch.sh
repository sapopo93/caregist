#!/usr/bin/env bash
# Daily revenue + health watch. Prints one report and exits non-zero if
# anything needs a human. Designed to be run by Hermes as a script job
# (no LLM, so a provider rate-limit cannot stop it).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

"$PY" tools/revenue_snapshot.py --days 30
echo
echo "----------------------------------------"
echo
# DETECT ONLY. Deliberately not --heal.
#
# self_heal.py --heal finalizes an in-SLA stranded reconciliation batch. That
# writes counts_reconciled=TRUE, which is the CQC freshness watermark, which
# flips commercialReadiness.checkoutReady to true, which OPENS PAID CHECKOUT.
# Sleep-checkout is parked until an explicit Go that names it as the gate, so a
# scheduled job must never be able to open it unattended. Run 6272 is exactly
# the batch this would have caught.
#
# To heal deliberately, a human runs: tools/self_heal.py --heal
"$PY" tools/self_heal.py
exit $?
