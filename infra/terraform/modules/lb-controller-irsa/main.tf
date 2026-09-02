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

# Built with aws_iam_policy_document rather than a raw jsonencode map: on a
# first apply, var.oidc_provider_url is unknown until the EKS cluster (and
# its OIDC issuer) actually exists, and jsonencode's map keys must be known
# at plan time — "${var.oidc_provider_url}:sub" as a literal map key fails
# with "Invalid template interpolation value". condition blocks accept an
# unknown value in `variable` without that restriction.
data "aws_iam_policy_document" "lb_controller_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }

    condition {
      test     = "StringEquals"
      variable = "${var.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lb_controller" {
  name               = "agentforge-${var.environment}-lb-controller"
  assume_role_policy = data.aws_iam_policy_document.lb_controller_assume_role.json

  tags = {
    Name = "agentforge-${var.environment}-lb-controller"
  }
}

resource "aws_iam_role_policy_attachment" "lb_controller" {
  role       = aws_iam_role.lb_controller.name
  policy_arn = aws_iam_policy.lb_controller.arn
}
