provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "agentforge"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
