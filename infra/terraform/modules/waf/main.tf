# Regional WAFv2 Web ACL for the public demo's ALB. Not associated here via
# a Terraform aws_wafv2_web_acl_association — the ALB doesn't exist until
# after the first Helm deploy (same chicken-egg problem the acm/route53
# modules solve differently). Instead, pass this module's web_acl_arn
# output to the Helm chart's ingress.annotations."alb.ingress.kubernetes.io/wafv2-acl-arn"
# (see infra/helm/agentforge/values-staging.yaml) — the AWS Load Balancer
# Controller associates it with the ALB it manages directly; no separate
# association resource needed.

resource "aws_wafv2_web_acl" "this" {
  name  = "agentforge-${var.environment}"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "rate-limit"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.rate_limit_per_5min
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "agentforge-${var.environment}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "aws-common-rule-set"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "agentforge-${var.environment}-common-rules"
      sampled_requests_enabled   = true
    }
  }

  dynamic "rule" {
    for_each = var.enable_bot_control ? [1] : []
    content {
      name     = "aws-bot-control"
      priority = 3

      override_action {
        none {}
      }

      statement {
        managed_rule_group_statement {
          name        = "AWSManagedRulesBotControlRuleSet"
          vendor_name = "AWS"
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "agentforge-${var.environment}-bot-control"
        sampled_requests_enabled   = true
      }
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "agentforge-${var.environment}"
    sampled_requests_enabled   = true
  }

  tags = {
    Name = "agentforge-${var.environment}"
  }
}
