output "endpoint" {
  value = aws_db_instance.this.endpoint
}

output "address" {
  value = aws_db_instance.this.address
}

output "port" {
  value = aws_db_instance.this.port
}

output "security_group_id" {
  value = aws_security_group.db.id
}

output "postgres_dsn" {
  description = "asyncpg DSN matching agentforge_common/db.py's expected format. Password is sensitive — read this output explicitly (terraform output postgres_dsn) rather than letting it print in plan/apply logs."
  value       = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/${var.db_name}"
  sensitive   = true
}
