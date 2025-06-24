output "mlflow_server_public_dns" {
  description = "Public DNS of the MLflow tracking server"
  value       = aws_instance.mlflow_ec2.public_dns
}

output "mlflow_server_public_ip" {
  description = "Public IP of the MLflow tracking server"
  value       = aws_instance.mlflow_ec2.public_ip
}

output "mlflow_server_private_ip" {
  description = "Private IP of the MLflow tracking server"
  value       = aws_instance.mlflow_ec2.private_ip
}