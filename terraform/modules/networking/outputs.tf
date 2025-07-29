output "vpc_id" {
  description = "The ID of the MLflow VPC"
  value       = aws_vpc.vpc.id
}

output "public_subnet_id" {
  description = "The ID of the public subnet"
  value       = aws_subnet.public_subnet.id
}

output "db_subnet_group_name" {
  description = "The name of the DB subnet group"
  value       = aws_db_subnet_group.mlflow_db_subnet_group.name
}

output "ec2_security_group_id" {
  description = "The ID of the EC2 security group"
  value       = aws_security_group.mlflow_ec2_sg.id
}

output "rds_security_group_id" {
  description = "The ID of the RDS security group"
  value       = aws_security_group.mlflow_rds_sg.id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = [aws_subnet.private_subnet_a.id, aws_subnet.private_subnet_b.id]
}

output "batch_sg_id" {
  description = "The ID of the Batch security group"
  value       = aws_security_group.batch_sg.id
}

output "sagemaker_security_group_id" {
  description = "The ID of the SageMaker security group"
  value       = aws_security_group.sagemaker_sg.id
}

output "monitor_lambda_sg" {
  description = "Security group for monitoring lambda"
  value       = aws_security_group.monitor_lambda_sg.id
}