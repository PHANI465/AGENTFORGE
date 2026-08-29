# See envs/*.tfvars for how these are set per environment (dev/staging/prod).
# Defaults below are dev-safe (cheapest viable shapes), never prod-safe.

variable "environment" {
  description = "Deployment environment name (dev, staging, prod). Used in resource naming/tagging."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to spread public/private subnets across."
  type        = number
  default     = 2
}

variable "single_nat_gateway" {
  description = "Use one shared NAT Gateway instead of one per AZ. Cuts the biggest recurring cost line (~$32/mo per extra NAT) at the cost of cross-AZ resilience — fine for dev/staging, not recommended for prod."
  type        = bool
  default     = true
}

variable "eks_cluster_version" {
  description = "Kubernetes version for the EKS control plane."
  type        = string
  default     = "1.30"
}

variable "eks_node_instance_types" {
  description = "EC2 instance types for the EKS managed node group."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "eks_node_desired_size" {
  description = "Desired number of worker nodes."
  type        = number
  default     = 2
}

variable "eks_node_min_size" {
  description = "Minimum number of worker nodes."
  type        = number
  default     = 1
}

variable "eks_node_max_size" {
  description = "Maximum number of worker nodes."
  type        = number
  default     = 4
}

variable "rds_instance_class" {
  description = "RDS instance class for the Postgres primary."
  type        = string
  default     = "db.t4g.micro"
}

variable "rds_allocated_storage_gb" {
  description = "RDS allocated storage in GB."
  type        = number
  default     = 20
}

variable "rds_engine_version" {
  description = "Postgres engine version, matching the postgres:16-alpine image used locally."
  type        = string
  default     = "16.4"
}

variable "rds_multi_az" {
  description = "Enable RDS Multi-AZ standby. Roughly doubles RDS cost — leave off for dev/staging."
  type        = bool
  default     = false
}

variable "db_name" {
  description = "Postgres database name."
  type        = string
  default     = "agentforge"
}

variable "db_username" {
  description = "Postgres master username."
  type        = string
  default     = "agentforge"
}

variable "db_password" {
  description = "Postgres master password. Pass via TF_VAR_db_password or a secrets manager — never commit a real value into a .tfvars file."
  type        = string
  sensitive   = true
}

variable "redis_node_type" {
  description = "ElastiCache node type."
  type        = string
  default     = "cache.t4g.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes in the Redis replication group."
  type        = number
  default     = 1
}

variable "ecr_repository_names" {
  description = "Names of the ECR repositories to create, one per deployable image."
  type        = list(string)
  default     = ["api-gateway", "agent-runtime", "eval-service", "trace-collector", "dashboard"]
}

variable "create_state_bucket" {
  description = "Whether to provision the S3 bucket used for Terraform remote state (module.s3). Bootstrap-only: create this once, outside the normal apply, then flip to false."
  type        = bool
  default     = false
}

variable "enable_tls" {
  description = "Provision Route53 + ACM + the Load Balancer Controller's IRSA role for public HTTPS ingress. Off by default (e.g. dev spin-up/teardown clusters with no real domain yet) — see docs/deployment-runbook.md."
  type        = bool
  default     = false
}

variable "domain_name" {
  description = "Domain (or subdomain) this environment serves from, e.g. \"agentforge.example.com\". Only used when enable_tls = true. Still a placeholder — substitute a real owned domain before applying with enable_tls = true."
  type        = string
  default     = "agentforge.example.com"
}

variable "create_route53_zone" {
  description = "true: this environment creates its own hosted zone for domain_name. false: look up an existing zone by that name instead (e.g. an environment sharing a zone another one already created). Only used when enable_tls = true."
  type        = bool
  default     = true
}

variable "enable_waf" {
  description = "Provision a regional WAFv2 Web ACL (rate-limiting + AWS managed common rule set) for the public demo environment. Independent of enable_tls so TLS and WAF can be turned on one at a time — see docs/deployment-runbook.md."
  type        = bool
  default     = false
}
