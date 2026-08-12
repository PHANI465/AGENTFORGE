terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state is intentionally not configured here — AWS Constraints in
  # CLAUDE.md keep this project on a $0 budget with no always-on cloud
  # resources, so there's no S3 bucket/DynamoDB table to point at yet.
  # Uncomment and fill in once you provision one (see modules/s3):
  #
  # backend "s3" {
  #   bucket         = "agentforge-terraform-state"
  #   key            = "agentforge/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "agentforge-terraform-locks"
  #   encrypt        = true
  # }
}
