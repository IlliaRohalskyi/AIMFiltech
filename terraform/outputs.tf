output "mlflow_server_public_dns" {
  description = "Public DNS of the MLflow tracking server"
  value       = module.mlflow_compute.mlflow_server_public_dns
}

output "mlflow_server_public_ip" {
  description = "Public IP of the MLflow tracking server"
  value       = module.mlflow_compute.mlflow_server_public_ip
}

output "mlflow_url" {
  description = "URL to access MLflow UI"
  value       = "https://${module.mlflow_compute.mlflow_server_public_dns}"
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.mlflow_storage.rds_address
}

output "lambda_ecr_repo" {
  description = "ECR repository URL for the Lambda function"
  value       = module.pipelines_storage.lambda_repo_url
}

output "openfoam_ecr_repo" {
  description = "ECR repository URL for the OpenFOAM image"
  value       = module.pipelines_storage.openfoam_repo_url
}