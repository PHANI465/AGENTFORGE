# IAM role for external-dns's Kubernetes service account (IRSA). external-dns
# watches Ingress resources and keeps the app hostname's Route53 record
# pointed at whatever ALB the AWS Load Balancer Controller creates — this is
# what lets Terraform own the zone and the ACM validation records (both
# knowable upfront) without needing to know the ALB's DNS name, which only
# exists after the first Helm deploy. The Helm install itself
# (kubernetes-sigs/external-dns) happens in .github/workflows/cd.yml.
#
# Policy is the project's unmodified copy of external-dns's own documented
# minimum policy:
# https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md

resource "aws_iam_policy" "external_dns" {
  name        = "agentforge-${var.environment}-external-dns"
  description = "Minimum Route53 permissions for external-dns (upstream-documented policy, unmodified)."
  policy      = file("${path.module}/iam_policy.json")
}

# Built with aws_iam_policy_document rather than a raw jsonencode map — see
# the matching comment in modules/lb-controller-irsa/main.tf: on a first
# apply var.oidc_provider_url is unknown until the EKS cluster exists, and
# jsonencode's map keys must be known at plan time, which a literal
# "${var.oidc_provider_url}:sub" key is not.
data "aws_iam_policy_document" "external_dns_assume_role" {
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

resource "aws_iam_role" "external_dns" {
  name               = "agentforge-${var.environment}-external-dns"
  assume_role_policy = data.aws_iam_policy_document.external_dns_assume_role.json

  tags = {
    Name = "agentforge-${var.environment}-external-dns"
  }
}

resource "aws_iam_role_policy_attachment" "external_dns" {
  role       = aws_iam_role.external_dns.name
  policy_arn = aws_iam_policy.external_dns.arn
}
