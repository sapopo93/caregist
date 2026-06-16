# Workflow: Backup Monitoring

## The backup script

`scripts/backup-db.sh` performs a nightly `pg_dump` of the Neon database, uploads it to S3 with SSE-KMS encryption, and emits a CloudWatch metric on completion. See the script for full details.

---

## The cron entry

Add the following to `/etc/cron.d/caregist` on the EC2 instance. This runs the backup at 03:00 UTC every day, appending output to a dedicated log file.

```cron
# Caregist daily database backup — runs at 03:00 UTC
# Environment variables must be set in /etc/environment or via a wrapper
0 3 * * * caregist-app BACKUP_S3_BUCKET=<bucket> BACKUP_KMS_KEY_ARN=<arn> AWS_REGION=eu-west-2 /opt/caregist/scripts/backup-db.sh >> /var/log/caregist/backup.log 2>&1
```

> **Adjust the path** if the scripts directory is mounted elsewhere (e.g. `/home/caregist/CareGist/scripts/backup-db.sh`).

### Recommended approach: use /etc/environment

Rather than embedding secrets in the cron entry, add them to `/etc/environment` so they are available to all cron jobs:

```bash
# /etc/environment (root-owned, 0644)
BACKUP_S3_BUCKET=caregist-backups-prod-<account-id>
BACKUP_KMS_KEY_ARN=arn:aws:kms:eu-west-2:<account-id>:key/<key-id>
AWS_REGION=eu-west-2
```

Then the cron entry simplifies to:

```cron
0 3 * * * caregist-app /opt/caregist/scripts/backup-db.sh >> /var/log/caregist/backup.log 2>&1
```

### Create the log directory

```bash
sudo mkdir -p /var/log/caregist
sudo chown caregist-app:caregist-app /var/log/caregist
```

---

## CloudWatch alarm

The Terraform module (`terraform/cloudwatch.tf`) creates the alarm `caregist-backup-missing-prod`. It triggers when:

- No `Caregist/Backup/BackupSuccess` metric is emitted within 30 hours (i.e. backup script did not run, or metric emission failed), **or**
- The metric value is 0 (backup script ran but reported failure).

### Where alerts land

The alarm is configured to send to an SNS topic. After `terraform apply`, the owner must:

1. Uncomment the SNS topic resource in `terraform/cloudwatch.tf`.
2. Add `ops@caregist.co.uk` as a subscriber.
3. Confirm the subscription from the email inbox.

Until this is done, the alarm will fire in CloudWatch but not send email notifications. Check alarm state manually:

```bash
aws cloudwatch describe-alarms \
  --alarm-names caregist-backup-missing-prod \
  --region eu-west-2 \
  --query 'MetricAlarms[0].StateValue'
```

### Viewing recent backup metrics

```bash
aws cloudwatch get-metric-statistics \
  --namespace Caregist/Backup \
  --metric-name BackupSuccess \
  --dimensions Name=Environment,Value=prod \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 86400 \
  --statistics Maximum \
  --region eu-west-2
```

---

## Monthly restore test

**Frequency**: once per month, on a weekday with two engineers available.

**Purpose**: verify that:
1. A recent snapshot can be downloaded and decrypted.
2. `pg_restore` completes without errors.
3. The verification query returns a plausible row count.
4. The restore role and ExternalId are still valid.

### Procedure

1. **Identify a recent snapshot** (from the last 7 days):

   ```bash
   aws s3 ls s3://${BACKUP_S3_BUCKET}/postgres/ --recursive --region eu-west-2 | sort | tail -5
   ```

2. **Create a temporary Neon branch** named `restore-test-<YYYYMM>` in the Neon dashboard. Copy the connection string.

3. **Run the restore script**:

   ```bash
   export BACKUP_S3_BUCKET="<bucket>"
   export AWS_REGION="eu-west-2"

   bash scripts/restore-from-snapshot.sh \
     --snapshot-key  "postgres/<YYYY>/<MM>/<DD>/caregist-<TIMESTAMP>.dump" \
     --target-db-url "postgresql://...@restore-test-<YYYYMM>.eu-west-2.aws.neon.tech/neondb?sslmode=require" \
     --restore-role-arn "${RESTORE_ROLE_ARN}" \
     --external-id   "caregist-restore-prod" \
     --mfa-serial    "arn:aws:iam::<account>:mfa/<username>" \
     --mfa-token     "<6-digit-code>"
   ```

4. **Verify the restored data** with additional spot-check queries:

   ```sql
   SELECT count(*) FROM care_providers;
   SELECT count(*) FROM trusted_event_ledger;
   SELECT count(*) FROM provider_monitors;
   ```

5. **Record the result** in the monthly ops log:
   - Date of test
   - Snapshot used (S3 key)
   - Row counts from verification queries
   - Time taken end-to-end
   - Any issues encountered

6. **Delete the test Neon branch** in the Neon dashboard.

### Log file

Keep a simple CSV or markdown table in your ops notes:

```
| Date       | Snapshot key                                      | Ledger rows | Duration | Notes |
|------------|---------------------------------------------------|-------------|----------|-------|
| 2025-02-01 | postgres/2025/01/31/caregist-20250131-030001.dump | 14,832      | 18 min   | OK    |
```
