output "vpc_id" {
  description = "The ID of the MLflow VPC"
  value       = aws_vpc.mlflow_vpc.id
}

output "rds_vpc_id" {
  description = "The ID of the RDS VPC"
  value       = aws_vpc.mlflow_rds_vpc.id
}

output "public_subnet_id" {
  description = "The ID of the public subnet"
  value       = aws_subnet.mlflow_public_subnet.id
}

output "db_subnet_group_name" {
  description = "The name of the DB subnet group"
  value       = aws_db_subnet_group.mlflow_db_subnet_group.name
}

output "ec2_security_group_id" {
  description = "The ID of the EC2 security group"
  value       = aws_security_group.ec2_sg.id
}

output "rds_security_group_id" {
  description = "The ID of the RDS security group"
  value       = aws_security_group.rds_sg.id
}