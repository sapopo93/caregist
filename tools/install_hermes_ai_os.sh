#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR_PROFILE="ai-company-governed"
CODER_PROFILE="coder"
CRON_NAME="AI OS GitHub repair ingest"
SCRIPT_NAME="ai-os-github-ingest.py"
SOURCE_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/hermes_ai_os_ingest.py"

fail() {
  printf 'AI_OS_INSTALL_FAIL: %s\n' "$*" >&2
  exit 1
}

command -v hermes >/dev/null 2>&1 || fail "hermes CLI not found"
command -v gh >/dev/null 2>&1 || fail "GitHub CLI (gh) not found"
command -v python3 >/dev/null 2>&1 || fail "python3 not found"
[[ -f "$SOURCE_SCRIPT" ]] || fail "missing $SOURCE_SCRIPT"

gh auth status >/dev/null 2>&1 || fail "gh is not authenticated. Run: gh auth login"
gh repo view sapopo93/caregist --json nameWithOwner >/dev/null || fail "gh cannot read sapopo93/caregist"
gh repo view sapopo93/regintel-v2 --json nameWithOwner >/dev/null || fail "gh cannot read sapopo93/regintel-v2"

orchestrator_info="$(hermes profile show "$ORCHESTRATOR_PROFILE" 2>&1)" \
  || fail "Hermes profile '$ORCHESTRATOR_PROFILE' is missing"
coder_info="$(hermes profile show "$CODER_PROFILE" 2>&1)" \
  || fail "Hermes profile '$CODER_PROFILE' is missing"

# Fail closed: the dispatch contract says Codex, so do not silently run another
# provider under the coder profile. The interactive Hermes model picker is the
# canonical one-time correction if this check fails.
if ! printf '%s\n' "$coder_info" | grep -Eiq 'openai-codex|codex'; then
  cat >&2 <<'EOF'
AI_OS_INSTALL_BLOCKED: the 'coder' profile is not visibly configured for Codex.
Configure it once with the Hermes model picker, then rerun this installer:

  hermes -p coder model

Choose the OpenAI Codex provider/runtime you have authenticated. Do not guess a
model name in config by hand.
EOF
  exit 2
fi

profile_path="$(printf '%s\n' "$orchestrator_info" | sed -n 's/^Path:[[:space:]]*//p' | head -n 1)"
[[ -n "$profile_path" ]] || fail "could not resolve HERMES_HOME from 'hermes profile show $ORCHESTRATOR_PROFILE'"
case "$profile_path" in
  '~/'*) profile_path="$HOME/${profile_path#\~/}" ;;
esac
mkdir -p "$profile_path/scripts"
install -m 700 "$SOURCE_SCRIPT" "$profile_path/scripts/$SCRIPT_NAME"

# Kanban is Hermes' durable multi-agent board. init is idempotent.
hermes -p "$ORCHESTRATOR_PROFILE" kanban init >/dev/null

# The gateway owns the Kanban dispatcher. Do not start a second standalone
# daemon; require the governed gateway that the user already operates.
if ! hermes -p "$ORCHESTRATOR_PROFILE" gateway status >/dev/null 2>&1; then
  fail "the $ORCHESTRATOR_PROFILE gateway is not healthy; start/fix it before enabling autonomous dispatch"
fi

if hermes -p "$ORCHESTRATOR_PROFILE" cron list 2>/dev/null | grep -Fq "$CRON_NAME"; then
  printf 'AI_OS_INSTALL: cron already exists: %s\n' "$CRON_NAME"
else
  hermes -p "$ORCHESTRATOR_PROFILE" cron create "every 5m" \
    --no-agent \
    --script "$SCRIPT_NAME" \
    --deliver local \
    --name "$CRON_NAME" >/dev/null
  printf 'AI_OS_INSTALL: created zero-token cron: %s\n' "$CRON_NAME"
fi

# Run the deterministic ingest once now so already-ready repair issues do not
# wait for the first scheduler tick. No model is invoked by this script.
HERMES_HOME="$profile_path" python3 "$profile_path/scripts/$SCRIPT_NAME"

printf '\nAI_OS_INSTALL_OK\n'
printf 'orchestrator_profile: %s\n' "$ORCHESTRATOR_PROFILE"
printf 'worker_profile: %s\n' "$CODER_PROFILE"
printf 'poller: %s/scripts/%s\n' "$profile_path" "$SCRIPT_NAME"
printf 'cron: %s (every 5m, no-agent)\n' "$CRON_NAME"
printf '\nCurrent Kanban tasks:\n'
hermes -p "$ORCHESTRATOR_PROFILE" kanban list
