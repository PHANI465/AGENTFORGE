variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "cluster_version" {
  type = string
}

variable "node_instance_types" {
  type = list(string)
}

variable "node_desired_size" {
  type = number
}

variable "node_min_size" {
  type = number
}

variable "node_max_size" {
  type = number
}

variable "admin_principal_arns" {
  description = "IAM principal ARNs (users/roles) granted cluster-admin via an EKS access entry, in addition to whatever principal actually creates the cluster (GitHub Actions' OIDC role, which EKS grants automatically). Needed to run kubectl from anywhere else — e.g. your own AWS Console/CloudShell identity."
  type        = list(string)
  default     = []
}
