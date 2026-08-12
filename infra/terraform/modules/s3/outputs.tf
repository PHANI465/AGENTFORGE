output "state_bucket_name" {
  value = var.create_state_bucket ? aws_s3_bucket.state[0].bucket : null
}

output "locks_table_name" {
  value = var.create_state_bucket ? aws_dynamodb_table.locks[0].name : null
}
