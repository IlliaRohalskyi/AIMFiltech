output "mlflow_bucket_name" {
  description = "Name of the MLflow S3 bucket"
  value       = aws_s3_bucket.mlflow_bucket.bucket
}

output "training_bucket_name" {
  description = "Name of the training data S3 bucket"
  value       = aws_s3_bucket.aimfiltech_training_bucket.bucket
}

output "rds_address" {
  description = "Address of the RDS instance"
  value       = aws_db_instance.mlflow_rds.address
}