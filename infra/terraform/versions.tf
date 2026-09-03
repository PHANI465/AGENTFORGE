terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Partial config on purpose — bucket/key/table differ per environment
  # (modules/s3 provisions one bucket + lock table per environment) and a
  # backend block can't reference a variable. infra-apply.yml's terraform
  # init supplies the rest via -backend-config flags, derived from
  # inputs.environment. See docs/deployment-runbook.md's "Bootstrapping
  # state for a new environment" section before the first-ever apply
  # against a given environment — that bucket has to exist before this
  # backend can be initialized against it at all.
  backend "s3" {}
}
