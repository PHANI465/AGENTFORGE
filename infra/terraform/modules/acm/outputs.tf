output "certificate_arn" {
  description = "Pass this as the Helm chart's ingress.annotations.\"alb.ingress.kubernetes.io/certificate-arn\" value."
  value       = aws_acm_certificate_validation.this.certificate_arn
}
