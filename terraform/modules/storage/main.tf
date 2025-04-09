# MLflow S3 bucket for artifact storage
resource "aws_s3_bucket" "mlflow_bucket" {
  bucket = var.s3_bucket_name

  tags = {
    Name = "MLflow Artifact Bucket"
  }

  force_destroy = true
}

resource "aws_s3_bucket_versioning" "enable_mlflow_versioning" {
  bucket = aws_s3_bucket.mlflow_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_policy" "restrict_s3_to_https_only" {
  bucket = aws_s3_bucket.mlflow_bucket.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "EnforceHttps",
        Effect    = "Deny",
        Principal = "*",
        Action    = "s3:*",
        Resource  = [
          "arn:aws:s3:::${aws_s3_bucket.mlflow_bucket.id}",
          "arn:aws:s3:::${aws_s3_bucket.mlflow_bucket.id}/*"
        ],
        Condition = {
          Bool: {
            "aws:SecureTransport": "false" # Deny requests that are not over HTTPS
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket" "aimfiltech_training_bucket" {
  bucket = "aimfiltech-bucket"

  tags = {
    Project     = "aimfiltech"
    Environment = "Production"
  }
  force_destroy = true
}

# RDS instance for MLflow backend
resource "aws_db_instance" "mlflow_rds" {
  identifier           = "mlflowdb"
  db_name              = "mlflowdb"
  allocated_storage    = 20
  engine               = "postgres"
  engine_version       = "17.2"
  instance_class       = var.rds_instance_class
  username             = var.mlflow_db_username
  password             = var.mlflow_db_password
  skip_final_snapshot  = true
  db_subnet_group_name = var.db_subnet_group_id
  vpc_security_group_ids = var.vpc_security_group_ids
  publicly_accessible  = false
  storage_encrypted    = true
  parameter_group_name = aws_db_parameter_group.mlflow_rds_parameters.name

  tags = {
    Name = "MLflow Database"
  }
}

resource "aws_db_parameter_group" "mlflow_rds_parameters" {
  name   = "mlflow-rds-params"
  family = "postgres17"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = {
    Name = "MLflow RDS Parameter Group"
  }
}