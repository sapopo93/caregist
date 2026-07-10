#!/usr/bin/env bash
# scripts/restore-from-snapshot.sh
#
# Break-glass restore: downloads a Neon snapshot from S3 and restores it to a
# staging or test Neon branch.
#
# SAFETY: This script REFUSES to restore to any database whose hostname does
# not contain "staging" or "restore-test". It will never auto-restore to prod.
#
# Usage:
#   restore-from-snapshot.sh \
#     --snapshot-key  postgres/2025/01/15/caregist-20250115-030001.dump \
#     --target-db-url "postgresql://user:pass@branch.eu-west-2.aws.neon.tech/neondb?sslmode=require" \
#     --restore-role-arn "arn:aws:iam::123456789012:role/caregist-restore-prod" \
#     --external-id   "caregist-restore-prod" \
#     --mfa-serial    "arn:aws:iam::123456789012:mfa/your-username" \
#     --mfa-token     "123456"
#
# Required environment variables:
#   BACKUP_S3_BUCKET  — bucket name (from terraform output)
#   AWS_REGION        — defaults to eu-west-2
#
# Full procedure: see workflows/restore-from-snapshot.md

set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-west-2}"
LOG_PREFIX="[caregist-restore][$(date -u +%Y%m%d-%H%M%S)]"

# ── Argument parsing ──────────────────────────────────────────────────────────

SNAPSHOT_KEY=""
TARGET_DB_URL=""
RESTORE_ROLE_ARN=""
EXTERNAL_ID=""
MFA_SERIAL=""
MFA_TOKEN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --snapshot-key)    SNAPSHOT_KEY="$2";    shift 2 ;;
    --target-db-url)   TARGET_DB_URL="$2";   shift 2 ;;
    --restore-role-arn) RESTORE_ROLE_ARN="$2"; shift 2 ;;
    --external-id)     EXTERNAL_ID="$2";     shift 2 ;;
    --mfa-serial)      MFA_SERIAL="$2";      shift 2 ;;
    --mfa-token)       MFA_TOKEN="$2";       shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

: "${SNAPSHOT_KEY:?--snapshot-key is required}"
: "${TARGET_DB_URL:?--target-db-url is required}"
: "${RESTORE_ROLE_ARN:?--restore-role-arn is required}"
: "${EXTERNAL_ID:?--external-id is required}"
: "${MFA_SERIAL:?--mfa-serial is required}"
: "${MFA_TOKEN:?--mfa-token is required}"
: "${BACKUP_S3_BUCKET:?BACKUP_S3_BUCKET env var must be set}"

log() { echo "${LOG_PREFIX} $*" >&2; }
fail() { log "FATAL: $*"; exit 1; }

# ── Safety: refuse prod targets ────────────────────────────────────────────────

TARGET_HOST=$(echo "${TARGET_DB_URL}" | sed -E 's|.*@([^/:]+).*|\1|')
log "Target host: ${TARGET_HOST}"

if [[ "${TARGET_HOST}" != *"staging"* ]] && [[ "${TARGET_HOST}" != *"restore-test"* ]]; then
  fail "SAFETY ABORT: Target hostname '${TARGET_HOST}' does not contain 'staging' or 'restore-test'. " \
       "This script refuses to restore to production. Create a Neon branch first and pass its connection string."
fi

log "Safety check passed: target is non-production (${TARGET_HOST})."

# ── Assume the restore role via STS ───────────────────────────────────────────

log "Assuming restore role ${RESTORE_ROLE_ARN} (MFA required)..."
SESSION_NAME="$(whoami)-restore-$(date +%s)"

CREDS_JSON=$(aws sts assume-role \
  --role-arn "${RESTORE_ROLE_ARN}" \
  --role-session-name "${SESSION_NAME}" \
  --external-id "${EXTERNAL_ID}" \
  --serial-number "${MFA_SERIAL}" \
  --token-code "${MFA_TOKEN}" \
  --duration-seconds 3600 \
  --region "${AWS_REGION}" \
  --output json) || fail "sts:AssumeRole failed. Check MFA token, ExternalId, and role ARN."

export AWS_ACCESS_KEY_ID=$(echo "${CREDS_JSON}"    | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['AccessKeyId'])")
export AWS_SECRET_ACCESS_KEY=$(echo "${CREDS_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['SecretAccessKey'])")
export AWS_SESSION_TOKEN=$(echo "${CREDS_JSON}"     | python3 -c "import sys,json; print(json.load(sys.stdin)['Credentials']['SessionToken'])")

log "Restore role assumed. Session: ${SESSION_NAME}"

# ── Download the snapshot ──────────────────────────────────────────────────────

DUMP_FILE="/tmp/restore-$(date +%s).dump"

log "Downloading s3://${BACKUP_S3_BUCKET}/${SNAPSHOT_KEY}..."
aws s3 cp \
  "s3://${BACKUP_S3_BUCKET}/${SNAPSHOT_KEY}" \
  "${DUMP_FILE}" \
  --region "${AWS_REGION}" \
  || fail "Download failed. Check that the snapshot key exists and the restore role has s3:GetObject."

DUMP_SIZE=$(du -sh "${DUMP_FILE}" | awk '{print $1}')
log "Downloaded: ${DUMP_FILE} (${DUMP_SIZE})"

# ── Restore via pg_restore ────────────────────────────────────────────────────

log "Running pg_restore against target (host: ${TARGET_HOST})..."
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  --dbname="${TARGET_DB_URL}" \
  "${DUMP_FILE}" \
  || fail "pg_restore failed. Review the output above for errors."

log "pg_restore completed."

# ── Verification query ────────────────────────────────────────────────────────

log "Running verification query: SELECT count(*) FROM trusted_event_ledger"
LEDGER_COUNT=$(psql "${TARGET_DB_URL}" -t -c "SELECT count(*) FROM trusted_event_ledger;" 2>&1 | tr -d '[:space:]')

if [[ -z "${LEDGER_COUNT}" ]] || [[ "${LEDGER_COUNT}" -lt 1 ]]; then
  fail "Verification failed: trusted_event_ledger returned 0 rows or query error. Restore may be incomplete."
fi

log "Verification passed: trusted_event_ledger has ${LEDGER_COUNT} rows."

# ── Cleanup ───────────────────────────────────────────────────────────────────

rm -f "${DUMP_FILE}"
log "Local dump file removed."

log "============================================================"
log "RESTORE COMPLETE"
log "  Snapshot : s3://${BACKUP_S3_BUCKET}/${SNAPSHOT_KEY}"
log "  Target   : ${TARGET_HOST}"
log "  Session  : ${SESSION_NAME}"
log "  Ledger   : ${LEDGER_COUNT} rows"
log "============================================================"
log "NEXT STEPS (from workflows/restore-from-snapshot.md):"
log "  1. Run additional verification queries specific to the incident."
log "  2. If cutting over, update DATABASE_URL in production .env and restart services."
log "  3. Rotate any credentials potentially exposed during the incident."
log "  4. Write an incident summary and record it in the audit chain."
