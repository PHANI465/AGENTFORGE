variable "environment" {
  description = "Deployment environment name (dev, staging, prod). Used in resource naming/tagging."
  type        = string
}

variable "oidc_provider_arn" {
  description = "ARN of the EKS cluster's IAM OIDC provider (module.eks.oidc_provider_arn)."
  type        = string
}

variable "oidc_provider_url" {
  description = "The OIDC provider's bare issuer hostname (module.eks.oidc_provider_url)."
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace external-dns's service account lives in."
  type        = string
  default     = "kube-system"
}

variable "service_account_name" {
  description = "Kubernetes service account name the external-dns Helm chart creates by default."
  type        = string
  default     = "external-dns"
}
