##############################################################################
# KMS Customer-Managed Key (CMK) — Phase A
#
# Separation of duty:
#   backup role  → Encrypt + GenerateDataKey (write path)
#   restore role → Decrypt                   (read path, MFA-gated)
#   EC2 instance → neither directly; uses the backup role via instance profile
#
# Annual rotation is enabled by default (AWS rotates the key material once
# per year). Rotation events should be mirrored into the Caregist audit chain
# by the owner. See workflows/backup-monitoring.md for guidance.
##############################################################################

data "aws_iam_policy_document" "kms_backup_policy" {
  # Root account: full KMS administration.
  statement {
    sid    = "RootAdministration"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }

  # Backup role: write-only access.
  statement {
    sid    = "BackupRoleEncrypt"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.backup.arn]
    }
    actions = [
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = ["*"]
  }

  # Restore role: decrypt only (invoked by humans via break-glass STS assume-role).
  statement {
    sid    = "RestoreRoleDecrypt"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.restore.arn]
    }
    actions = [
      "kms:Decrypt",
      "kms:DescribeKey",
    ]
    resources = ["*"]
  }
}

resource "aws_kms_key" "backup" {
  description             = "Caregist backup encryption key (Phase A)"
  enable_key_rotation     = true
  deletion_window_in_days = var.kms_deletion_window_days
  policy                  = data.aws_iam_policy_document.kms_backup_policy.json

  tags = {
    Name        = "${var.project_name}-backup-${var.environment}"
    DataDomain  = "backup"
    NeonProject = var.neon_project_id
  }
}

resource "aws_kms_alias" "backup" {
  name          = "alias/${var.project_name}-backup-${var.environment}"
  target_key_id = aws_kms_key.backup.key_id
}
