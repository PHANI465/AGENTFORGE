# IAM role for the AWS Load Balancer Controller's Kubernetes service account
# (IRSA — IAM Roles for Service Accounts), so the controller can create/manage
# ALBs on behalf of Ingress resources without static AWS credentials mounted
# into the pod. The Helm chart install itself (kubernetes-sigs/aws-load-balancer-controller)
# happens in .github/workflows/cd.yml, not here — this module only creates the
# IAM side IRSA needs.
#
# The attached policy is the project's unmodified copy of the controller's
# own published minimum-permissions policy:
# https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

resource "aws_iam_policy" "lb_controller" {
  name        = "agentforge-${var.environment}-lb-controller"
  description = "Minimum permissions for the AWS Load Balancer Controller (upstream-published policy, unmodified)."
  policy      = file("${path.module}/iam_policy.json")
}

resource "aws_iam_role" "lb_controller" {
  name = "agentforge-${var.environment}-lb-controller"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = var.oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${var.oidc_provider_url}:sub" = "system:serviceaccount:${var.namespace}:${var.service_account_name}"
          "${var.oidc_provider_url}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = {
    Name = "agentforge-${var.environment}-lb-controller"
  }
}

resource "aws_iam_role_policy_attachment" "lb_controller" {
  role       = aws_iam_role.lb_controller.name
  policy_arn = aws_iam_policy.lb_controller.arn
}
