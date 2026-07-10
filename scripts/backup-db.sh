#!/usr/bin/env bash
# scripts/backup-db.sh
#
# Daily Neon -> S3 backup for Caregist.
# Runs as the EC2 instance profile (caregist-backup-prod) which has
# write-only access to s3://${BACKUP_S3_BUCKET}/postgres/ and KMS encrypt.
#
# Required environment variables (set in /etc/environment or the cron wrapper):
#   DATABASE_URL        — PostgreSQL connection string (from production .env)
#   BACKUP_S3_BUCKET    — bucket name (output from terraform output backup_bucket_name)
#   BACKUP_KMS_KEY_ARN  — CMK ARN    (output from terraform output kms_key_arn)
#   AWS_REGION          — defaults to eu-west-2
#
# Optional:
#   BACKUP_MAX_RETRIES  — number of upload retry attempts (default 3)
#
# Cron entry (see workflows/backup-monitoring.md):
#   0 3 * * * caregist-app /opt/caregist/scripts/backup-db.sh >> /var/log/caregist/backup.log 2>&1

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${BACKUP_S3_BUCKET:?BACKUP_S3_BUCKET must be set}"
: "${BACKUP_KMS_KEY_ARN:?BACKUP_KMS_KEY_ARN must be set}"
AWS_REGION="${AWS_REGION:-eu-west-2}"
BACKUP_MAX_RETRIES="${BACKUP_MAX_RETRIES:-3}"

TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")
YEAR=$(date -u +"%Y")
MONTH=$(date -u +"%m")
DAY=$(date -u +"%d")
DUMP_FILE="/tmp/caregist-${TIMESTAMP}.dump"
S3_KEY="postgres/${YEAR}/${MONTH}/${DAY}/caregist-${TIMESTAMP}.dump"
LOG_PREFIX="[caregist-backup][${TIMESTAMP}]"

# ── Helpers ──────────────────────────────────────────────────────────────────

log() { echo "${LOG_PREFIX} $*" >&2; }

emit_metric() {
  local value="$1"
  aws cloudwatch put-metric-data \
    --region "${AWS_REGION}" \
    --namespace "Caregist/Backup" \
    --metric-name "BackupSuccess" \
    --value "${value}" \
    --dimensions "Name=Environment,Value=${ENVIRONMENT:-prod}" \
    --unit "Count" || true  # never let a metric failure abort the script
}

cleanup() {
  if [[ -f "${DUMP_FILE}" ]]; then
    rm -f "${DUMP_FILE}"
    log "Cleaned up local dump file."
  fi
}

trap cleanup EXIT

fail() {
  log "FATAL: $*"
  emit_metric 0
  exit 1
}

# ── Step 1: pg_dump ──────────────────────────────────────────────────────────

log "Starting pg_dump to ${DUMP_FILE}"
pg_dump \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-privileges \
  --dbname="${DATABASE_URL}" \
  --file="${DUMP_FILE}" \
  || fail "pg_dump failed."

DUMP_SIZE=$(du -sh "${DUMP_FILE}" | awk '{print $1}')
log "pg_dump complete. Dump size: ${DUMP_SIZE}. Uploading to s3://${BACKUP_S3_BUCKET}/${S3_KEY}"

# ── Step 2: Upload to S3 with retries ────────────────────────────────────────

upload_to_s3() {
  aws s3 cp \
    "${DUMP_FILE}" \
    "s3://${BACKUP_S3_BUCKET}/${S3_KEY}" \
    --sse aws:kms \
    --sse-kms-key-id "${BACKUP_KMS_KEY_ARN}" \
    --region "${AWS_REGION}" \
    --expected-size "$(stat -c%s "${DUMP_FILE}")" \
    --no-progress
}

ATTEMPT=0
UPLOADED=false
while [[ "${ATTEMPT}" -lt "${BACKUP_MAX_RETRIES}" ]]; do
  ATTEMPT=$(( ATTEMPT + 1 ))
  log "Upload attempt ${ATTEMPT}/${BACKUP_MAX_RETRIES}..."
  if upload_to_s3; then
    UPLOADED=true
    break
  else
    WAIT=$(( 2 ** ATTEMPT ))
    log "Upload failed. Retrying in ${WAIT}s..."
    sleep "${WAIT}"
  fi
done

if [[ "${UPLOADED}" != "true" ]]; then
  fail "Upload failed after ${BACKUP_MAX_RETRIES} attempts."
fi

# ── Step 3: Verify the upload ─────────────────────────────────────────────────

log "Verifying upload..."
aws s3api head-object \
  --bucket "${BACKUP_S3_BUCKET}" \
  --key "${S3_KEY}" \
  --region "${AWS_REGION}" \
  > /dev/null \
  || fail "Upload verification failed: object not found in S3."

log "Backup verified at s3://${BACKUP_S3_BUCKET}/${S3_KEY}"

# ── Step 4: Emit CloudWatch success metric ────────────────────────────────────

emit_metric 1
log "SUCCESS. Backup complete."
