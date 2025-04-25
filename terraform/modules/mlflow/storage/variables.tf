variable "s3_bucket_name" {
  description = "Name of the S3 bucket for MLflow artifacts"
  type        = string
}

variable "rds_instance_class" {
  description = "Instance class for RDS"
  type        = string
}

variable "db_subnet_group_id" {
  description = "ID of the DB subnet group"
  type        = string
}

variable "vpc_security_group_ids" {
  description = "List of VPC security group IDs"
  type        = list(string)
}

variable "mlflow_db_username" {
  description = "Username for the MLflow database"
  type        = string
  sensitive   = true
}

variable "mlflow_db_password" {
  description = "Password for the MLflow database"
  type        = string
  sensitive   = true
}