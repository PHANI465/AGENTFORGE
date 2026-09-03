output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "configure_kubectl" {
  description = "Run this after apply to point kubectl/helm at the new cluster."
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "ecr_repository_urls" {
  value = module.ecr.repository_urls
}

output "vpc_id" {
  description = "Feed this into the aws-load-balancer-controller Helm install's --set vpcId=. Without it, the controller falls back to discovering the VPC via EC2 instance metadata from inside its own pod, which fails outright unless the node group's metadata hop limit is explicitly raised to 2 — simpler to just tell it directly."
  value       = module.vpc.vpc_id
}

output "rds_endpoint" {
  value = module.rds.endpoint
}

output "redis_primary_endpoint" {
  value = module.elasticache.primary_endpoint
}

output "postgres_dsn" {
  sensitive = true
  value     = module.rds.postgres_dsn
}

output "redis_url" {
  value = module.elasticache.redis_url
}

output "acm_certificate_arn" {
  description = "Only set when enable_tls = true. Feed this into the Helm chart's alb.ingress.kubernetes.io/certificate-arn annotation."
  value       = var.enable_tls ? module.acm[0].certificate_arn : null
}

output "lb_controller_irsa_role_arn" {
  description = "Only set when enable_ingress = true. Feed this into the aws-load-balancer-controller Helm install's serviceAccount.annotations."
  value       = var.enable_ingress ? module.lb_controller_irsa[0].role_arn : null
}

output "external_dns_irsa_role_arn" {
  description = "Only set when enable_tls = true. Feed this into the external-dns Helm install's serviceAccount.annotations."
  value       = var.enable_tls ? module.external_dns_irsa[0].role_arn : null
}

output "waf_web_acl_arn" {
  description = "Only set when enable_waf = true. Feed this into the Helm chart's alb.ingress.kubernetes.io/wafv2-acl-arn annotation."
  value       = var.enable_waf ? module.waf[0].web_acl_arn : null
}

output "route53_zone_id" {
  description = "Only set when enable_tls = true. external-dns needs this (via its own IAM policy, not shown here) to manage the app hostname's record."
  value       = var.enable_tls ? module.route53[0].zone_id : null
}

output "route53_name_servers" {
  description = "Only set when enable_tls = true and create_route53_zone = true. Delegate domain_name to Route53 by adding these as NS records at your registrar."
  value       = var.enable_tls ? module.route53[0].name_servers : null
}
