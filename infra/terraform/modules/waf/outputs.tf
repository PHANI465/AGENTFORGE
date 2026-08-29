output "web_acl_arn" {
  description = "Pass this as the Helm chart's ingress.annotations.\"alb.ingress.kubernetes.io/wafv2-acl-arn\" value — the AWS Load Balancer Controller handles the actual association."
  value       = aws_wafv2_web_acl.this.arn
}
