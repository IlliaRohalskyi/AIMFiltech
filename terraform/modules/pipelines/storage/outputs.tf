output "s3_bucket_name" {
  description = "S3 bucket name for data storage"
  value       = aws_s3_bucket.aimfiltech_bucket.bucket
}

output "openfoam_repo_url" {
  description = "ECR repository URL for the OpenFOAM image"
  value       = aws_ecr_repository.openfoam_ecr_repo.repository_url
}

output "lambda_repo_url" {
  description = "ECR repository URL for the Lambda function"
  value       = aws_ecr_repository.lambda_ecr_repo.repository_url
}

output "sagemaker_repo_url" {
  description = "ECR repository URL for the SageMaker training job"
  value       = aws_ecr_repository.sagemaker_ecr_repo.repository_url
}