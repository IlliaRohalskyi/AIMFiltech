variable "subnet_ids" {
    description = "List of subnet IDs for the compute environment"
    type        = list(string)
}

variable "security_group_ids" {
    description = "List of security group IDs for the compute environment"
    type        = list(string)
}

variable "image_tag" {
    description = "Docker image for the job"
    type        = string
}

variable "repository_url" {
    description = "ECR repository URL for the Docker image"
    type        = string
}

variable "aws_region" {
    description = "AWS region to deploy resources"
    type        = string
}

variable "aws_account_id" {
    description = "AWS account ID"
    type        = string
}