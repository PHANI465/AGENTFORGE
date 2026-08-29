output "role_arn" {
  description = "Pass this as serviceAccount.annotations.\"eks.amazonaws.com/role-arn\" when helm-installing the external-dns chart."
  value       = aws_iam_role.external_dns.arn
}
