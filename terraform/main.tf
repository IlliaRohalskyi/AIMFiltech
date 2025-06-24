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

#Network module: VPC, subnets, security groups
module "networking" {
  source     = "./modules/networking"
  aws_region = var.aws_region
  ip_address = var.ip_address
}

#Storage module: S3 buckets and RDS
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

#Compute module: EC2, IAM roles, user data
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
  mlflow_basic_auth_user = var.mlflow_basic_auth_user
  mlflow_basic_auth_password = var.mlflow_basic_auth_password
  depends_on = [module.networking, module.mlflow_storage]
}

#Pipelines module: S3 bucket for pipelines
module "pipelines_storage" {
  source             = "./modules/pipelines/storage"
  s3_bucket_name     = var.s3_bucket_name
}

#Pipelines module: Lambda
module "pipelines_lambda" {
  s3_bucket_name = module.pipelines_storage.s3_bucket_name
  source            = "./modules/pipelines/lambda"
  image_tag         = var.image_tag
  repository_url = module.pipelines_storage.lambda_repo_url

  depends_on = [module.pipelines_storage]
}

#Pipelines module: Batch
module "pipelines_batch" {
  source            = "./modules/pipelines/batch"
  image_tag         = var.image_tag
  repository_url = module.pipelines_storage.openfoam_repo_url
  subnet_ids        = module.networking.private_subnet_ids
  security_group_ids = [module.networking.batch_sg_id]
  aws_account_id = var.aws_account_id
  aws_region = var.aws_region
  s3_bucket_name = module.pipelines_storage.s3_bucket_name

  depends_on = [module.networking, module.pipelines_storage]
}

#Pipelines module: SageMaker
module "sagemaker" {
  source = "./modules/pipelines/sagemaker"

  mlflow_basic_auth_user = var.mlflow_basic_auth_user
  mlflow_basic_auth_password = var.mlflow_basic_auth_password
}

#Pipelines module: Step Function
module "pipeline_step_function" {
  source            = "./modules/pipelines/step_function"
  aws_account_id = var.aws_account_id
  aws_region = var.aws_region
  s3_bucket_name     = module.pipelines_storage.s3_bucket_name
  split_data_lambda_name = module.pipelines_lambda.lambda_name
  post_process_lambda_name = module.pipelines_lambda.post_process_lambda_name
  batch_job_queue_arn = module.pipelines_batch.batch_job_queue_arn
  batch_job_definition_arn = module.pipelines_batch.batch_job_definition_arn
  batch_job_name = module.pipelines_batch.batch_job_name
  sagemaker_security_group_id = module.networking.sagemaker_security_group_id
  sagemaker_subnet_id = module.networking.private_subnet_ids[0]
  repository_url = module.pipelines_storage.sagemaker_repo_url
  image_tag = var.image_tag
  sagemaker_role_arn = module.sagemaker.sagemaker_role_arn
  mlflow_private_ip = module.mlflow_compute.mlflow_server_private_ip

  depends_on = [module.pipelines_batch, module.pipelines_lambda]
}

#Pipelines module: Trigger
module "pipeline_trigger" {
  source            = "./modules/pipelines/trigger"
  s3_bucket_name     = module.pipelines_storage.s3_bucket_name
  step_function_arn = module.pipeline_step_function.step_function_arn
  aws_region = var.aws_region  
  depends_on = [module.pipeline_step_function, module.pipelines_storage]
}