# Bootstrap bucket for Terraform remote state (see root versions.tf's
# commented-out `backend "s3"` block) and, if the platform ever needs it,
# a spot for eval-run artifacts too large for Postgres. Not required to run
# AgentForge — everything else in this repo works against a fresh local
# state file.
resource "aws_s3_bucket" "state" {
  count  = var.create_state_bucket ? 1 : 0
  bucket = "agentforge-${var.environment}-terraform-state"

  tags = {
    Name = "agentforge-${var.environment}-terraform-state"
  }
}

resource "aws_s3_bucket_versioning" "state" {
  count  = var.create_state_bucket ? 1 : 0
  bucket = aws_s3_bucket.state[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  count  = var.create_state_bucket ? 1 : 0
  bucket = aws_s3_bucket.state[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  count  = var.create_state_bucket ? 1 : 0
  bucket = aws_s3_bucket.state[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "locks" {
  count        = var.create_state_bucket ? 1 : 0
  name         = "agentforge-${var.environment}-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = "agentforge-${var.environment}-terraform-locks"
  }
}
