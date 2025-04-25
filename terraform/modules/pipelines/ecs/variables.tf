variable "repository_url" {
  description = "ECR repository URL for the Docker image"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "s3_bucket_name" {
    description = "S3 bucket name for data storage"
    type        = string
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
}