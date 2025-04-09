output "mlflow_server_public_dns" {
  description = "Public DNS of the MLflow tracking server"
  value       = module.compute.mlflow_server_public_dns
}

output "mlflow_server_public_ip" {
  description = "Public IP of the MLflow tracking server"
  value       = module.compute.mlflow_server_public_ip
}

output "mlflow_url" {
  description = "URL to access MLflow UI"
  value       = "https://${module.compute.mlflow_server_public_dns}"
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.storage.rds_address
}