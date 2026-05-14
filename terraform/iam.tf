##############################################################################
# IAM — Separation of Duty
#
# backup role  (EC2 service principal)
#   - Assumed by the EC2 instance via the instance profile.
#   - May PUT objects under postgres/ prefix and use the CMK for encryption.
#   - Cannot decrypt or access any other prefix.
#
# restore role (humans, break-glass)
#   - Assumed by humans via `sts:AssumeRole` with MFA + ExternalId.
#   - May GET objects under postgres/ prefix and decrypt with the CMK.
#   - Cannot write backups.
#   - Full break-glass procedure in workflows/restore-from-snapshot.md.
##############################################################################

# ── Backup Role ──────────────────────────────────────────────────────────────

data "aws_iam_policy_document" "backup_trust" {
  statement {
    sid     = "EC2AssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backup" {
  name               = "${var.project_name}-backup-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.backup_trust.json
  description        = "Caregist backup role: write-only S3 + KMS encrypt. Attached to EC2 via instance profile."

  tags = {
    Name = "${var.project_name}-backup-${var.environment}"
  }
}

data "aws_iam_policy_document" "backup_permissions" {
  statement {
    sid    = "S3WriteBackups"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:AbortMultipartUpload",
    ]
    resources = ["${aws_s3_bucket.backups.arn}/postgres/*"]
  }

  statement {
    sid    = "KMSEncrypt"
    effect = "Allow"
    actions = [
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = [aws_kms_key.backup.arn]
  }

  statement {
    sid    = "CloudWatchMetrics"
    effect = "Allow"
    actions = [
      "cloudwatch:PutMetricData",
    ]
    # CloudWatch PutMetricData does not support resource-level restrictions.
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["Caregist/Backup"]
    }
  }
}

resource "aws_iam_policy" "backup" {
  name        = "${var.project_name}-backup-${var.environment}"
  description = "Backup role policy: S3 PutObject on postgres/ prefix + KMS encrypt + CloudWatch metrics."
  policy      = data.aws_iam_policy_document.backup_permissions.json
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = aws_iam_policy.backup.arn
}

resource "aws_iam_instance_profile" "backup" {
  name = "${var.project_name}-backup-${var.environment}"
  role = aws_iam_role.backup.name
}

# ── Restore Role ─────────────────────────────────────────────────────────────
# TODO(owner): Replace the placeholder account ID in the principal with the
# ARN of the IAM user or role that your ops team uses for break-glass access.
# The current policy allows any principal in the same account that presents
# valid MFA + the ExternalId. Tighten the Principal to a specific IAM user ARN
# after first apply.

data "aws_iam_policy_document" "restore_trust" {
  statement {
    sid     = "BreakGlassAssumeWithMFA"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    condition {
      test     = "Bool"
      variable = "aws:MultiFactorAuthPresent"
      values   = ["true"]
    }
    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = ["caregist-restore-${var.environment}"]
    }
  }
}

resource "aws_iam_role" "restore" {
  name               = "${var.project_name}-restore-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.restore_trust.json
  description        = "Caregist restore role: read-only S3 + KMS decrypt. Break-glass with MFA + ExternalId."

  tags = {
    Name = "${var.project_name}-restore-${var.environment}"
  }
}

data "aws_iam_policy_document" "restore_permissions" {
  statement {
    sid    = "S3ReadBackups"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.backups.arn,
      "${aws_s3_bucket.backups.arn}/postgres/*",
    ]
  }

  statement {
    sid    = "KMSDecrypt"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]
    resources = [aws_kms_key.backup.arn]
  }
}

resource "aws_iam_policy" "restore" {
  name        = "${var.project_name}-restore-${var.environment}"
  description = "Restore role policy: S3 GetObject on postgres/ prefix + KMS decrypt."
  policy      = data.aws_iam_policy_document.restore_permissions.json
}

resource "aws_iam_role_policy_attachment" "restore" {
  role       = aws_iam_role.restore.name
  policy_arn = aws_iam_policy.restore.arn
}
