resource "aws_ecr_repository" "this" {
  for_each = toset(var.repository_names)

  name = "agentforge/${each.value}"
  # Let `terraform destroy` remove the repo even though CI has pushed images
  # into it — without this a teardown fails with RepositoryNotEmptyException
  # and every repo has to be emptied by hand first. These are rebuildable
  # build artifacts (CI repushes them on the next deploy), never source of
  # truth, so deleting them with the environment is exactly what we want.
  force_delete = true
  # MUTABLE, not IMMUTABLE: cd.yml pushes both a unique sha-<commit> tag
  # and a floating :latest on every deploy, and immutable repos reject
  # any second push to a tag that already exists — every deploy after
  # the first would fail pushing :latest. The sha- tags already give a
  # real immutable audit trail per build; :latest just needs to move.
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "agentforge-${var.environment}-${each.value}"
  }
}

# Keep the last 10 tagged images and expire anything untagged after 1 day —
# CI (see .github/workflows/cd.yml) pushes an image on every merge to main,
# so repos would otherwise grow unbounded.
resource "aws_ecr_lifecycle_policy" "this" {
  for_each   = aws_ecr_repository.this
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep only the last 10 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}
