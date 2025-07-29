variable "monitoring_lambda_subnet_id" {
  description = "Private subnet ID for monitoring Lambda."
  type        = string
}

variable "monitoring_lambda_security_group_id" {
  description = "Security group ID for monitoring Lambda."
  type        = string
}
# Pre-processing Lambda resources
resource "aws_iam_role" "lambda_exec" {
  name = "preprocess_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_s3" {
  name = "preprocess_s3_policy"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucketVersions",
          "s3:PutObjectTagging",
          "s3:GetObjectVersion"
        ],
        Resource = [
            "arn:aws:s3:::${var.s3_bucket_name}",
            "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      }
    ]
  })
}

resource "aws_lambda_function" "container_lambda" {
  function_name = "preprocess_lambda"
  package_type  = "Image"
  image_uri     = "${var.repository_url}:${var.image_tag}"
  role          = aws_iam_role.lambda_exec.arn
  architectures = ["x86_64"]

  memory_size   = 512
  timeout       = 300

  environment {
    variables = {
      S3_BUCKET = var.s3_bucket_name,
      LAMBDA_HANDLER = "src.lambda_functions.pre_processing.lambda_handler"
    }
  }
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Post-processing Lambda resources
resource "aws_iam_role" "post_process_lambda_exec" {
  name = "post_process_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "post_process_lambda_s3" {
  name = "post_process_s3_policy"
  role = aws_iam_role.post_process_lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucketVersions",
          "s3:PutObjectTagging",
          "s3:GetObjectVersion"
        ],
        Resource = [
            "arn:aws:s3:::${var.s3_bucket_name}",
            "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      }
    ]
  })
}

resource "aws_lambda_function" "post_process_lambda" {
  function_name = "postprocess_lambda"
  package_type  = "Image"
  image_uri     = "${var.repository_url}:${var.image_tag}"
  role          = aws_iam_role.post_process_lambda_exec.arn
  architectures = ["x86_64"]

  memory_size   = 512
  timeout       = 300   

  image_config {
    command = ["src.lambda_functions.post_processing.lambda_handler"]
  }
}

resource "aws_iam_role_policy_attachment" "post_process_lambda_logs" {
  role       = aws_iam_role.post_process_lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Monitoring Lambda resources
resource "aws_iam_role" "monitoring_lambda_exec" {
  name = "monitoring_lambda_exec_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "monitoring_lambda_s3" {
  name = "monitoring_lambda_s3_policy"
  role = aws_iam_role.monitoring_lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucketVersions",
          "s3:PutObjectTagging",
          "s3:GetObjectVersion"
        ],
        Resource = [
            "arn:aws:s3:::${var.s3_bucket_name}",
            "arn:aws:s3:::${var.s3_bucket_name}/*",
            "arn:aws:s3:::${var.mlflow_bucket_name}",
            "arn:aws:s3:::${var.mlflow_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "sns:Publish"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
          "secretsmanager:ListSecrets"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "sts:AssumeRole"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "monitoring_lambda" {
  function_name = "monitoring_lambda"
  package_type  = "Image"
  image_uri     = "${var.repository_url}:${var.image_tag}"
  role          = aws_iam_role.monitoring_lambda_exec.arn
  architectures = ["x86_64"]

  memory_size   = 1024  # Higher memory for data processing
  timeout       = 600   # Longer timeout for comprehensive analysis

  image_config {
    command = ["src.lambda_functions.monitoring.lambda_handler"]
  }

  environment {
    variables = {
      S3_BUCKET = var.s3_bucket_name
    }
  }

  vpc_config {
    subnet_ids         = [var.monitoring_lambda_subnet_id]
    security_group_ids = [var.monitoring_lambda_security_group_id]
  }
}

resource "aws_iam_role_policy_attachment" "monitoring_lambda_logs" {
  role       = aws_iam_role.monitoring_lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}