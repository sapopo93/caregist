variable "region" {
  description = "AWS region. Must be eu-west-2 (London) to satisfy UK data residency requirement."
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  description = "Short project identifier used in resource names and tags."
  type        = string
  default     = "caregist"
}

variable "environment" {
  description = "Deployment environment. Must be 'prod' or 'staging'."
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["prod", "staging"], var.environment)
    error_message = "environment must be 'prod' or 'staging'."
  }
}

variable "ec2_instance_id" {
  description = "ID of the existing EC2 instance (e.g. i-0abc123def456). Set in prod.tfvars. This module does NOT manage the EC2 instance itself — only the surrounding backup/KMS infra."
  type        = string
  # No default — owner must supply this in their tfvars.
  # TODO(owner): set this in terraform/prod.tfvars after terraform apply.
}

variable "neon_project_id" {
  description = "Neon project ID (e.g. noisy-lab-123456). Used only for resource tagging. Does not affect AWS resources."
  type        = string
  # No default — owner must supply this in their tfvars.
  # TODO(owner): copy from the Neon dashboard and set in terraform/prod.tfvars.
}

variable "backup_retention_days" {
  description = "Number of days to retain current-version backup objects in S3. Noncurrent versions are always removed after 7 days."
  type        = number
  default     = 7
}

variable "kms_deletion_window_days" {
  description = "Waiting period (in days) before KMS key deletion takes effect. Min 7, max 30. Set to 30 per owner decision."
  type        = number
  default     = 30
}

variable "backup_role_principal_arn" {
  description = "ARN of the principal that may assume the backup role. Defaults to the instance profile we create. Override only if you are not using the aws_iam_instance_profile.backup resource from this module."
  type        = string
  default     = ""
  # Intentionally left empty; the iam.tf trust policy references aws_iam_role.backup directly.
  # This variable is reserved for future use (e.g. a separate CI/CD role).
}
