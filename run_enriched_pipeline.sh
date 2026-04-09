#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

if [ -z "${CQC_API_KEY:-}" ]; then
    echo "ERROR: CQC_API_KEY not set. Add it to .env or export it." >&2
    exit 1
fi

PYTHON="${SCRIPT_DIR}/.venv/bin/python3"
if [ ! -x "$PYTHON" ]; then
    PYTHON="/usr/bin/python3"
fi

"$PYTHON" -u extract_cqc.py --sleep 0.02
"$PYTHON" -u clean_cqc.py
"$PYTHON" -u quality_audit.py
"$PYTHON" -u prepare_directory.py
"$PYTHON" -u support_quality_hook.py || true
