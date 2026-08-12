output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.this.endpoint
}

output "cluster_ca_certificate" {
  value = aws_eks_cluster.this.certificate_authority[0].data
}

output "cluster_security_group_id" {
  value = aws_security_group.cluster.id
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.eks.arn
}

output "node_security_group_id" {
  description = "EKS auto-manages a node security group; exposed here via the cluster's vpc_config for use by RDS/ElastiCache security group rules."
  value       = aws_eks_cluster.this.vpc_config[0].cluster_security_group_id
}
