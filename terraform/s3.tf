##############################################################################
# S3 Backup Bucket
#
# Bucket name includes the AWS account ID to guarantee global uniqueness.
# All objects are encrypted with the CMK (SSE-KMS, bucket_key_enabled for
# cost efficiency). Versioning is enabled so accidental deletes can be
# recovered within the retention window. Public access is blocked uncondi-
# tionally. HTTPS is enforced by a bucket policy deny.
##############################################################################

locals {
  backup_bucket_name = "${var.project_name}-backups-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "backups" {
  bucket = local.backup_bucket_name

  tags = {
    Name       = local.backup_bucket_name
    DataDomain = "backup"
  }
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    bucket_key_enabled = true

    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.backup.arn
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "expire-postgres-backups"
    status = "Enabled"

    filter {
      prefix = "postgres/"
    }

    # Expire current-version objects after the configured retention window.
    expiration {
      days = var.backup_retention_days
    }

    # Remove old versions quickly to avoid stale data accumulation.
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Deny all requests that do not use TLS.
data "aws_iam_policy_document" "backups_bucket_policy" {
  statement {
    sid    = "DenyNonTLS"
    effect = "Deny"
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    actions   = ["s3:*"]
    resources = [
      aws_s3_bucket.backups.arn,
      "${aws_s3_bucket.backups.arn}/*",
    ]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "backups" {
  bucket = aws_s3_bucket.backups.id
  policy = data.aws_iam_policy_document.backups_bucket_policy.json

  # Ensure public access block is applied before the bucket policy.
  depends_on = [aws_s3_bucket_public_access_block.backups]
}
