terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment and configure this backend block before running `terraform apply`.
  # Create a dedicated state bucket in eu-west-2 first (e.g. caregist-tfstate-<account-id>).
  # The bucket must have versioning enabled and SSE-S3 or SSE-KMS encryption.
  #
  # backend "s3" {
  #   bucket         = "caregist-tfstate-<YOUR_ACCOUNT_ID>"
  #   key            = "prod/terraform.tfstate"
  #   region         = "eu-west-2"
  #   encrypt        = true
  #   dynamodb_table = "caregist-tfstate-lock"  # optional but recommended
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Used to get the current AWS account ID for bucket naming.
data "aws_caller_identity" "current" {}
