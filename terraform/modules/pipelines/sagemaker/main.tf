resource "aws_secretsmanager_secret" "mlflow_basic_auth" {
  name        = "mlflow-basic-auth"
  description = "MLflow basic auth credentials"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "mlflow_basic_auth_version" {
  secret_id     = aws_secretsmanager_secret.mlflow_basic_auth.id
  secret_string = jsonencode({
    username = var.mlflow_basic_auth_user
    password = var.mlflow_basic_auth_password
  })
}

resource "aws_iam_role" "sagemaker_execution_role" {
  name = "aimfiltech-sagemaker-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "sagemaker.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_policy" "sagemaker_iam_policy" {
  name = "aimfiltech-sagemaker-iam-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = aws_secretsmanager_secret.mlflow_basic_auth.arn
      },
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:CreateNetworkInterfacePermission",
          "ec2:DeleteNetworkInterface",
          "ec2:DeleteNetworkInterfacePermission",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeVpcs",
          "ec2:DescribeDhcpOptions",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "iam:GetRole"

        ],
        Resource = aws_iam_role.sagemaker_execution_role.arn
      },
      {
        Effect = "Allow",
        Action = [
          "sagemaker:UpdateTrainingJob",
        ],
        Resource = "*"
      }
    ]
  })
}


resource "aws_iam_role_policy_attachment" "sagemaker_secrets_policy_attach" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = aws_iam_policy.sagemaker_iam_policy.arn
}