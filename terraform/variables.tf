variable "aws_region" {
  type    = string
  description = "AWS region to deploy resources"
}

variable "ec2_instance_type" {
  type    = string
  default = "t2.micro"
  description = "EC2 instance type"
}

variable "rds_instance_class" {
  type    = string
  default = "db.t3.micro"
  description = "RDS instance class"
}

variable "s3_mlflow_bucket_name" {
  type    = string
  default = "aimfiltech-mlflow"
  description = "Name of the MLFlow S3 bucket"
}

variable "mlflow_db_username" {
  type = string
  description = "Username for the MLflow database"
  sensitive = true
}

variable "mlflow_db_password" {
  type = string
  description = "Password for the MLflow database"
  sensitive = true
}

variable "key_name" {
  type = string
  description = "Name of the key pair"
  default = "mlflow-key"
}

variable "s3_bucket_name" {
    default = "aimfiltech-bucket"
    type = string
    description = "Name of the S3 bucket"
}

variable "image_tag" {
  type    = string
  description = "Docker image tag"
}

variable "aws_account_id" {
  type    = string
  description = "AWS account ID"
  sensitive = true
}

variable "mlflow_basic_auth_user" {
  type = string
  description = "Username for MLflow basic authentication"
  sensitive = true
}

variable "mlflow_basic_auth_password" {
  type = string
  description = "Password for MLflow basic authentication"
  sensitive = true
}

variable "ip_address" {
  type = string
  description = "IP address for the MLflow instance"
  sensitive = true
}