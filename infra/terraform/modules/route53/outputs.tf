output "zone_id" {
  value = var.create_zone ? aws_route53_zone.this[0].zone_id : data.aws_route53_zone.existing[0].zone_id
}

output "name_servers" {
  description = "Only meaningful when create_zone = true — add these as NS records at your domain registrar to delegate the zone to Route53."
  value       = var.create_zone ? aws_route53_zone.this[0].name_servers : null
}
