variable "domain_name" {
  description = "Domain the certificate covers, e.g. \"agentforge.example.com\". Must match module.route53's domain_name for DNS validation to land in the right zone."
  type        = string
}

variable "zone_id" {
  description = "Route53 hosted zone ID to create the DNS validation record in (module.route53.zone_id)."
  type        = string
}
