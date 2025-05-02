variable "s3_bucket_name" {
  type        = string
  description = "Name of the S3 bucket"
}

variable "repository_url" {
  type        = string
  description = "ECR repository URL"
}

variable "image_tag" {
  type        = string
  description = "Docker image tag"
}