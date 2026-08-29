output "role_arn" {
  description = "Pass this as eks.serviceAccount.annotations.\"eks.amazonaws.com/role-arn\" when helm-installing the aws-load-balancer-controller chart."
  value       = aws_iam_role.lb_controller.arn
}
