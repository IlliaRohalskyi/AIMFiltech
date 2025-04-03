terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.82.2"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Budget resource stays in main
resource "aws_budgets_budget" "budget" {
  name         = "budget"
  budget_type  = "COST"
  limit_amount = "100"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
}

# 1. Network module: VPC, subnets, security groups
module "networking" {
  source     = "./modules/networking"
  aws_region = var.aws_region
}

# 2. Storage module: S3 buckets and RDS
module "storage" {
  source             = "./modules/storage"
  s3_bucket_name     = var.s3_bucket_name
  rds_instance_class = var.rds_instance_class
  db_subnet_group_id = module.networking.db_subnet_group_name
  vpc_security_group_ids = [module.networking.rds_security_group_id]
  mlflow_db_username = var.mlflow_db_username
  mlflow_db_password = var.mlflow_db_password
  
  depends_on = [module.networking]
}

# 3. Compute module: EC2, IAM roles, user data
module "compute" {
  source                = "./modules/compute"
  key_name              = var.key_name
  ec2_instance_type     = var.ec2_instance_type
  subnet_id             = module.networking.public_subnet_id
  vpc_security_group_ids = [module.networking.ec2_security_group_id]
  rds_address           = module.storage.rds_address
  s3_bucket_name        = module.storage.mlflow_bucket_name
  mlflow_db_username    = var.mlflow_db_username
  mlflow_db_password    = var.mlflow_db_password
  
  depends_on = [module.networking, module.storage]
}