# Workflow: Restore from Snapshot

## When to invoke

Invoke this procedure when any of the following occur:

- **Data corruption**: a bug or external process wrote invalid data to the production Neon database.
- **Accidental delete**: a migration, script, or human error removed rows or tables that cannot be trivially reconstructed.
- **Rollback after a failed migration**: `apply_migrations.py` is designed to be forward-only; if a migration produces irrecoverable state, restore to the pre-migration snapshot.
- **Security incident**: a database credential was compromised and you need to restore to a known-good state on a fresh branch.

Do **not** invoke this procedure as a first resort. Check first whether the data loss can be fixed at the application layer or via a targeted SQL correction.

---

## Pre-flight

Before starting a restore, confirm all of the following:

- [ ] **Two-person rule**: a second authorised engineer is present (in-person or on a call). No solo restores. Log both names in the incident ticket.
- [ ] **Deploy lock in place**: no deployments running or queued. Check GitHub Actions and any open deploy SSH sessions.
- [ ] **Snapshot freshness confirmed**: list the available snapshots and identify the target:

  ```bash
  aws s3 ls s3://${BACKUP_S3_BUCKET}/postgres/ --recursive --region eu-west-2 | sort | tail -20
  ```

  Note the S3 key of the snapshot you intend to restore (e.g. `postgres/2025/01/15/caregist-20250115-030001.dump`).

- [ ] **Target Neon branch ready**: never restore to the production branch. Spin up a fresh Neon branch first (see Step 2 below).
- [ ] **MFA device available**: the restore IAM role requires MFA. Confirm your MFA device is to hand.
- [ ] **`RESTORE_ROLE_ARN` noted**: retrieve from `terraform output restore_role_arn` or the AWS IAM console.

---

## Break-glass IAM

The restore role is not available day-to-day. You must assume it explicitly with MFA and an ExternalId.

```bash
# Substitute your values:
#   RESTORE_ROLE_ARN  — from terraform output restore_role_arn
#   MFA_SERIAL_ARN    — arn:aws:iam::<account>:mfa/<username>
#   MFA_CODE          — current 6-digit token from your MFA device

aws sts assume-role \
  --role-arn "${RESTORE_ROLE_ARN}" \
  --role-session-name "$(whoami)-restore-$(date +%s)" \
  --external-id "caregist-restore-prod" \
  --serial-number "<MFA_SERIAL_ARN>" \
  --token-code "<MFA_CODE>" \
  --duration-seconds 3600 \
  --region eu-west-2
```

**Two-person rule**: the second engineer must witness this command being run and confirm the session name is logged in the incident ticket.

The returned credentials (`AccessKeyId`, `SecretAccessKey`, `SessionToken`) are passed automatically by `scripts/restore-from-snapshot.sh` — you do not need to export them manually when using the script.

---

## Step-by-step restore procedure

### Step 1 — Identify the snapshot S3 key

```bash
# List the last 20 snapshots (newest last)
aws s3 ls "s3://${BACKUP_S3_BUCKET}/postgres/" --recursive --region eu-west-2 | sort | tail -20
```

Note the full key of the snapshot you want, e.g.:
```
postgres/2025/01/15/caregist-20250115-030001.dump
```

Consider: is the data you need to recover present in that snapshot? The RPO is 24 hours — up to 24 hours of writes may be lost. Confirm with the incident owner which snapshot is acceptable.

### Step 2 — Spin up a fresh Neon branch as the restore target

In the Neon dashboard:
1. Go to your project → **Branches** → **Create branch**.
2. Name it `restore-test-<incident-date>` (e.g. `restore-test-20250115`).
3. Set the parent to `main` (or the branch you want to restore into).
4. Copy the connection string — it must contain `restore-test` in the hostname for the safety check to pass.

> The script hard-codes a safety check: it refuses to restore to any host that does not contain `staging` or `restore-test`. This prevents accidental production overwrites.

### Step 3 — Run the restore script

```bash
export BACKUP_S3_BUCKET="<bucket name from terraform output>"
export AWS_REGION="eu-west-2"

bash scripts/restore-from-snapshot.sh \
  --snapshot-key  "postgres/2025/01/15/caregist-20250115-030001.dump" \
  --target-db-url "postgresql://user:pass@restore-test-branch.eu-west-2.aws.neon.tech/neondb?sslmode=require" \
  --restore-role-arn "${RESTORE_ROLE_ARN}" \
  --external-id   "caregist-restore-prod" \
  --mfa-serial    "arn:aws:iam::<account>:mfa/<username>" \
  --mfa-token     "<6-digit-code>"
```

Monitor the output. The script will:
1. Assume the restore role via STS (MFA + ExternalId required).
2. Download the snapshot from S3 (decrypted via the restore role's KMS Decrypt permission).
3. Run `pg_restore --clean --if-exists --no-owner --no-privileges` against the target branch.
4. Run a verification query (`SELECT count(*) FROM trusted_event_ledger`).
5. Print a summary.

### Step 4 — Verify the restored data

Run additional verification queries specific to the incident:

```sql
-- Check row counts for key tables
SELECT 'care_providers' AS tbl, count(*) FROM care_providers
UNION ALL SELECT 'trusted_event_ledger', count(*) FROM trusted_event_ledger
UNION ALL SELECT 'provider_monitors', count(*) FROM provider_monitors;

-- Check the most recent migration applied
SELECT filename, applied_at FROM schema_migrations ORDER BY applied_at DESC LIMIT 3;

-- Spot-check a specific provider if relevant to the incident
SELECT location_id, name, registered_manager_name FROM care_providers WHERE location_id = '<id>';
```

### Step 5 — Cutover plan

If the restored data is confirmed good and you need to cut production over:

1. **Announce downtime**: notify users via status page or email.
2. **Stop the API and frontend** on EC2:
   ```bash
   sudo systemctl stop caregist-api caregist-frontend
   ```
3. **Update `DATABASE_URL`** in `/home/caregist/CareGist/.env` to point at the restored Neon branch (or promote the branch to `main` in Neon).
4. **Restart services**:
   ```bash
   sudo systemctl start caregist-api caregist-frontend
   ```
5. **Verify** the health endpoint: `curl https://caregist.co.uk/api/v1/health`
6. **Run smoke tests** per `workflows/deploy-ec2.md`.

---

## RTO

**Target: 4 hours** from incident declaration to restored service.

Typical breakdown:
- Pre-flight + two-person coordination: ~30 min
- Neon branch creation + script run: ~20 min
- Verification and spot-checking: ~30 min
- Cutover (if needed): ~30 min
- Buffer for unexpected issues: ~110 min

---

## RPO

**Up to 24 hours of writes may be lost.** Backups run daily at 03:00 UTC. A incident at 02:59 UTC means the last good snapshot is ~24 hours old.

If Neon's own point-in-time recovery (PITR) is available on the project tier, it can provide a finer-grained recovery point. Check the Neon dashboard for PITR options before defaulting to the S3 snapshot restore.

---

## Post-restore

After a successful restore, regardless of whether full cutover occurred:

1. **Rotate credentials**: rotate `DATABASE_URL`, `API_MASTER_KEY`, and any other credentials that could have been exposed during the incident.
2. **Write an incident summary**: document what happened, what data was lost, the restore timeline, and corrective actions.
3. **Record in the audit chain**: insert a row into `trusted_event_ledger` with event type `INCIDENT_RESTORE` and the incident summary as the payload.
4. **Delete the restore branch** in Neon once the incident is closed and data is confirmed good.
5. **Review backup freshness**: confirm the next scheduled backup ran successfully (check CloudWatch alarm state and S3).
