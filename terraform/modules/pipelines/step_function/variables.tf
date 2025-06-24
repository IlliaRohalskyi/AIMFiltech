variable "aws_region" {
  description = "AWS region where resources are deployed"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "split_data_lambda_name" {
  description = "Name of the Lambda function for splitting data"
  type        = string
}

variable "batch_job_queue_arn" {
  description = "ARN of the AWS Batch Job Queue"
  type        = string
}

variable "batch_job_definition_arn" {
  description = "ARN of the AWS Batch Job Definition"
  type        = string
}

variable "batch_job_name" {
  description = "Name of the AWS Batch job"
  type        = string
}

variable "post_process_lambda_name" {
  description = "Name of the Lambda function for post-processing data"
  type        = string
}

variable "sagemaker_role_arn" {
  description = "ARN of IAM role for SageMaker"
  type        = string
}

variable "sagemaker_security_group_id" {
  description = "Security group ID for SageMaker training job"
  type        = string
}

variable "sagemaker_subnet_id" {
  description = "Subnet ID for SageMaker training job"
  type        = string
}

variable "repository_url" {
  description = "URL of the Docker repository for Sagemaker training job"
  type        = string
}

variable "image_tag" {
  description = "Tag of the Docker image for Sagemaker training job"
  type        = string
}

variable "mlflow_private_ip" {
    description = "Private IP address of the MLflow server"
    type        = string
}