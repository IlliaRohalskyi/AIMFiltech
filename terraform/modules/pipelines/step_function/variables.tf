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