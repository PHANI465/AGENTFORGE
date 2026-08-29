# Owns the hosted zone only. The actual app-hostname record (pointing at
# whatever ALB the AWS Load Balancer Controller creates for the Ingress) is
# NOT created here — that's managed in-cluster by external-dns (installed
# alongside the LB controller in cd.yml's deploy-eks job), because the ALB's
# DNS name doesn't exist until after the first Helm deploy. Terraform owns
# what's knowable upfront: the zone itself and (in module.acm) the
# certificate's DNS validation records.

resource "aws_route53_zone" "this" {
  count = var.create_zone ? 1 : 0
  name  = var.domain_name

  tags = {
    Name = "agentforge-${var.domain_name}"
  }
}

data "aws_route53_zone" "existing" {
  count = var.create_zone ? 0 : 1
  name  = var.domain_name
}
