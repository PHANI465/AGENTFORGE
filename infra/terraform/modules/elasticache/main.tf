resource "aws_elasticache_subnet_group" "this" {
  name       = "agentforge-${var.environment}-redis-subnets"
  subnet_ids = var.private_subnet_ids
}

resource "aws_security_group" "redis" {
  name        = "agentforge-${var.environment}-redis-sg"
  description = "Allow Redis access from the EKS cluster only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from EKS nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.eks_node_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "agentforge-${var.environment}-redis-sg"
  }
}

# Single-node replication group, not a cluster-mode setup — matches the
# single redis:7-alpine container used locally (docker-compose.yml). The
# platform's Redis usage (LiteLLM response cache, per ADR-001) doesn't need
# clustering; this is the smallest HA-capable ElastiCache primitive.
resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "agentforge-${var.environment}"
  description           = "AgentForge Redis - LiteLLM response cache"

  engine         = "redis"
  engine_version = "7.1"
  node_type      = var.node_type
  num_cache_clusters = var.num_cache_nodes
  port           = 6379

  subnet_group_name = aws_elasticache_subnet_group.this.name
  security_group_ids = [aws_security_group.redis.id]

  automatic_failover_enabled = var.num_cache_nodes > 1
  at_rest_encryption_enabled = true
  transit_encryption_enabled = false # Redis AUTH/TLS not wired up locally either — see docs/security.md

  tags = {
    Name = "agentforge-${var.environment}-redis"
  }
}
