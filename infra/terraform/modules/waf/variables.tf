variable "environment" {
  description = "Deployment environment name (dev, staging, prod). Used in resource naming/tagging."
  type        = string
}

variable "rate_limit_per_5min" {
  description = "Max requests from a single IP in a rolling 5-minute window before WAF starts blocking it. AWS WAF's rate-based rules are always measured over 5 minutes — not configurable to a different window."
  type        = number
  default     = 2000
}

variable "enable_bot_control" {
  description = "Add the AWS Managed Bot Control rule group. Real per-request cost on top of the WAF base price (~$1/mo + $0.60 per million requests baseline; Bot Control adds ~$10/mo + $1/million) — off by default to match this project's cost-conscious defaults. See docs/aws-cost-estimate.md."
  type        = bool
  default     = false
}
