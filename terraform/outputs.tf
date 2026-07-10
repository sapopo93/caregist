output "kms_key_arn" {
  description = "ARN of the Caregist backup CMK. Set as BACKUP_KMS_KEY_ARN in the production environment."
  value       = aws_kms_key.backup.arn
}

output "kms_key_alias" {
  description = "Friendly alias for the backup CMK."
  value       = aws_kms_alias.backup.name
}

output "backup_bucket_name" {
  description = "Name of the S3 backup bucket. Set as BACKUP_S3_BUCKET in the production environment."
  value       = aws_s3_bucket.backups.bucket
}

output "backup_role_arn" {
  description = "ARN of the IAM backup role. Attached to EC2 via the instance profile."
  value       = aws_iam_role.backup.arn
}

output "restore_role_arn" {
  description = "ARN of the IAM restore role. Used in break-glass STS AssumeRole calls. Set as RESTORE_ROLE_ARN in non-prod environments doing restore tests."
  value       = aws_iam_role.restore.arn
}

output "backup_instance_profile_name" {
  description = "Name of the EC2 instance profile wrapping the backup role. Use this when attaching via the AWS CLI."
  value       = aws_iam_instance_profile.backup.name
}

output "backup_instance_profile_arn" {
  description = "ARN of the EC2 instance profile."
  value       = aws_iam_instance_profile.backup.arn
}
