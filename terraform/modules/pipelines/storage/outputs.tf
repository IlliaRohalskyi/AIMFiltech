output "s3_bucket_name" {
  description = "S3 bucket name for data storage"
  value       = aws_s3_bucket.aimfiltech_bucket.bucket
}

output "repository_url" {
  description = "ECR repository URL for the Docker image"
  value       = aws_ecr_repository.ecr_repo.repository_url
}