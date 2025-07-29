variable "mlflow_basic_auth_user" {
  type     = string
  sensitive = true
}

variable "mlflow_basic_auth_password" {
  type     = string
  sensitive = true
}

variable "repository_url" {
  description = "ECR repository URL for SageMaker container"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
}

variable "sagemaker_security_group_id" {
  description = "Security group ID for SageMaker"
  type        = string
}

variable "sagemaker_subnet_id" {
  description = "Subnet ID for SageMaker"
  type        = string
}