variable "environment" {
  description = "Deployment environment name (dev, staging, prod). Used in resource naming/tagging."
  type        = string
}

variable "oidc_provider_arn" {
  description = "ARN of the EKS cluster's IAM OIDC provider (module.eks.oidc_provider_arn)."
  type        = string
}

variable "oidc_provider_url" {
  description = "The OIDC provider's issuer URL without the https:// prefix — needed to build the trust policy's condition keys (the provider ARN alone doesn't give Terraform the bare hostname)."
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace the controller's service account lives in."
  type        = string
  default     = "kube-system"
}

variable "service_account_name" {
  description = "Kubernetes service account name the AWS Load Balancer Controller Helm chart creates by default."
  type        = string
  default     = "aws-load-balancer-controller"
}
