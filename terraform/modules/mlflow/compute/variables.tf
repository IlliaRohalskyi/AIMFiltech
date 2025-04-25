variable "ec2_instance_type" {
  description = "Instance type for EC2"
  type        = string
}

variable "key_name" {
  description = "Name of the SSH key pair"
  type        = string
}

variable "subnet_id" {
  description = "ID of the subnet for EC2"
  type        = string
}

variable "vpc_security_group_ids" {
  description = "List of VPC security group IDs"
  type        = list(string)
}

variable "rds_address" {
  description = "Address of the RDS instance"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for MLflow artifacts"
  type        = string
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