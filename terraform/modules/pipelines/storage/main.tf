resource "aws_s3_bucket" "aimfiltech_bucket" {
  bucket = var.s3_bucket_name

  tags = {
    Project     = "aimfiltech"
    Environment = "Production"
  }
  force_destroy = true
}

resource "aws_s3_object" "raw_folder" {
  bucket = aws_s3_bucket.aimfiltech_bucket.id
  key    = "raw/"
}

resource "aws_s3_object" "transform_folder" {
  bucket = aws_s3_bucket.aimfiltech_bucket.id
  key    = "processed/"
}

resource "aws_s3_bucket_versioning" "enable_aimfiltech_versioning" {
  bucket = aws_s3_bucket.aimfiltech_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_ecr_repository" "ecr_repo" {
  name                 = "aimfiltech-ecr-repo"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true
}

resource "aws_ecr_lifecycle_policy" "ecr_repo_policy" {
  repository = aws_ecr_repository.ecr_repo.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description = "Retain only 5 most recent images"
        selection    = {
          tagStatus = "any"
          countType = "imageCountMoreThan"
          countNumber = 5
        }
        action       = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_s3_bucket_policy" "restrict_s3_to_https_only" {
  bucket = aws_s3_bucket.aimfiltech_bucket.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "EnforceHttps",
        Effect    = "Deny",
        Principal = "*",
        Action    = "s3:*",
        Resource  = [
          "arn:aws:s3:::${aws_s3_bucket.aimfiltech_bucket.id}",
          "arn:aws:s3:::${aws_s3_bucket.aimfiltech_bucket.id}/*"
        ],
        Condition = {
          Bool: {
            "aws:SecureTransport": "false" # Deny requests that are not over HTTPS
          }
        }
      }
    ]
  })
}