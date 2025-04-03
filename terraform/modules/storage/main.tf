# MLflow S3 bucket for artifact storage
resource "aws_s3_bucket" "mlflow_bucket" {
  bucket = var.s3_bucket_name
  acl    = "private"

  versioning {
    enabled = true
  }

  tags = {
    Name = "MLflow Artifact Bucket"
  }
}

# Training data bucket
resource "aws_s3_bucket" "aimfiltech_training_bucket" {
  bucket = "aimfiltech-training-bucket"
  acl    = "private"

  versioning {
    enabled = true
  }

  tags = {
    Project     = "aimfiltech"
    Environment = "Production"
  }
}

# Data source to gather all files in the ../data folder
data "local_file" "files" {
  for_each = fileset("${path.module}/../../data", "*")
  filename = "${path.module}/../../data/${each.value}"
}

# Create an S3 bucket object for each file
resource "aws_s3_bucket_object" "add_training_data" {
  for_each = data.local_file.files

  bucket = aws_s3_bucket.aimfiltech_training_bucket.id
  key    = basename(data.local_file.files[each.key].filename)
  source = data.local_file.files[each.key].filename
  acl    = "private"
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
  
  tags = {
    Name = "MLflow Database"
  }
}