# Terraform — Caregist Backup & KMS Infrastructure (Phase A)

This module provisions the AWS resources required for automated daily database backups and EBS encryption for Caregist. It does **not** manage the existing EC2 instance itself — see the note on Phase B below.

## What this module creates

| Resource | Purpose |
|---|---|
| `aws_kms_key.backup` + alias | Customer-managed CMK for SSE-KMS encryption of S3 objects and new EBS volumes |
| `aws_s3_bucket.backups` | Backup bucket with versioning, SSE-KMS, lifecycle rules, and HTTPS-only policy |
| `aws_iam_role.backup` + profile | EC2 instance profile: write-only S3 + KMS encrypt |
| `aws_iam_role.restore` | Break-glass restore role: read-only S3 + KMS decrypt (MFA + ExternalId required) |
| `aws_ebs_default_kms_key.this` | Sets account default EBS KMS key so new volumes use the CMK |
| `aws_cloudwatch_metric_alarm.backup_missing` | Fires if no backup metric lands within 30 hours |

## Prerequisites

1. AWS credentials configured for `eu-west-2` (London) with permission to create KMS keys, S3 buckets, and IAM roles.
2. Terraform >= 1.5.0 installed locally.
3. A remote state bucket created in `eu-west-2` (see Remote State section below).

## Quickstart

```bash
cd terraform

# 1. Copy the example tfvars and fill in your values
cp prod.tfvars.example prod.tfvars   # create this file — see variables.tf for required fields

# 2. Initialise Terraform (downloads provider plugins)
terraform init

# 3. Review what will be created — no AWS resources are touched yet
terraform plan -var-file=prod.tfvars

# 4. Apply (creates KMS key, S3 bucket, IAM roles, CloudWatch alarm)
terraform apply -var-file=prod.tfvars
```

## Required tfvars

Create `terraform/prod.tfvars` (do NOT commit to git — add to `.gitignore`):

```hcl
ec2_instance_id = "i-0abc123def456789"   # your EC2 instance ID
neon_project_id = "your-neon-project-id" # from the Neon dashboard
```

## Remote State

The backend block in `providers.tf` is commented out. Before running `terraform apply` in a shared team environment, create a state bucket and uncomment the block:

```bash
# Create the state bucket (one-time setup — do not use Terraform to manage the state bucket itself)
aws s3api create-bucket \
  --bucket caregist-tfstate-$(aws sts get-caller-identity --query Account --output text) \
  --region eu-west-2 \
  --create-bucket-configuration LocationConstraint=eu-west-2

aws s3api put-bucket-versioning \
  --bucket caregist-tfstate-<ACCOUNT_ID> \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket caregist-tfstate-<ACCOUNT_ID> \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

Then uncomment the `backend "s3"` block in `terraform/providers.tf` and set the bucket name.

## What to verify after first apply

```bash
# 1. KMS key exists and alias is correct
aws kms describe-key --region eu-west-2 --key-id alias/caregist-backup-prod

# 2. S3 bucket exists with SSE-KMS
aws s3api get-bucket-encryption --region eu-west-2 \
  --bucket $(terraform output -raw backup_bucket_name)

# 3. Versioning enabled
aws s3api get-bucket-versioning --region eu-west-2 \
  --bucket $(terraform output -raw backup_bucket_name)

# 4. IAM roles exist
aws iam get-role --role-name caregist-backup-prod
aws iam get-role --role-name caregist-restore-prod

# 5. CloudWatch alarm exists
aws cloudwatch describe-alarms --region eu-west-2 \
  --alarm-names caregist-backup-missing-prod
```

## Attach the instance profile to the existing EC2

After `terraform apply` completes:

```bash
aws ec2 associate-iam-instance-profile \
  --region eu-west-2 \
  --instance-id <EC2_INSTANCE_ID> \
  --iam-instance-profile Name=$(terraform output -raw backup_instance_profile_name)
```

> Note: If the instance already has an instance profile, you must first disassociate it:
> `aws ec2 describe-iam-instance-profile-associations --filters Name=instance-id,Values=<ID>`
> then `aws ec2 disassociate-iam-instance-profile --association-id <ASSOC_ID>`

## Verify the backup script can write to S3

SSH into the EC2 instance and run a quick write test using the instance profile credentials:

```bash
# On the EC2 instance (instance profile must be attached first)
export BACKUP_S3_BUCKET="$(aws sts get-caller-identity > /dev/null && \
  echo 'caregist-backups-prod-'$(aws sts get-caller-identity --query Account --output text))"
export BACKUP_KMS_KEY_ARN="<value from terraform output kms_key_arn>"

echo "test" | aws s3 cp - \
  s3://${BACKUP_S3_BUCKET}/postgres/test-write.txt \
  --sse aws:kms \
  --sse-kms-key-id "${BACKUP_KMS_KEY_ARN}" \
  --region eu-west-2

# Clean up
aws s3 rm s3://${BACKUP_S3_BUCKET}/postgres/test-write.txt --region eu-west-2
```

## Install the backup cron

See `workflows/backup-monitoring.md` for the cron entry to add to `/etc/cron.d/caregist` on the EC2 instance.

## EBS encryption of the existing volume

In-place EBS encryption is not possible. The migration path (snapshot → copy-with-encryption → swap) is documented with exact CLI commands in `terraform/ebs.tf`. Schedule this as a follow-on operation during a maintenance window.

## Relationship to the manual deploy runbook

`workflows/deploy-ec2.md` remains the source of truth for deploying the application. This Terraform module provisions only the surrounding backup and encryption infrastructure. Future Phase B+ work will import the EC2 instance, security groups, and networking into Terraform.

## Phase B note (future PRs)

This module intentionally does NOT import or manage the existing EC2 instance, its security groups, or VPC resources. Doing so mid-flight without a full audit creates risk. Phase B will:

1. Run `terraform import aws_instance.app <ec2_instance_id>` after a full resource audit.
2. Add ALB + HTTPS termination.
3. Move cron jobs to EventBridge Scheduler.

## Key rotation

Annual key rotation is enabled. When AWS rotates the CMK material, a CloudTrail event `RotateKey` will be emitted. The owner should mirror this event into Caregist's own audit chain (see `trusted_event_ledger`) to satisfy the audit requirement.

## Two-person rule

The restore role trust policy enforces MFA + ExternalId at the IAM level. The two-person approval rule (second engineer must be present during restore) is a process discipline documented in `workflows/restore-from-snapshot.md` — it cannot be enforced by IaC alone.
