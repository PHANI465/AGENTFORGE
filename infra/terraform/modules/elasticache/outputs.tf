output "primary_endpoint" {
  value = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "port" {
  value = aws_elasticache_replication_group.this.port
}

output "redis_url" {
  description = "URL matching the REDIS_URL env var format used by agent-runtime's litellm.Cache(type=\"redis\") wiring."
  value       = "redis://${aws_elasticache_replication_group.this.primary_endpoint_address}:${aws_elasticache_replication_group.this.port}/0"
}

output "security_group_id" {
  value = aws_security_group.redis.id
}
