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

variable "s3_bucket_name" {
  type    = string
  default = "aimfiltech-mlflow"
  description = "Name of the S3 bucket"
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

variable "vpc_cidr" {
    type = string
    description = "CIDR block for the VPC"
}

variable "public_subnet_cidr" {
    type = string
    description = "CIDR block for the public subnet"
}

variable "private_subnet_cidr" {
    type = string
    description = "CIDR block for the private subnet"
}

variable "availability_zone" {
    type = string
    description = "Availability zone for the public subnet"
}