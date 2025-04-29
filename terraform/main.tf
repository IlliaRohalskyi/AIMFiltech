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
module "mlflow_storage" {
  source             = "./modules/mlflow/storage"
  s3_bucket_name     = var.s3_mlflow_bucket_name
  rds_instance_class = var.rds_instance_class
  db_subnet_group_id = module.networking.db_subnet_group_name
  vpc_security_group_ids = [module.networking.rds_security_group_id]
  mlflow_db_username = var.mlflow_db_username
  mlflow_db_password = var.mlflow_db_password
  
  depends_on = [module.networking]
}

# 3. Compute module: EC2, IAM roles, user data
module "mlflow_compute" {
  source                = "./modules/mlflow/compute"
  key_name              = var.key_name
  ec2_instance_type     = var.ec2_instance_type
  subnet_id             = module.networking.public_subnet_id
  vpc_security_group_ids = [module.networking.ec2_security_group_id]
  rds_address           = module.mlflow_storage.rds_address
  s3_bucket_name        = module.mlflow_storage.mlflow_bucket_name
  mlflow_db_username    = var.mlflow_db_username
  mlflow_db_password    = var.mlflow_db_password
  depends_on = [module.networking, module.mlflow_storage]
}

# 4. Pipelines module: S3 bucket for pipelines
module "pipelines_storage" {
  source             = "./modules/pipelines/storage"
  s3_bucket_name     = var.s3_bucket_name
}

# 5. Pipelines module: ECS
module "pipelines_ecs" {
  source            = "./modules/pipelines/ecs"
  image_tag         = var.image_tag
  aws_region       = var.aws_region
  s3_bucket_name     = module.pipelines_storage.s3_bucket_name
  repository_url = module.pipelines_storage.repository_url
  aws_account_id   = var.aws_account_id

  depends_on = [module.pipelines_storage]
}

#6. Pipelines module: Batch
module "pipelines_batch" {
  source            = "./modules/pipelines/batch"
  image_tag         = var.image_tag
  repository_url = module.pipelines_storage.repository_url
  subnet_ids        = module.networking.private_subnet_ids
  security_group_ids = [module.networking.batch_sg_id]
  aws_account_id = var.aws_account_id
  aws_region = var.aws_region

  depends_on = [module.networking, module.pipelines_storage]
}