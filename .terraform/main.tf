terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.82.2"
    }
  }
}

provider "aws" {
  region = "eu-central-1"
}

resource "aws_budgets_budget" "budget" {
  name         = "budget"
  budget_type  = "COST"
  limit_amount = "100"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
}

resource "aws_s3_bucket" "aimfiltech-training-bucket" {
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

resource "aws_s3_bucket_object" "add-training-data" {
  bucket = aws_s3_bucket.aimfiltech-training-bucket.id
  key    = "231212_Lab data.xlsx"
  source = "${path.module}/../data/231212_Lab data.xlsx"
  acl    = "private"
}


