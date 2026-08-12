resource "aws_db_subnet_group" "this" {
  name       = "agentforge-${var.environment}-db-subnets"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "agentforge-${var.environment}-db-subnets"
  }
}

resource "aws_security_group" "db" {
  name        = "agentforge-${var.environment}-rds-sg"
  description = "Allow Postgres access from the EKS cluster only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Postgres from EKS nodes"
    from_port       = 5432
    to_port         = 5432
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
    Name = "agentforge-${var.environment}-rds-sg"
  }
}

resource "aws_db_instance" "this" {
  identifier     = "agentforge-${var.environment}"
  engine         = "postgres"
  engine_version = var.engine_version

  instance_class        = var.instance_class
  allocated_storage     = var.allocated_storage_gb
  storage_type          = "gp3"
  storage_encrypted     = true
  db_name               = var.db_name
  username              = var.db_username
  password              = var.db_password
  db_subnet_group_name  = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]

  multi_az            = var.multi_az
  publicly_accessible = false

  backup_retention_period = var.environment == "prod" ? 7 : 1
  skip_final_snapshot     = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "agentforge-${var.environment}-final" : null
  deletion_protection     = var.environment == "prod"

  tags = {
    Name = "agentforge-${var.environment}-postgres"
  }
}
